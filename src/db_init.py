"""
db_init.py — Database initialization entry point.

Design goals
------------
* Idempotent: safe to call on every container start or Streamlit rerun.
* Zero side-effects when the schema already exists (CREATE TABLE IF NOT EXISTS).
* Works on Streamlit Cloud (no pre-existing file required).
* Decoupled: can be called standalone (e.g. from main_api.py startup) or
  via the shared DataManager instance used by the Streamlit app.
* Thread-safe for concurrent access: SQLite WAL mode + context managers.

Initialization is guaranteed to run exactly once per process by the
module-level _initialized flag, which avoids redundant PRAGMA lookups on
every Streamlit script rerun.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

# ── Module-level guard ────────────────────────────────────────────────────────
# Set to True after the first successful init in this process/container.
# Streamlit reruns the top-level script frequently; this prevents redundant
# PRAGMA calls on every rerun without needing @st.cache_resource.
_initialized: bool = False


# ── Configurable path (override via env var for tests or staging) ─────────────
DB_PATH: str = os.environ.get("PULSE_DB_PATH", "data/pulse.db")


def ensure_initialized(db_path: str = DB_PATH) -> None:
    """
    Public entry point. Call once at app startup.

    * Creates the ``data/`` directory if missing.
    * Creates all tables and indexes inside a single atomic transaction.
    * Applies any pending column migrations for existing databases.
    * Sets SQLite WAL mode for safer concurrent reads.

    Safe to call multiple times — subsequent calls return immediately.
    """
    global _initialized
    if _initialized:
        return

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    logger.info(f"Initializing database at: {db_path}")

    try:
        _create_schema(db_path)
        _initialized = True
        logger.info("Database initialization complete.")
    except Exception:
        logger.exception("Database initialization failed.")
        raise


def _create_schema(db_path: str) -> None:
    """
    Creates all tables, indexes, and migrations inside one transaction.
    All statements use IF NOT EXISTS / ALTER TABLE only-if-missing guards.
    """
    with sqlite3.connect(db_path) as conn:
        # WAL mode: readers don't block writers; safe for Streamlit's
        # multi-thread executor + background pipeline thread.
        conn.execute("PRAGMA journal_mode=WAL")

        # ── Core review storage ───────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id           TEXT PRIMARY KEY,
                platform     TEXT,
                rating       INTEGER,
                title        TEXT,
                review_text  TEXT,
                date         TEXT,
                raw_data     TEXT,
                UNIQUE(platform, review_text, date)
            )
        """)

        # ── Incremental scrape coverage tracker ───────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_history (
                platform     TEXT,
                scrape_date  TEXT,
                PRIMARY KEY (platform, scrape_date)
            )
        """)

        # ── Pipeline run lifecycle table ──────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                run_id             TEXT PRIMARY KEY,
                status             TEXT NOT NULL DEFAULT 'triggered',
                trigger_source     TEXT NOT NULL DEFAULT 'manual',
                triggered_by       TEXT,
                start_date         TEXT,
                end_date           TEXT,
                triggered_at       TEXT,
                started_at         TEXT,
                completed_at       TEXT,
                reviews_processed  INTEGER,
                themes_identified  INTEGER,
                error_message      TEXT
            )
        """)

        # ── Column migrations (backward-compat for older DB files) ────────────
        _apply_migrations(conn)

        # ── Indexes ───────────────────────────────────────────────────────────
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_history_triggered
            ON run_history (triggered_at DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_history_status
            ON run_history (status)
        """)

        conn.commit()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """
    Non-destructive schema migrations: add columns that are missing from
    databases created by older versions of the app.
    Only adds; never drops or renames existing columns.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(run_history)")}
    pending = [
        ("status",           "TEXT NOT NULL DEFAULT 'succeeded'"),
        ("trigger_source",   "TEXT NOT NULL DEFAULT 'manual'"),
        ("triggered_by",     "TEXT"),
        ("triggered_at",     "TEXT"),
        ("started_at",       "TEXT"),
        ("completed_at",     "TEXT"),
        ("error_message",    "TEXT"),
    ]
    for col, col_def in pending:
        if col not in existing:
            conn.execute(f"ALTER TABLE run_history ADD COLUMN {col} {col_def}")
            logger.info(f"Migration applied: added column run_history.{col}")
