"""Logging for the `attempts` table (§7) - not optional bookkeeping. The M5
measurement numbers (mis-hear rate, gate catch rate, ledger first-try rate)
are computed from this table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def log_attempt(
    conn: sqlite3.Connection,
    call_sid: str,
    caller_id: str,
    state: str,
    raw_transcript: str | None = None,
    hypothesis: str | None = None,
    confidence: float | None = None,
    ledger_hit: bool = False,
    gate_fired: bool = False,
) -> None:
    conn.execute(
        """INSERT INTO attempts
           (call_sid, caller_id, state, raw_transcript, hypothesis, confidence, ledger_hit, gate_fired, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            call_sid,
            caller_id,
            state,
            raw_transcript,
            hypothesis,
            confidence,
            1 if ledger_hit else 0,
            1 if gate_fired else 0,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
