import pytest
from datetime import datetime, timedelta
from src.pii_cleaner import PIICleaner
from src.ingestion import ReviewSchema, IngestionModule
import csv
import os

def test_pii_cleaner_masking():
    test_text = "My email is test@example.com and phone is 9876543210. Visit http://groww.in"
    cleaned = PIICleaner.clean(test_text)
    assert "[EMAIL]" in cleaned
    assert "[PHONE]" in cleaned
    assert "[URL]" in cleaned
    assert "test@example.com" not in cleaned

def test_text_normalization():
    test_text = "  Check this <p>tag</p> content   "
    normalized = PIICleaner.normalize_text(test_text)
    assert normalized == "Check this tag content"

def test_review_validation_schema():
    # Valid review
    valid_data = {
        "rating": 5,
        "title": "Great App!",
        "review_text": "I love using Groww. Contact me at 1234567890 if you have questions.",
        "date": datetime.now()
    }
    review = ReviewSchema(**valid_data)
    assert "[PHONE]" in review.review_text
    assert "1234567890" not in review.review_text

    # Invalid rating
    with pytest.raises(ValueError):
        ReviewSchema(rating=6, review_text="Bad rating", date=datetime.now())

def test_ingestion_filtering(tmp_path):
    # Create sample CSV
    d = tmp_path / "data"
    d.mkdir()
    csv_file = d / "test_reviews.csv"
    
    old_date = (datetime.now() - timedelta(weeks=20)).strftime('%Y-%m-%d')
    new_date = (datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d')
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['rating', 'title', 'review_text', 'date'])
        writer.writeheader()
        writer.writerow({'rating': 5, 'title': 'Old', 'review_text': 'Too old to ingest', 'date': old_date})
        writer.writerow({'rating': 4, 'title': 'New', 'review_text': 'Perfectly fine', 'date': new_date})
        writer.writerow({'rating': 3, 'title': 'Duplicate', 'review_text': 'Perfectly fine', 'date': new_date})
    
    module = IngestionModule(weeks_back=12)
    results = module.process_csv(str(csv_file))
    
    # Should only have the 'New' one (Old is filtered, Duplicate is dropped)
    assert len(results) == 1
    assert results[0]['title'] == "New"
