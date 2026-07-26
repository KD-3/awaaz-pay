import os
import tempfile

import pytest

from app.core.ledger import record_correction, resolve_payee
from app.core.state_machine import Payee

SUNITA = Payee("payee-sunita", "Sunita", "XXXX-XXXX-4521")
RAMESH = Payee("payee-ramesh", "Ramesh", "XXXX-XXXX-7789")
MANOJ = Payee("payee-manoj", "Manoj", "XXXX-XXXX-1102")
PAYEES = [SUNITA, RAMESH, MANOJ]


@pytest.fixture
def conn():
    from app.db import get_connection, init_db

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = path
    import importlib

    import app.config as config_module
    importlib.reload(config_module)
    import app.db as db_module
    importlib.reload(db_module)

    db_module.init_db()
    connection = db_module.get_connection()
    yield connection
    connection.close()
    os.remove(path)


def test_call_one_gate_fires_then_correction_written(conn):
    # ASR mis-hears "Sunita" as "suneetha" - too dissimilar for a direct match
    resolved, ledger_hit = resolve_payee(conn, "demo-caller-1", "suneetha", PAYEES)
    assert resolved is None
    assert ledger_hit is False

    # caller narrows/confirms it was actually Sunita -> a correction gets written
    record_correction(conn, "demo-caller-1", "payee", "suneetha", "Sunita", resolved_id=SUNITA.payee_id)
    conn.commit()

    row = conn.execute(
        "SELECT heard_text, corrected_to, resolved_id, hit_count FROM corrections WHERE caller_id = ?",
        ("demo-caller-1",),
    ).fetchone()
    assert row["heard_text"] == "suneetha"
    assert row["corrected_to"] == "Sunita"
    assert row["resolved_id"] == SUNITA.payee_id
    assert row["hit_count"] == 1


def test_call_two_same_utterance_resolves_first_try_via_ledger(conn):
    record_correction(conn, "demo-caller-1", "payee", "suneetha", "Sunita", resolved_id=SUNITA.payee_id)
    conn.commit()

    resolved, ledger_hit = resolve_payee(conn, "demo-caller-1", "suneetha", PAYEES)

    assert resolved is not None
    assert resolved.payee_id == SUNITA.payee_id
    assert ledger_hit is True

    row = conn.execute(
        "SELECT hit_count FROM corrections WHERE caller_id = ? AND heard_text = ?",
        ("demo-caller-1", "suneetha"),
    ).fetchone()
    assert row["hit_count"] == 2


def test_ledger_entries_are_scoped_to_one_caller(conn):
    record_correction(conn, "demo-caller-1", "payee", "suneetha", "Sunita", resolved_id=SUNITA.payee_id)
    conn.commit()

    resolved, ledger_hit = resolve_payee(conn, "demo-caller-2", "suneetha", PAYEES)
    assert resolved is None
    assert ledger_hit is False


def test_correction_overwrite_resets_hit_count(conn):
    record_correction(conn, "demo-caller-1", "payee", "suneetha", "Sunita", resolved_id=SUNITA.payee_id)
    resolve_payee(conn, "demo-caller-1", "suneetha", PAYEES)  # bumps hit_count to 2
    conn.commit()

    record_correction(conn, "demo-caller-1", "payee", "suneetha", "Ramesh", resolved_id=RAMESH.payee_id)
    conn.commit()

    row = conn.execute(
        "SELECT corrected_to, resolved_id, hit_count FROM corrections WHERE caller_id = ? AND heard_text = ?",
        ("demo-caller-1", "suneetha"),
    ).fetchone()
    assert row["corrected_to"] == "Ramesh"
    assert row["resolved_id"] == RAMESH.payee_id
    assert row["hit_count"] == 1


def test_direct_match_resolves_close_pronunciation_without_ledger(conn):
    resolved, ledger_hit = resolve_payee(conn, "demo-caller-1", "sunita", PAYEES)
    assert resolved is not None
    assert resolved.payee_id == SUNITA.payee_id
    assert ledger_hit is False
