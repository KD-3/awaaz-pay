"""The audio bridge (§5): Vobiz media stream <-> Saaras STT <-> gate/ledger
<-> state machine <-> Sarvam-30B (slots only) <-> Bulbul TTS <-> Vobiz
playback.

Protocol note: the inbound "start"/"media"/"stop" event shapes below are
built from Vobiz's published docs and its Pipecat integration reference
(streamId/callId/media.payload, playAudio/clearAudio/checkpoint commands).
The exact inbound "media" frame shape wasn't in the fetched docs verbatim, so
`_extract_inbound_payload` tries the documented field path and logs the raw
frame once if it doesn't match - the first real inbound call is where this
gets pinned down for real, per the build plan.

Inbound audio is buffered per caller turn and transcribed via REST once a
simple energy-based VAD decides the caller has stopped talking (see
CallHandler.handle_inbound_audio / _maybe_finish_utterance). The streaming
STT WebSocket was tried first and reliably closed the connection after 1-2
messages with zero transcript events, confirmed on live calls and in
isolated tests with both silence and known-good real speech - not something
fixable from this side, and the REST endpoint transcribes the same audio
correctly every time. See app/sarvam/stt.py's module docstring for the full
trail. The trade-off: the abort keyword now fires after ~700ms of trailing
silence rather than instantly mid-utterance, since there is no longer a
partial-transcript stream to check word-by-word.
"""
from __future__ import annotations

import asyncio
import audioop
import base64
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.core import ledger
from app.core.attempts import log_attempt
from app.core.gate import gate_amount
from app.core.numerals import parse_spoken_amount
from app.core.state_machine import CallSession, Payee, State, is_abort
from app.db import get_connection
from app.rail.rail_core import PayeeNotFound, create_transfer, resolve_payee, settle_after_delay
from app.sarvam.slots import extract_slots
from app.sarvam.stt import SAMPLE_RATE_HZ, transcribe_utterance
from app.sarvam.tts import BulbulClient

logger = logging.getLogger("awaazpay.bridge")

# Simple energy-based VAD tuning. RMS threshold on 16-bit PCM decoded from
# mulaw; 700ms of trailing silence after real speech ends the utterance;
# utterances shorter than 200ms are treated as noise blips, not a turn.
_SILENCE_RMS_THRESHOLD = 400
_END_OF_UTTERANCE_SILENCE_MS = 700.0
_MIN_UTTERANCE_MS = 200.0

# Demo caller resolution: the phone number stubbed to caller_id (§7 seed data
# has 2 hardcoded demo callers; a real deployment would map Vobiz's `from`
# number here instead).
DEFAULT_CALLER_ID = "demo-caller-1"

_UNKNOWN_FRAME_LOGGED = False


def _load_payees(conn, caller_id: str) -> list[Payee]:
    rows = conn.execute(
        "SELECT payee_id, display_name, masked_account FROM payees WHERE caller_id = ?",
        (caller_id,),
    ).fetchall()
    return [Payee(r["payee_id"], r["display_name"], r["masked_account"]) for r in rows]


def _extract_inbound_payload(frame: dict) -> bytes | None:
    global _UNKNOWN_FRAME_LOGGED
    media = frame.get("media")
    if isinstance(media, dict) and "payload" in media:
        return base64.b64decode(media["payload"])
    if not _UNKNOWN_FRAME_LOGGED:
        logger.warning("Unrecognized inbound media frame shape, logging raw for debugging: %s", frame)
        _UNKNOWN_FRAME_LOGGED = True
    return None


class VobizConnection:
    """Thin send-side wrapper around the raw FastAPI websocket using the
    documented Vobiz stream commands (playAudio / clearAudio / checkpoint)."""

    def __init__(self, ws: WebSocket, stream_id: str):
        self._ws = ws
        self.stream_id = stream_id

    async def play_audio(self, mulaw_bytes: bytes) -> None:
        await self._ws.send_text(
            json.dumps(
                {
                    "event": "playAudio",
                    "streamId": self.stream_id,
                    "media": {
                        "contentType": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "payload": base64.b64encode(mulaw_bytes).decode("ascii"),
                    },
                }
            )
        )

    async def clear_audio(self) -> None:
        await self._ws.send_text(json.dumps({"event": "clearAudio", "streamId": self.stream_id}))

    async def checkpoint(self, name: str) -> None:
        await self._ws.send_text(json.dumps({"event": "checkpoint", "streamId": self.stream_id, "name": name}))


class CallHandler:
    def __init__(self, ws: WebSocket, call_sid: str, stream_id: str, caller_id: str):
        self.ws = ws
        self.call_sid = call_sid
        self.conn_out = VobizConnection(ws, stream_id)
        self.caller_id = caller_id
        self.language_code: str | None = None
        self.aborted = False
        self._speak_task: asyncio.Task | None = None

        conn = get_connection()
        try:
            self.payees = _load_payees(conn, caller_id)
        finally:
            conn.close()
        self.session = CallSession(call_sid=call_sid, caller_id=caller_id, payees=self.payees)

        self.tts: BulbulClient | None = None

        self._utterance_pcm = bytearray()
        self._speech_detected = False
        self._silence_ms = 0.0
        self._processing_utterance = False

    async def start(self) -> None:
        turn = self.session.greet()
        await self._speak(turn.line)

    async def _ensure_tts(self) -> BulbulClient:
        if self.tts is None:
            self.tts = BulbulClient(target_language_code=self.language_code or "hi-IN")
            await self.tts.connect()
        return self.tts

    async def _speak(self, text: str) -> None:
        """Speaks `text`, cancellable mid-utterance by an abort (§8.2)."""
        tts = await self._ensure_tts()

        async def _run():
            async for chunk in tts.speak(text):
                await self.conn_out.play_audio(chunk)

        self._speak_task = asyncio.create_task(_run())
        try:
            await self._speak_task
        except asyncio.CancelledError:
            pass

    async def handle_inbound_audio(self, mulaw_bytes: bytes) -> None:
        """Simple energy-based VAD: accumulate decoded PCM while the caller is
        speaking, and once real speech has been seen followed by a stretch of
        silence, treat that as one complete utterance and transcribe it."""
        if self._processing_utterance:
            return  # still transcribing the previous turn; drop stray frames

        pcm = audioop.ulaw2lin(mulaw_bytes, 2)
        rms = audioop.rms(pcm, 2)
        frame_ms = len(mulaw_bytes) / (SAMPLE_RATE_HZ / 1000)

        if rms >= _SILENCE_RMS_THRESHOLD:
            self._speech_detected = True
            self._silence_ms = 0.0
            self._utterance_pcm.extend(pcm)
        elif self._speech_detected:
            self._silence_ms += frame_ms
            self._utterance_pcm.extend(pcm)

        utterance_ms = len(self._utterance_pcm) / 2 / (SAMPLE_RATE_HZ / 1000)
        if (
            self._speech_detected
            and self._silence_ms >= _END_OF_UTTERANCE_SILENCE_MS
            and utterance_ms >= _MIN_UTTERANCE_MS
        ):
            pcm_bytes = bytes(self._utterance_pcm)
            self._utterance_pcm = bytearray()
            self._speech_detected = False
            self._silence_ms = 0.0
            self._processing_utterance = True
            asyncio.create_task(self._process_utterance(pcm_bytes))

    async def _process_utterance(self, pcm_bytes: bytes) -> None:
        """`_processing_utterance` must stay True for the ENTIRE turn, not
        just through transcription - clearing it early let a second
        utterance start processing (and racing the state machine) while the
        first was still mid-flight through slot extraction and reply. That
        race was confirmed live: a payee resolved successfully, and the very
        next logged turn was still in AWAIT_PAYEE."""
        try:
            result = await transcribe_utterance(pcm_bytes, language_code=self.language_code)

            if self.language_code is None and result.language_code:
                self.language_code = result.language_code  # locked for the rest of the call (§11)

            transcript = result.transcript.strip()
            if not transcript:
                return
            if is_abort(transcript):
                await self._handle_abort()
                return
            await self._handle_final_transcript(transcript, confidence=None)
        except Exception:
            logger.exception("Utterance processing failed for call %s", self.call_sid)
        finally:
            self._processing_utterance = False

    async def _handle_abort(self) -> None:
        if self.aborted:
            return
        self.aborted = True
        if self._speak_task is not None and not self._speak_task.done():
            self._speak_task.cancel()
        await self.conn_out.clear_audio()
        turn = self.session.abort()
        conn = get_connection()
        try:
            log_attempt(conn, self.call_sid, self.caller_id, state=State.ABORTED.value, raw_transcript="[abort]")
            conn.commit()
        finally:
            conn.close()
        await self._speak(turn.line)

    async def _handle_final_transcript(self, transcript: str, confidence: float | None) -> None:
        state = self.session.state
        slots = await extract_slots(transcript, self.language_code or "hi-IN")

        conn = get_connection()
        try:
            if state == State.AWAIT_PAYEE:
                await self._handle_payee_turn(conn, transcript, slots)
            elif state == State.CONFIRM_PAYEE:
                await self._handle_yes_no(conn, transcript, slots, self.session.confirm_payee)
            elif state == State.AWAIT_AMOUNT:
                await self._handle_amount_turn(conn, transcript, slots, confidence)
            elif state == State.CONFIRM_AMOUNT:
                await self._handle_yes_no(conn, transcript, slots, self.session.confirm_amount)
            elif state == State.FINAL_CONFIRM:
                await self._handle_final_confirm(conn, transcript, slots)
            conn.commit()
        finally:
            conn.close()

    async def _handle_payee_turn(self, conn, transcript: str, slots) -> None:
        phrase = slots.payee_phrase or transcript
        resolved, ledger_hit = ledger.resolve_payee(conn, self.caller_id, phrase, self.payees)
        log_attempt(
            conn, self.call_sid, self.caller_id, state=State.AWAIT_PAYEE.value,
            raw_transcript=transcript, hypothesis=phrase, ledger_hit=ledger_hit, gate_fired=resolved is None,
        )
        self._pending_payee_phrase = phrase
        turn = self.session.submit_payee(resolved, ledger_hit=ledger_hit)
        await self._speak(turn.line)

    async def _handle_amount_turn(self, conn, transcript: str, slots, confidence: float | None) -> None:
        phrase = slots.amount_phrase or transcript
        amount_paise = parse_spoken_amount(phrase, self.language_code or "hi")

        second_parse = await extract_slots(transcript, self.language_code or "hi-IN")
        second_paise = (
            parse_spoken_amount(second_parse.amount_phrase, self.language_code or "hi")
            if second_parse.amount_phrase
            else None
        )

        gate = gate_amount(amount_paise, confidence=confidence, second_parse_paise=second_paise)
        log_attempt(
            conn, self.call_sid, self.caller_id, state=State.AWAIT_AMOUNT.value,
            raw_transcript=transcript, hypothesis=str(amount_paise), confidence=confidence,
            gate_fired=not gate.passed,
        )
        turn = self.session.submit_amount(amount_paise, gate.passed, candidates=gate.candidates)
        await self._speak(turn.line)

    async def _handle_yes_no(self, conn, transcript: str, slots, transition) -> None:
        if slots.intent == "correct" and self.session.state == State.CONFIRM_PAYEE:
            # Caller is correcting a wrong payee readback - write the ledger entry (§9.1 step 4).
            if self.session.selected_payee is not None:
                ledger.record_correction(
                    conn, self.caller_id, "payee",
                    getattr(self, "_pending_payee_phrase", transcript),
                    self.session.selected_payee.display_name,
                    resolved_id=self.session.selected_payee.payee_id,
                )
            turn = transition(False)
        else:
            yes = slots.intent == "confirm" or transcript.strip().lower() in ("haan", "yes", "haanji", "ha")
            if yes and self.session.state == State.CONFIRM_PAYEE and getattr(self, "_pending_payee_phrase", None):
                ledger.record_correction(
                    conn, self.caller_id, "payee", self._pending_payee_phrase,
                    self.session.selected_payee.display_name, resolved_id=self.session.selected_payee.payee_id,
                )
            turn = transition(yes)
        await self._speak(turn.line)

    async def _handle_final_confirm(self, conn, transcript: str, slots) -> None:
        yes = slots.intent == "confirm" or transcript.strip().lower() in ("haan", "yes", "haanji", "ha", "bhejo")
        turn = self.session.final_confirm(yes)
        await self._speak(turn.line)
        if not yes:
            return

        idempotency_key = self.call_sid
        try:
            txn_id, status = create_transfer(
                conn, self.caller_id, self.session.selected_payee.payee_id, self.session.amount_paise, idempotency_key
            )
            conn.commit()
        except PayeeNotFound:
            return
        if status == "pending":
            asyncio.create_task(settle_after_delay(get_connection, txn_id))
        done_turn = self.session.committed(txn_id)
        await self._speak(done_turn.line)

    async def close(self) -> None:
        if self.tts is not None:
            await self.tts.close()


async def handle_stream_websocket(ws: WebSocket) -> None:
    await ws.accept()
    handler: CallHandler | None = None

    try:
        while True:
            raw = await ws.receive_text()
            frame = json.loads(raw)
            event = frame.get("event")

            if event == "start":
                if handler is not None:
                    # Vobiz can send more than one "start" event over the same
                    # connection (confirmed on a live call: the conversation
                    # state kept resetting back to AWAIT_PAYEE mid-call). A
                    # second "start" is not a new call - building a fresh
                    # CallHandler here would silently wipe the in-progress
                    # CallSession and replay the greeting from scratch.
                    logger.info("Ignoring duplicate 'start' event for call %s", handler.call_sid)
                    continue
                start = frame.get("start", {})
                call_sid = start.get("callId", "unknown-call")
                stream_id = start.get("streamId", frame.get("streamId", "unknown-stream"))
                handler = CallHandler(ws, call_sid=call_sid, stream_id=stream_id, caller_id=DEFAULT_CALLER_ID)
                await handler.start()

            elif event == "media" and handler is not None:
                payload = _extract_inbound_payload(frame)
                if payload is not None:
                    await handler.handle_inbound_audio(payload)

            elif event == "stop":
                break

    except WebSocketDisconnect:
        pass
    finally:
        if handler is not None:
            await handler.close()
