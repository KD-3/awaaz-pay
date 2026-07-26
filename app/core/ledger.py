"""The correction ledger (§9) - the differentiator. Worth more rubric points
than audio quality: build and protect this above everything except a working
phone call (per IDEA_SCOPE.md §13 M3).

Governance, restated because it is what makes this L4+ rather than a cache:
- Entries are scoped to one caller_id. Never shared, never global.
- A ledger hit bypasses the *gate*, not the *confirmation*. Money never moves
  without a readback.
- A caller can overwrite an entry by correcting again. Last correction wins,
  hit_count resets.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from rapidfuzz import fuzz

from app.core.state_machine import Payee

LEDGER_MATCH_THRESHOLD = 85
DIRECT_MATCH_THRESHOLD = 75

# Minimal best-effort Devanagari -> Latin transliteration for fuzzy-match
# comparison purposes only (not for TTS/display). Covers common independent
# vowels, matras and consonants seen in payee names and amount phrases.
_DEVANAGARI_MAP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ं": "n", "ँ": "n", "ः": "h",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "़": "", "्": "",
}

_PUNCT_RE = re.compile(r"[^\w\s]")


def _transliterate_devanagari(text: str) -> str:
    return "".join(_DEVANAGARI_MAP.get(ch, ch) for ch in text)


def normalize_hypothesis(text: str) -> str:
    text = _transliterate_devanagari(text)
    text = text.lower().strip()
    text = _PUNCT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass
class LedgerMatch:
    correction_id: int
    corrected_to: str
    resolved_id: str | None
    hit_count: int


def _fuzzy_match_corrections(
    conn: sqlite3.Connection, caller_id: str, entity_type: str, normalized_heard: str, threshold: int
) -> LedgerMatch | None:
    rows = conn.execute(
        "SELECT id, heard_text, corrected_to, resolved_id, hit_count FROM corrections "
        "WHERE caller_id = ? AND entity_type = ?",
        (caller_id, entity_type),
    ).fetchall()

    best_row = None
    best_score = 0.0
    for row in rows:
        score = fuzz.partial_ratio(normalized_heard, row["heard_text"])
        if score > best_score:
            best_score = score
            best_row = row

    if best_row is None or best_score < threshold:
        return None
    return LedgerMatch(
        correction_id=best_row["id"],
        corrected_to=best_row["corrected_to"],
        resolved_id=best_row["resolved_id"],
        hit_count=best_row["hit_count"],
    )


def touch_ledger_hit(conn: sqlite3.Connection, correction_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE corrections SET hit_count = hit_count + 1, last_used_at = ? WHERE id = ?",
        (now, correction_id),
    )


def record_correction(
    conn: sqlite3.Connection,
    caller_id: str,
    entity_type: str,
    heard_text: str,
    corrected_to: str,
    resolved_id: str | None = None,
) -> None:
    """Write (or overwrite) a correction. Last correction wins; hit_count resets (§9.2)."""
    normalized = normalize_hypothesis(heard_text)
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT id FROM corrections WHERE caller_id = ? AND entity_type = ? AND heard_text = ?",
        (caller_id, entity_type, normalized),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE corrections SET corrected_to = ?, resolved_id = ?, hit_count = 1, last_used_at = ? WHERE id = ?",
            (corrected_to, resolved_id, now, existing["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO corrections
               (caller_id, entity_type, heard_text, corrected_to, resolved_id, hit_count, created_at, last_used_at)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (caller_id, entity_type, normalized, corrected_to, resolved_id, now, now),
        )


def resolve_payee(
    conn: sqlite3.Connection,
    caller_id: str,
    payee_phrase: str,
    payees: list[Payee],
    ledger_threshold: int = LEDGER_MATCH_THRESHOLD,
    direct_threshold: int = DIRECT_MATCH_THRESHOLD,
) -> tuple[Payee | None, bool]:
    """Returns (resolved_payee_or_None, ledger_hit). Ledger is consulted before
    the normal gate path, per §9.1."""
    normalized = normalize_hypothesis(payee_phrase)

    ledger_match = _fuzzy_match_corrections(conn, caller_id, "payee", normalized, ledger_threshold)
    if ledger_match and ledger_match.resolved_id:
        payee = next((p for p in payees if p.payee_id == ledger_match.resolved_id), None)
        if payee is not None:
            touch_ledger_hit(conn, ledger_match.correction_id)
            return payee, True

    best_payee = None
    best_score = 0.0
    for payee in payees:
        score = fuzz.partial_ratio(normalized, normalize_hypothesis(payee.display_name))
        if score > best_score:
            best_score = score
            best_payee = payee

    if best_payee is not None and best_score >= direct_threshold:
        return best_payee, False

    return None, False
