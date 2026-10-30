"""Database abstraction: SQLite (default) or PostgreSQL via psycopg3.

Configuration:
    DATABASE_TYPE=postgres  (default: "sqlite")
    DATABASE_PATH           (file path for SQLite, connection URL for PostgreSQL)

Both adapters implement the same minimal surface:
  - execute(sql, params) -> cursor
  - cursor.fetchone() / fetchall() -> row (dict-like)
  - cursor.lastrowid (SQLite) / RETURNING (PostgreSQL wrappers)
  - close()
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request

from app.schema import SCHEMA_SQL, SCHEMA_SQL_POSTGRES


def _schema_sql(dialect: str) -> str:
    """Return DDL for the target database."""
    if dialect == "postgres":
        return SCHEMA_SQL_POSTGRES
    return SCHEMA_SQL


# ---------------------------------------------------------------------------
# SQLite connector (existing, unchanged)
# ---------------------------------------------------------------------------


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


# ---------------------------------------------------------------------------
# PostgreSQL connector (lazy import)
# ---------------------------------------------------------------------------


def connect_postgres(url: str) -> object:
    """Lazy-import psycopg3 and connect with dict-row factory."""
    import psycopg  # type: ignore[import-untyped]
    import psycopg.rows  # type: ignore[import-untyped]

    conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)  # type: ignore[arg-type]
    conn.execute("SET client_min_messages TO WARNING")
    return conn


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _db_type() -> str:
    """Read DATABASE_TYPE from environment (default: 'sqlite')."""
    return os.environ.get("DATABASE_TYPE", "sqlite")


def _should_use_postgres() -> bool:
    return _db_type() == "postgres"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def init_db(path: Path | str, database_type: str = "sqlite") -> None:
    """Create tables.  Accepts a file path (SQLite) or a connection URL (Postgres)."""
    if database_type == "postgres":
        conn = connect_postgres(str(path))
        try:
            conn.execute(_schema_sql("postgres"))
        finally:
            conn.close()
    else:
        conn = connect(path)
        try:
            conn.executescript(_schema_sql("sqlite"))
            conn.execute("PRAGMA journal_mode = WAL")
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Transaction (generic — rollback / commit on both adapters)
# ---------------------------------------------------------------------------


@contextmanager
def transaction(conn: object) -> Iterator[object]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# FastAPI dependency (connection per request)
# ---------------------------------------------------------------------------


def get_db(request: Request) -> Iterator[object]:
    path = request.app.state.db_path
    if _should_use_postgres():
        yield connect_postgres(str(path))
    else:
        yield connect(path)


def close_db(conn: object) -> None:
    conn.close()
