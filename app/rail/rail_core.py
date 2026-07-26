"""Plain functions backing the mocked rail (§12) - shared by the HTTP router
(mock_rail.py, for curl/judge probing) and the telephony bridge (which calls
these directly in-process rather than looping back over HTTP)."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from app import razorpay_client

logger = logging.getLogger("awaazpay.rail")

PENDING_DELAY_SECONDS = 2.0


class PayeeNotFound(Exception):
    pass


def resolve_payee(conn: sqlite3.Connection, caller_id: str, payee_id: str) -> dict:
    row = conn.execute(
        "SELECT payee_id, display_name, masked_account FROM payees WHERE payee_id = ? AND caller_id = ?",
        (payee_id, caller_id),
    ).fetchone()
    if row is None:
        raise PayeeNotFound(payee_id)
    return {"payee_id": row["payee_id"], "name": row["display_name"], "masked_account": row["masked_account"]}


def create_transfer(
    conn: sqlite3.Connection, caller_id: str, payee_id: str, amount_paise: int, idempotency_key: str
) -> tuple[str, str]:
    """Returns (txn_id, status). Idempotent on (idempotency_key, payee_id, amount_paise)."""
    existing = conn.execute(
        "SELECT txn_id, status FROM transfers WHERE call_sid = ? AND payee_id = ? AND amount_paise = ?",
        (idempotency_key, payee_id, amount_paise),
    ).fetchone()
    if existing is not None:
        return existing["txn_id"], existing["status"]

    payee_row = conn.execute(
        "SELECT display_name FROM payees WHERE payee_id = ? AND caller_id = ?", (payee_id, caller_id)
    ).fetchone()
    if payee_row is None:
        raise PayeeNotFound(payee_id)

    try:
        txn_id = razorpay_client.create_order(
            amount_paise, receipt=idempotency_key, notes={"caller_id": caller_id, "payee": payee_row["display_name"]}
        )
    except Exception:
        logger.exception("Razorpay order creation failed, falling back to a local txn_id")
        txn_id = f"txn_{uuid.uuid4().hex[:12]}"

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO transfers (txn_id, call_sid, caller_id, payee_id, amount_paise, status, committed_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
        (txn_id, idempotency_key, caller_id, payee_id, amount_paise, now),
    )
    return txn_id, "pending"


def get_status(conn: sqlite3.Connection, txn_id: str) -> str | None:
    row = conn.execute("SELECT status FROM transfers WHERE txn_id = ?", (txn_id,)).fetchone()
    return row["status"] if row else None


async def settle_after_delay(get_conn, txn_id: str) -> None:
    await asyncio.sleep(PENDING_DELAY_SECONDS)
    conn = get_conn()
    try:
        conn.execute("UPDATE transfers SET status = 'success' WHERE txn_id = ?", (txn_id,))
        conn.commit()
    finally:
        conn.close()
