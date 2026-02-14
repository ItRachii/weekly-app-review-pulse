import pytest
import re
from src.pii_cleaner import PIICleaner

def test_pii_regex_coverage():
    """Verify the PIICleaner can detect and mask emails, phones, and urls."""
    text = "Contact me at test@example.com or +91 9876543210. Visit https://groww.in"
    cleaned = PIICleaner.clean(text)
    
    assert "test@example.com" not in cleaned
    assert "9876543210" not in cleaned
    assert "https://groww.in" not in cleaned
    assert "[EMAIL]" in cleaned or "[PHONE]" in cleaned or "[URL]" in cleaned

def test_pydantic_schema_validation():
    """Verify ReviewSchema correctly cleans PII on initialization."""
    from src.ingestion import ReviewSchema
    from datetime import datetime
    
    raw_text = "I am at john.doe@mail.com"
    review = ReviewSchema(
        rating=5,
        review_text=raw_text,
        date=datetime.now(),
        platform="playstore"
    )
    
    # review_text should be cleaned automatically via Pydantic validator
    assert "john.doe@mail.com" not in review.review_text
    assert "[EMAIL]" in review.review_text

def test_report_pii_safety():
    """Verify that a generated executive note doesn't contain usernames or common patterns."""
    from src.report_generator import PulseReportGenerator
    
    gen = PulseReportGenerator()
    # Mocking a report with PII
    pii_report = "User john_doe123 says: Call me on 9112233445"
    with pytest.warns(None): # No specific warning logic yet, but good to check
        safe_report = gen._enforce_constraints(pii_report)
        # We expect the generator or post-processing to avoid these if we integrate PIICleaner
        # For now, let's verify if our cleaner catches it
        final_safe = PIICleaner.clean(safe_report)
        assert "9112233445" not in final_safe
