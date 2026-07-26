"""M5 measurement (§13 M5). Computes and prints the five numbers for the
demo one-pager:

  1. Amount mis-heard rate, raw ASR, over telephony audio
  2. Of those mis-hears, how many were caught by the gate before commit
  3. Wrong-transfer rate (mis-heard AND committed) - target zero
  4. First-try resolution rate, call 1 vs call 2, with the ledger active
  5. Median time from call start to commit

Two data sources, used together:

  - The `attempts`/`transfers` tables, populated by real or rehearsal calls
    through the live bridge. This is always available once at least one call
    has been placed, and is what numbers 2-5 are actually computed from
    per IDEA_SCOPE.md §7 ("attempts is not optional bookkeeping").
  - `corpus/manifest.json`, if present, for number 1 (mis-heard rate against
    ground truth) - requires the recorded test corpus from §14, which this
    build cannot produce itself (needs a real phone call). If the corpus
    isn't there yet, this script says so plainly and reports what it can
    from `attempts` alone rather than silently omitting the number.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path

from app.db import get_connection

CORPUS_MANIFEST = Path(__file__).resolve().parent.parent / "corpus" / "manifest.json"


def mis_heard_rate_from_corpus() -> tuple[float, int] | None:
    if not CORPUS_MANIFEST.exists():
        return None
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    clips = [c for c in manifest if c.get("kind") == "amount"]
    if not clips:
        return None
    # Requires clips to already carry an `asr_hypothesis_paise` field filled in
    # by running them through Saaras v3 batch STT + parse_spoken_amount
    # offline - that step needs the actual recorded audio, so this only
    # activates once corpus/manifest.json has been populated post-recording.
    scored = [c for c in clips if "asr_hypothesis_paise" in c]
    if not scored:
        return None
    mis_heard = sum(1 for c in scored if c["asr_hypothesis_paise"] != c["expected_amount_paise"])
    return mis_heard / len(scored), len(scored)


def compute_from_attempts() -> dict:
    conn = get_connection()
    try:
        amount_attempts = conn.execute(
            "SELECT gate_fired FROM attempts WHERE state = 'AWAIT_AMOUNT'"
        ).fetchall()
        gate_fired_count = sum(1 for r in amount_attempts if r["gate_fired"])
        gate_total = len(amount_attempts)
        gate_catch_rate = (gate_fired_count / gate_total) if gate_total else None

        committed_wrong = conn.execute(
            """SELECT COUNT(*) AS n FROM attempts a
               JOIN transfers t ON t.call_sid = a.call_sid
               WHERE a.gate_fired = 1 AND t.status = 'success'"""
        ).fetchone()["n"]
        total_committed = conn.execute("SELECT COUNT(*) AS n FROM transfers WHERE status = 'success'").fetchone()["n"]
        wrong_transfer_rate = (committed_wrong / total_committed) if total_committed else 0.0

        payee_attempts = conn.execute(
            "SELECT caller_id, ledger_hit, created_at FROM attempts WHERE state = 'AWAIT_PAYEE' ORDER BY created_at"
        ).fetchall()
        by_caller: dict[str, list] = {}
        for row in payee_attempts:
            by_caller.setdefault(row["caller_id"], []).append(row["ledger_hit"])
        first_try_rates = {}
        for caller_id, hits in by_caller.items():
            if len(hits) >= 2:
                first_try_rates[caller_id] = {"call_1_ledger_hit": bool(hits[0]), "call_2_ledger_hit": bool(hits[1])}

        commit_times = conn.execute(
            """SELECT a.created_at AS start_ts, t.committed_at AS commit_ts
               FROM transfers t
               JOIN attempts a ON a.call_sid = t.call_sid
               WHERE t.status = 'success'
               GROUP BY t.txn_id"""
        ).fetchall()
        durations = []
        for row in commit_times:
            try:
                start = datetime.fromisoformat(row["start_ts"])
                end = datetime.fromisoformat(row["commit_ts"])
                durations.append((end - start).total_seconds())
            except (TypeError, ValueError):
                continue
        median_seconds = statistics.median(durations) if durations else None

        return {
            "gate_total_amount_attempts": gate_total,
            "gate_fired_count": gate_fired_count,
            "gate_catch_rate": gate_catch_rate,
            "wrong_transfer_rate": wrong_transfer_rate,
            "committed_wrong_count": committed_wrong,
            "total_committed": total_committed,
            "ledger_first_try_by_caller": first_try_rates,
            "median_seconds_to_commit": median_seconds,
        }
    finally:
        conn.close()


def main() -> None:
    print("=== AWAAZ-PAY M5 measurement ===\n")

    corpus_result = mis_heard_rate_from_corpus()
    if corpus_result is None:
        print("1. Amount mis-heard rate (raw ASR): NOT AVAILABLE")
        print("   corpus/manifest.json is missing or not yet scored against Saaras v3 batch STT.")
        print("   This requires the recorded 8kHz telephony test corpus from IDEA_SCOPE.md §14,")
        print("   which needs a real phone call to produce - flagged, not silently skipped.\n")
    else:
        rate, n = corpus_result
        print(f"1. Amount mis-heard rate (raw ASR, n={n} clips): {rate:.1%}\n")

    stats = compute_from_attempts()

    if stats["gate_total_amount_attempts"] == 0:
        print("2-5. NOT AVAILABLE: no attempts logged yet. Place at least one call (or run the")
        print("     rehearsal script) so the bridge populates the attempts/transfers tables.\n")
        return

    print(
        f"2. Gate catch rate: {stats['gate_fired_count']}/{stats['gate_total_amount_attempts']} "
        f"amount attempts gated ({stats['gate_catch_rate']:.1%})"
    )
    print(
        f"3. Wrong-transfer rate: {stats['committed_wrong_count']}/{stats['total_committed']} "
        f"committed transfers were gate-fired-then-committed ({stats['wrong_transfer_rate']:.1%}) - target 0%"
    )
    print("4. First-try ledger resolution, call 1 vs call 2, per caller:")
    if not stats["ledger_first_try_by_caller"]:
        print("   NOT AVAILABLE: need at least 2 payee-resolution attempts for the same caller_id.")
    else:
        for caller_id, rates in stats["ledger_first_try_by_caller"].items():
            print(f"   {caller_id}: call 1 ledger_hit={rates['call_1_ledger_hit']}, call 2 ledger_hit={rates['call_2_ledger_hit']}")
    if stats["median_seconds_to_commit"] is not None:
        print(f"5. Median time from call start to commit: {stats['median_seconds_to_commit']:.1f}s")
    else:
        print("5. Median time from call start to commit: NOT AVAILABLE (no successful transfers yet)")


if __name__ == "__main__":
    main()
