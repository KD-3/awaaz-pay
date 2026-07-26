"""Seeds 6 payees across 2 hardcoded demo caller IDs (§7)."""
from datetime import datetime, timezone

from app.db import db_session, init_db

CALLER_A = "demo-caller-1"
CALLER_B = "demo-caller-2"

PAYEES = [
    (CALLER_A, "payee-sunita", "Sunita", "wife", "XXXX-XXXX-4521"),
    (CALLER_A, "payee-ramesh", "Ramesh", "brother", "XXXX-XXXX-7789"),
    (CALLER_A, "payee-manoj", "Manoj", "father", "XXXX-XXXX-1102"),
    (CALLER_B, "payee-geeta", "Geeta", "wife", "XXXX-XXXX-3390"),
    (CALLER_B, "payee-suresh", "Suresh", "brother", "XXXX-XXXX-6644"),
    (CALLER_B, "payee-anita", "Anita", "sister", "XXXX-XXXX-9981"),
]


def seed() -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        for caller_id in (CALLER_A, CALLER_B):
            conn.execute(
                """INSERT INTO callers (caller_id, first_seen, last_seen, language, call_count)
                   VALUES (?, ?, ?, NULL, 0)
                   ON CONFLICT(caller_id) DO NOTHING""",
                (caller_id, now, now),
            )
        for caller_id, payee_id, display_name, relationship, masked_account in PAYEES:
            conn.execute(
                """INSERT INTO payees (payee_id, caller_id, display_name, relationship, masked_account)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(payee_id) DO NOTHING""",
                (payee_id, caller_id, display_name, relationship, masked_account),
            )
    print(f"Seeded {len(PAYEES)} payees across 2 callers: {CALLER_A}, {CALLER_B}")


if __name__ == "__main__":
    seed()
