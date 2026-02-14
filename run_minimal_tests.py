import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.pii_cleaner import PIICleaner
from src.ingestion import ReviewSchema
from src.orchestrator import PulseOrchestrator

def test_pii_cleaning():
    print("Testing PII Cleaning...")
    text = "Secret email: secret@groww.in"
    cleaned = PIICleaner.clean(text)
    assert "secret@groww.in" not in cleaned
    assert "[EMAIL]" in cleaned
    print("PII Cleaning Passed")

def test_schema_validation():
    print("Testing Schema Validation...")
    raw_text = "Phone: 9988776655"
    review = ReviewSchema(
        rating=5,
        review_text=raw_text,
        date=datetime.now(),
        platform="test"
    )
    assert "9988776655" not in review.review_text
    assert "[PHONE]" in review.review_text
    print("Schema Validation Passed")

def test_orchestrator_initialization():
    print("Testing Orchestrator...")
    orch = PulseOrchestrator()
    assert os.path.exists('data/raw')
    assert os.path.exists('data/processed')
    print("Orchestrator Passed")

def test_data_manager():
    print("Testing DataManager...")
    from src.data_manager import DataManager
    from datetime import datetime, timedelta
    
    test_db = "data/test_pulse.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    try:
        db = DataManager()
        db.DB_PATH = test_db
        db._init_db()
        
        # Test Save/Get
        reviews = [{"platform": "ios", "rating": 5, "reviewText": "Test", "date": datetime.now()}]
        db.save_reviews(reviews)
        cached = db.get_cached_reviews(datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1))
        assert len(cached) >= 1
        
        # Test Missing Ranges
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)
        ranges = db.get_missing_ranges(start, end, "ios")
        assert len(ranges) == 1
        
        db.mark_scraped("ios", datetime(2024, 1, 2), datetime(2024, 1, 3))
        ranges = db.get_missing_ranges(start, end, "ios")
        assert len(ranges) == 2 # 1st and 4-5th
        
        print("DataManager Passed")
    finally:
        try:
            if os.path.exists(test_db):
                os.remove(test_db)
        except PermissionError:
            pass # On Windows, SQLite sometimes holds the lock for a few ms longer

if __name__ == "__main__":
    try:
        test_pii_cleaning()
        test_schema_validation()
        test_data_manager()
        test_orchestrator_initialization() # Kept original function name
        print("\nALL MINIMAL TESTS PASSED SUCCESSFULLY")
    except Exception as e:
        print(f"\nTESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
