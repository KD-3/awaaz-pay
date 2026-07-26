import sqlite3
from contextlib import contextmanager

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS callers (
    caller_id TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    language TEXT,
    call_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payees (
    payee_id TEXT PRIMARY KEY,
    caller_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    relationship TEXT,
    masked_account TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('payee', 'amount')),
    heard_text TEXT NOT NULL,
    corrected_to TEXT NOT NULL,
    resolved_id TEXT,
    hit_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    caller_id TEXT NOT NULL,
    state TEXT NOT NULL,
    raw_transcript TEXT,
    hypothesis TEXT,
    confidence REAL,
    ledger_hit INTEGER NOT NULL DEFAULT 0,
    gate_fired INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transfers (
    txn_id TEXT PRIMARY KEY,
    call_sid TEXT NOT NULL,
    caller_id TEXT NOT NULL,
    payee_id TEXT NOT NULL,
    amount_paise INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'aborted')),
    committed_at TEXT,
    aborted_at TEXT,
    abort_state TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
