"""Small SQLite access layer; all paths are local to this WattWise install."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS appliance_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    appliances_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS household_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('prepaid', 'postpaid')),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('prepaid', 'postpaid')),
    request_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS analysis_history_user_created
    ON analysis_history(user_id, created_at DESC);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    db_path = path or current_app.config["DATABASE_PATH"]
    connection = sqlite3.connect(db_path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(app) -> None:
    db_path = app.config["DATABASE_PATH"]
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=5)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()
