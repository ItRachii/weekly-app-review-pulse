import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import os

logger = logging.getLogger(__name__)

class DataManager:
    """
    Manages review persistence in SQLite.
    """
    DB_PATH = "data/pulse.db"

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    platform TEXT,
                    rating INTEGER,
                    title TEXT,
                    review_text TEXT,
                    date TEXT,
                    raw_data TEXT,
                    UNIQUE(platform, review_text, date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    platform TEXT,
                    scrape_date TEXT,
                    PRIMARY KEY (platform, scrape_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    run_id           TEXT PRIMARY KEY,
                    status           TEXT NOT NULL DEFAULT 'triggered',
                    trigger_source   TEXT NOT NULL DEFAULT 'manual',
                    triggered_by     TEXT,
                    start_date       TEXT,
                    end_date         TEXT,
                    triggered_at     TEXT,
                    started_at       TEXT,
                    completed_at     TEXT,
                    reviews_processed INTEGER,
                    themes_identified INTEGER,
                    error_message    TEXT
                )
            """)
            # Migrate existing rows: add missing columns if upgrading from old schema
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(run_history)").fetchall()}
            migrations = [
                ("status",            "TEXT NOT NULL DEFAULT 'succeeded'"),
                ("trigger_source",    "TEXT NOT NULL DEFAULT 'manual'"),
                ("triggered_by",      "TEXT"),
                ("triggered_at",      "TEXT"),
                ("started_at",        "TEXT"),
                ("completed_at",      "TEXT"),
                ("error_message",     "TEXT"),
            ]
            for col, col_def in migrations:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE run_history ADD COLUMN {col} {col_def}")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_history_triggered
                ON run_history (triggered_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_history_status
                ON run_history (status)
            """)
            conn.commit()

    def get_cached_reviews(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieves reviews within the specified date range."""
        logger.debug(f"Querying cache for range: {start_date.isoformat()} to {end_date.isoformat()}")
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT * FROM reviews 
                WHERE date >= ? AND date <= ?
            """
            cursor = conn.execute(query, (start_date.isoformat(), end_date.isoformat()))
            rows = cursor.fetchall()
            
            reviews = [dict(row) for row in rows]
            logger.debug(f"Cache result: Found {len(reviews)} reviews.")
            return reviews

    def save_reviews(self, reviews: List[Dict[str, Any]]) -> int:
        """Saves new reviews to the database, returning the count of saved records."""
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError ("Type %s not serializable" % type(obj))

        saved_count = 0
        with sqlite3.connect(self.DB_PATH) as conn:
            for r in reviews:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO reviews (platform, rating, title, review_text, date, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        r['platform'],
                        r['rating'],
                        r.get('title', ''),
                        r.get('review_text', r.get('reviewText', '')),
                        r['date'] if isinstance(r['date'], str) else r['date'].isoformat(),
                        json.dumps(r, default=json_serial)
                    ))
                    if conn.total_changes > 0:
                        saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save review: {e}")
            conn.commit()
        return saved_count

    def get_missing_ranges(self, start_date: datetime, end_date: datetime, platform: str) -> List[Tuple[datetime, datetime]]:
        """
        Naive implementation: Returns the full range if any day is missing.
        Better implementation: Identifies gaps in scrape_history.
        For now, let's stick to a simpler logic: 
        If we don't have records for a platform in this range, we scrape.
        """
        # Improved: Check scrape_history for full coverage
        days_needed = (end_date - start_date).days + 1
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT scrape_date FROM scrape_history 
                WHERE platform = ? AND scrape_date >= ? AND scrape_date <= ?
            """, (platform, start_date.date().isoformat(), end_date.date().isoformat()))
            covered_days = {row[0] for row in cursor.fetchall()}

        missing_ranges = []
        current_start = None
        
        for i in range(days_needed):
            day = (start_date + timedelta(days=i)).date()
            day_str = day.isoformat()
            
            if day_str not in covered_days:
                if current_start is None:
                    current_start = datetime.combine(day, datetime.min.time())
            else:
                if current_start is not None:
                    missing_ranges.append((current_start, datetime.combine(day - timedelta(days=1), datetime.max.time())))
                    current_start = None
        
        if current_start is not None:
            missing_ranges.append((current_start, end_date))
            
        return missing_ranges

    def has_platform_history(self, platform: str) -> bool:
        """Checks if there is any scrape history for the given platform."""
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.execute("SELECT 1 FROM scrape_history WHERE platform = ? LIMIT 1", (platform,))
            return cursor.fetchone() is not None

    def mark_scraped(self, platform: str, start_date: datetime, end_date: datetime):
        """Marks a range as successfully scraped."""
        days = (end_date - start_date).days + 1
        with sqlite3.connect(self.DB_PATH) as conn:
            for i in range(days):
                day = (start_date + timedelta(days=i)).date().isoformat()
                conn.execute("INSERT OR IGNORE INTO scrape_history (platform, scrape_date) VALUES (?, ?)", (platform, day))
            conn.commit()

    def purge_data(self) -> None:
        """
        Atomically deletes all terminal rows from every table and re-creates
        the schema, leaving the database clean and immediately usable.

        Safety guarantees:
        - Aborts with RuntimeError if any 'triggered' or 'running' job exists.
        - All three DELETEs run in one transaction; rolled back on any failure.
        - Schema is re-created via _init_db() after the transaction commits.
        """
        _ACTIVE = ("triggered", "running")
        logger.warning("Initiating full database purge…")

        with sqlite3.connect(self.DB_PATH) as conn:
            # Guard: refuse to purge while any job is actively in-flight
            active_count = conn.execute(
                "SELECT COUNT(*) FROM run_history WHERE status IN (?,?)", _ACTIVE
            ).fetchone()[0]
            if active_count:
                raise RuntimeError(
                    f"Purge aborted: {active_count} active job(s) still running. "
                    "Wait for all jobs to reach a terminal state first."
                )

            try:
                # Chronological order: run metadata → scrape coverage → raw reviews
                conn.execute("DELETE FROM run_history")
                conn.execute("DELETE FROM scrape_history")
                conn.execute("DELETE FROM reviews")
                conn.commit()
            except Exception:
                conn.rollback()
                logger.error("Purge transaction rolled back due to an error.")
                raise

        # Re-create schema so the DB is immediately usable after purge
        self._init_db()
        logger.info("Database purged and schema re-initialized successfully.")

    def reset_database(self) -> None:
        """Backwards-compat alias for purge_data(). Existing callers unchanged."""
        self.purge_data()


    def upsert_run_log(self, run_data: Dict[str, Any]):
        """Insert-or-replace a run row. Called immediately at trigger time."""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO run_history
                        (run_id, status, trigger_source, triggered_by,
                         start_date, end_date, triggered_at,
                         started_at, completed_at,
                         reviews_processed, themes_identified, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_data['run_id'],
                    run_data.get('status', 'triggered'),
                    run_data.get('trigger_source', 'manual'),
                    run_data.get('triggered_by'),
                    run_data.get('start_date'),
                    run_data.get('end_date'),
                    run_data.get('triggered_at', datetime.now().isoformat()),
                    run_data.get('started_at'),
                    run_data.get('completed_at'),
                    run_data.get('reviews_processed'),
                    run_data.get('themes_identified'),
                    run_data.get('error_message'),
                ))
                conn.commit()
            logger.info(f"Upserted run log for {run_data['run_id']} (status={run_data.get('status', 'triggered')})")
        except Exception as e:
            logger.error(f"Failed to upsert run log: {e}")

    # Keep old name as an alias so any existing callers don't break
    def save_run_log(self, run_data: Dict[str, Any]):
        """Alias for upsert_run_log (backwards-compat)."""
        self.upsert_run_log(run_data)

    def update_run_status(self, run_id: str, status: str, **kwargs):
        """Patch status and optional timestamp / count fields on an existing row."""
        allowed = {"started_at", "completed_at", "reviews_processed",
                   "themes_identified", "error_message"}
        fields: Dict[str, Any] = {k: v for k, v in kwargs.items() if k in allowed}
        fields["status"] = status

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [run_id]

        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.execute(
                    f"UPDATE run_history SET {set_clause} WHERE run_id = ?", values
                )
                conn.commit()
            logger.info(f"Updated run {run_id} → status={status}")
        except Exception as e:
            logger.error(f"Failed to update run status for {run_id}: {e}")

    def list_run_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns all runs (any status), newest-first. Used by the dashboard."""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM run_history
                    ORDER BY triggered_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list run history: {e}")
            return []

    def get_run_log(self, run_id: str) -> Dict[str, Any]:
        """Retrieves metadata for a specific run."""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM run_history WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Failed to get run log: {e}")
            return {}
