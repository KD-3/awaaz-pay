"""Saaras v3 STT client (§6). Uses `codemix` mode - Hindi in Devanagari with
English words preserved in Latin, which is what a Hinglish amount phrase
actually looks like on the wire.

Uses the REST batch endpoint, not the streaming WebSocket. The streaming
socket was tried first (per-chunk `AudioData` messages, `input_audio_codec`
declared at connect time, both matching the SDK's own pydantic constraints)
and still closed the connection after 1-2 messages with zero transcript
events every time, on live calls and in isolated tests with both silence and
real synthesized speech - confirmed not a content or VAD issue by feeding a
known-good full utterance and getting nothing back even after an explicit
flush(). The REST endpoint transcribes the same audio correctly on the first
try. Given a phone call is naturally turn-based (the caller pauses between
utterances), batching a whole utterance to REST once local silence-detection
decides the caller has stopped talking (see app/telephony/bridge.py's simple
energy-based VAD) is a reliable trade of a few hundred ms of latency for
something that actually works.

Confidence field: the REST response includes `language_probability`, which is
confidence in LANGUAGE DETECTION, not confidence in transcription accuracy -
using it as the §8.4 amount-confidence gate would be conflating two different
things, so it's surfaced but not fed into gate.py. The fallback gate
(double-parse + plausibility + round-number) remains the real mechanism.
"""
from __future__ import annotations

import io
import wave
from dataclasses import dataclass

import httpx

from app.config import settings
from app.sarvam._http import with_retry

SAMPLE_RATE_HZ = 8000  # what Vobiz gives us, and what we tell the WAV header
DEFAULT_LANGUAGE_CODE = "hi-IN"  # locked demo language subset is Hindi + Hinglish (§3)
_STT_URL = "https://api.sarvam.ai/speech-to-text"


@dataclass
class TranscriptResult:
    transcript: str
    language_code: str | None
    language_probability: float | None


def mulaw_to_wav_bytes(mulaw_bytes: bytes) -> bytes:
    """Wraps raw 8kHz mulaw PCM (after audioop decode) into an in-memory WAV
    file. Callers pass already-decoded linear PCM; see bridge.py's utterance
    buffer, which accumulates decoded PCM directly."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE_HZ)
        wf.writeframes(mulaw_bytes)
    return buf.getvalue()


async def transcribe_utterance(pcm16_bytes: bytes, language_code: str | None = None) -> TranscriptResult:
    """Transcribes one complete utterance (linear16 PCM, 8kHz, mono) via the
    REST batch endpoint."""
    wav_bytes = mulaw_to_wav_bytes(pcm16_bytes)
    form_data = {"model": "saaras:v3", "mode": "codemix"}
    if language_code:
        form_data["language_code"] = language_code
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await with_retry(
            lambda: http.post(
                _STT_URL,
                headers={"api-subscription-key": settings.sarvam_api_key},
                files={"file": ("utterance.wav", wav_bytes, "audio/wav")},
                data=form_data,
            )
        )
    resp.raise_for_status()
    data = resp.json()
    return TranscriptResult(
        transcript=data.get("transcript", "") or "",
        language_code=data.get("language_code"),
        language_probability=data.get("language_probability"),
    )
