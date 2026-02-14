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

    def reset_database(self):
        """Drops and recreates all tables to purge all records."""
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("DROP TABLE IF EXISTS reviews")
            conn.execute("DROP TABLE IF EXISTS scrape_history")
            conn.commit()
        self._init_db()
        logger.info("Database reset successfully.")
