"""Demo reset script (§M6). Wipes attempts and transfers, preserves seeded
payees. Corrections are preserved by default (needed for the "second call
resolves first-try" beat) - pass --clear-corrections to run the "first call,
gate fires" beat instead. Run both against a fresh DB to rehearse the full
demo arc.
"""
import argparse

from app.db import get_connection, init_db
from app.seed import seed


def reset(clear_corrections: bool) -> None:
    init_db()
    seed()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM attempts")
        conn.execute("DELETE FROM transfers")
        if clear_corrections:
            conn.execute("DELETE FROM corrections")
        conn.commit()
    finally:
        conn.close()
    print("Reset complete. Payees preserved." + (" Corrections cleared." if clear_corrections else " Corrections preserved."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clear-corrections",
        action="store_true",
        help="Also wipe the corrections table (run the 'first call, gate fires' beat from scratch).",
    )
    args = parser.parse_args()
    reset(clear_corrections=args.clear_corrections)
