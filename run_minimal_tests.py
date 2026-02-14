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

if __name__ == "__main__":
    try:
        test_pii_cleaning()
        test_schema_validation()
        test_orchestrator_initialization()
        print("\nALL MINIMAL TESTS PASSED SUCCESSFULLY")
    except Exception as e:
        print(f"\nTEST FAILED: {str(e)}")
        sys.exit(1)
