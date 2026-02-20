import pytest
from datetime import datetime, timedelta
from src.data_manager import DataManager
import os

@pytest.fixture
def db(tmp_path):
    """Each test gets its own isolated SQLite file under pytest's tmp_path."""
    test_db = str(tmp_path / "test_pulse.db")
    manager = DataManager()
    manager.DB_PATH = test_db
    manager._init_db()
    yield manager
    # tmp_path is automatically cleaned up by pytest — no manual removal needed

def test_save_and_get_reviews(db):
    reviews = [
        {"platform": "ios", "rating": 5, "reviewText": "Great app!", "date": datetime(2024, 1, 1).isoformat()},
        {"platform": "android", "rating": 4, "reviewText": "Nice UI", "date": datetime(2024, 1, 2).isoformat()}
    ]
    
    db.save_reviews(reviews)
    
    cached = db.get_cached_reviews(datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert len(cached) == 2
    assert any(r['review_text'] == "Great app!" for r in cached)

def test_missing_ranges(db):
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 10)
    platform = "ios"
    
    # Initially all ranges are missing
    ranges = db.get_missing_ranges(start, end, platform)
    assert len(ranges) == 1
    assert ranges[0] == (start, end)
    
    # Mark some days as scraped
    db.mark_scraped(platform, datetime(2024, 1, 3), datetime(2024, 1, 5))
    
    # Now we should have two missing ranges: 1-2 and 6-10
    ranges = db.get_missing_ranges(start, end, platform)
    assert len(ranges) == 2
    assert ranges[0][0].date() == start.date()
    assert ranges[0][1].date() == datetime(2024, 1, 2).date()
    assert ranges[1][0].date() == datetime(2024, 1, 6).date()
    assert ranges[1][1].date() == end.date()


# --- Regression tests for pipeline visibility fix ---

def test_upsert_run_log_no_duplicate(db):
    """Double-upsert with same run_id must produce exactly one row (INSERT OR REPLACE)."""
    now = datetime.now().isoformat()
    db.upsert_run_log({"run_id": "r1", "status": "triggered", "triggered_at": now})
    db.upsert_run_log({"run_id": "r1", "status": "running",   "triggered_at": now})
    runs = db.list_run_history()
    matching = [r for r in runs if r["run_id"] == "r1"]
    assert len(matching) == 1, "Duplicate rows must not exist for the same run_id"
    assert matching[0]["status"] == "running"


def test_update_run_status_transition(db):
    """Status must progress triggered → running → succeeded without creating new rows."""
    now = datetime.now().isoformat()
    db.upsert_run_log({"run_id": "r2", "status": "triggered", "triggered_at": now})
    db.update_run_status("r2", "running", started_at=now)
    db.update_run_status("r2", "succeeded",
                         completed_at=now, reviews_processed=42, themes_identified=3)
    row = db.get_run_log("r2")
    assert row["status"] == "succeeded"
    assert row["reviews_processed"] == 42
    assert row["completed_at"] is not None
    # Still exactly one row in history
    assert len([r for r in db.list_run_history() if r["run_id"] == "r2"]) == 1
