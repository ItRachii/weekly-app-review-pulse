import csv
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from src.pii_cleaner import PIICleaner

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReviewSchema(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = ""
    review_text: str = Field(..., min_length=1)
    date: datetime
    platform: str = "unknown"

    @validator('review_text', pre=True)
    def clean_text(cls, v):
        if not isinstance(v, str):
            v = str(v)
        # Normalize and mask PII
        v = PIICleaner.normalize_text(v)
        v = PIICleaner.clean(v)
        return v

    @validator('title', pre=True)
    def clean_title(cls, v):
        if v and isinstance(v, str):
            v = PIICleaner.normalize_text(v)
            v = PIICleaner.clean(v)
        elif not v:
            v = ""
        return v

    @validator('date', pre=True)
    def parse_date(cls, v):
        if isinstance(v, datetime):
            return v
        # Try common formats
        formats = ['%Y-%m-%d', '%d-%m-%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']
        for fmt in formats:
            try:
                return datetime.strptime(v, fmt)
            except (ValueError, TypeError):
                continue
        raise ValueError(f"Could not parse date: {v}")

class IngestionModule:
    """
    Handles CSV ingestion, filtering, and normalization of app reviews.
    Pure Python implementation to avoid system dependency issues.
    """
    
    def __init__(self, weeks_back: int = 12):
        self.weeks_back = weeks_back
        self.cutoff_date = datetime.now() - timedelta(weeks=weeks_back)

    def process_csv(self, file_path: str) -> List[Dict[str, Any]]:
        logger.info(f"Starting ingestion for file: {file_path}")
        
        processed_reviews = []
        seen_reviews = set() # For deduplication (text + date)

        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Required columns check
                required_cols = {'rating', 'title', 'review_text', 'date'}
                if not required_cols.issubset(set(reader.fieldnames or [])):
                    missing = required_cols - set(reader.fieldnames or [])
                    logger.error(f"Missing columns in CSV: {missing}")
                    return []

                for row in reader:
                    try:
                        # 1. basic cleaning & validation
                        if not row['review_text'] or not row['rating'] or not row['date']:
                            continue
                        
                        # 2. Validation & Normalization via Pydantic
                        review_obj = ReviewSchema(
                            rating=row['rating'],
                            title=row['title'],
                            review_text=row['review_text'],
                            date=row['date'],
                            platform=row.get('platform', 'unknown')
                        )

                        # 3. Filter by date range
                        if review_obj.date < self.cutoff_date:
                            continue

                        # 4. Deduplication
                        dedup_key = (review_obj.review_text, review_obj.date.isoformat())
                        if dedup_key in seen_reviews:
                            continue
                        seen_reviews.add(dedup_key)
                        
                        # Double check empty after cleaning
                        if not review_obj.review_text.strip():
                            continue
                            
                        # Convert to dict for output
                        review_dict = review_obj.dict()
                        processed_reviews.append(review_dict)
                        
                    except Exception as e:
                        logger.debug(f"Skipping row due to error: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to process CSV: {e}")
            return []

        logger.info(f"Successfully processed {len(processed_reviews)} reviews.")
        return processed_reviews

    def save_to_json(self, reviews: List[Dict[str, Any]], output_path: str):
        try:
            # Handle datetime serialization
            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError ("Type %s not serializable" % type(obj))

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(reviews, f, default=json_serial, indent=2)
            logger.info(f"Output saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")

if __name__ == "__main__":
    module = IngestionModule(weeks_back=52)
    # Target can be run from here if needed
