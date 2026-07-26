"""Sarvam-30B slot extraction (§11). Slot filler only - the governing rule
(IDEA_SCOPE.md §5.1) is that no LLM output can trigger a commit. This module
returns structured JSON and nothing else; app/core/state_machine.py is the
only thing that decides whether to advance, re-ask, or commit.

Uses the REST endpoint directly, not the `sarvamai` SDK's `chat.completions()`
- the installed SDK version's method signature has no `response_format`
parameter at all (confirmed by reading its source), even though the raw REST
API accepts and honors it (confirmed directly against the live API). Also
async via httpx rather than the SDK's sync client, since this is called from
inside the call-handling event loop and a blocking HTTP call there would
stall audio processing for the whole request round-trip.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.config import settings
from app.sarvam._http import with_retry

_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"

_SYSTEM_PROMPT = """You extract three things from a transcript of a phone call about sending money: who the money is for, how much, and whether the caller is confirming, correcting, or aborting. You do not decide anything. You return JSON.

Return strict JSON only, no prose, no markdown fences:
{"payee_phrase": string or null, "amount_phrase": string or null, "intent": one of "provide", "confirm", "correct", "abort", "unclear"}

payee_phrase and amount_phrase must be copied verbatim from the transcript, exactly as spoken. Do not translate them, do not convert number words to another language, do not normalize or paraphrase them.

Respond in the language the caller used. Proper nouns stay exactly as spoken. Never switch to English mid-call."""


@dataclass
class SlotResult:
    payee_phrase: str | None
    amount_phrase: str | None
    intent: str


async def extract_slots(transcript: str, language_code: str = "hi-IN") -> SlotResult:
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await with_retry(
            lambda: http.post(
                _CHAT_URL,
                headers={"api-subscription-key": settings.sarvam_api_key},
                json={
                    "model": settings.sarvam_slot_model,
                    "temperature": 0,
                    "reasoning_effort": None,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": transcript},
                    ],
                },
            )
        )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return SlotResult(payee_phrase=None, amount_phrase=None, intent="unclear")

    return SlotResult(
        payee_phrase=parsed.get("payee_phrase"),
        amount_phrase=parsed.get("amount_phrase"),
        intent=parsed.get("intent", "unclear"),
    )
