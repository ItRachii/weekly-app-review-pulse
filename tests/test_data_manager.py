import pytest
from datetime import datetime, timedelta
from src.data_manager import DataManager
import os

@pytest.fixture
def db():
    # Use a test database
    test_db = "data/test_pulse.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    manager = DataManager()
    manager.DB_PATH = test_db
    manager._init_db()
    
    yield manager
    
    if os.path.exists(test_db):
        os.remove(test_db)

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
