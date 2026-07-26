"""Bulbul v3 TTS client (§6, §10). Outputs mulaw to match Vobiz's wire format
directly - no re-encoding needed before it goes back over the bridge.

Uses the REST `convert()` call, not the WebSocket streaming socket. The
streaming socket's `configure()` only accepts `output_audio_codec="mp3"`
(confirmed by reading the installed SDK's docstring - "currently supports
MP3 only"); silently passing "mulaw" there does not error, it is just
ignored, and the bytes that come back are MP3-compressed - sending those
straight to Vobiz as if they were raw mulaw produced audible static on a
live call. The REST endpoint's `output_audio_codec` genuinely supports
"mulaw" with `speech_sample_rate=8000` (confirmed against the live API: the
returned bytes start with 0xFF padding, mulaw's silence value, with no
RIFF/WAV header). Bot lines are short, complete, pre-composed strings, so
losing token-level streaming costs nothing here.
"""
from __future__ import annotations

import base64

import httpx

from app.config import settings
from app.sarvam._http import with_retry

SAMPLE_RATE_HZ = 8000
DEFAULT_SPEAKER = "shubh"
_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_FRAME_BYTES = 320  # 40ms of 8kHz mulaw per outbound frame


class BulbulClient:
    def __init__(self, target_language_code: str = "hi-IN", dict_id: str | None = None):
        self._target_language_code = target_language_code
        self._dict_id = dict_id
        self._http = httpx.AsyncClient(timeout=15.0)

    async def connect(self) -> None:
        pass  # no persistent connection needed for the REST path

    async def speak(self, text: str):
        """Synthesizes `text` and yields raw mulaw audio in small frames."""
        payload = {
            "text": text,
            "target_language_code": self._target_language_code,
            "model": "bulbul:v3",
            "speaker": DEFAULT_SPEAKER,
            "output_audio_codec": "mulaw",
            "speech_sample_rate": SAMPLE_RATE_HZ,
        }
        if self._dict_id:
            payload["dict_id"] = self._dict_id

        resp = await with_retry(
            lambda: self._http.post(
                _TTS_URL,
                headers={"api-subscription-key": settings.sarvam_api_key},
                json=payload,
            )
        )
        resp.raise_for_status()
        audio_b64 = resp.json()["audios"][0]
        mulaw_bytes = base64.b64decode(audio_b64)

        for offset in range(0, len(mulaw_bytes), _FRAME_BYTES):
            yield mulaw_bytes[offset : offset + _FRAME_BYTES]

    async def close(self) -> None:
        await self._http.aclose()


def seed_pronunciation_dict(payee_names: list[str]) -> str | None:
    """Builds a Bulbul pronunciation dictionary from the seeded payee names
    (§10) so the TTS doesn't mangle the name it's asking the caller to
    confirm. Best-effort: if the dictionary API call fails or isn't reachable
    (e.g. no network during offline dev), returns None and callers fall back
    to plain speaker pronunciation - this is an explicitly cuttable M4 item
    per IDEA_SCOPE.md §13, not a hard dependency of the call flow."""
    if not settings.sarvam_api_key:
        return None
    try:
        resp = httpx.post(
            "https://api.sarvam.ai/text-to-speech/dictionary",
            headers={"api-subscription-key": settings.sarvam_api_key},
            json={"entries": [{"word": name, "pronunciation": name} for name in payee_names]},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("dict_id")
    except Exception:
        return None
