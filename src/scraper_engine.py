import urllib.request
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.ingestion import ReviewSchema

# Use the library for Android as it is more robust, if it works
try:
    from google_play_scraper import reviews, Sort
    HAS_PLAY_SCRAPER = True
except ImportError:
    HAS_PLAY_SCRAPER = False

from utils.logger import setup_logger

logger = setup_logger("scraper_engine")

class ScraperEngine:
    """
    Scraper engine for App Store (urllib-based) and Play Store (library-based).
    """
    
    def __init__(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, weeks_back: int = 12):
        self.end_date = end_date or datetime.now()
        if start_date:
            self.start_date = start_date
        else:
            self.start_date = self.end_date - timedelta(weeks=weeks_back)

    def scrape_app_store(self, app_id: str, country: str = 'in') -> List[Dict[str, Any]]:
        logger.info(f"Scraping App Store via RSS for ID: {app_id}")
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortby=mostrecent/json"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            feed = data.get('feed', {})
            entries = feed.get('entry', [])
            
            if not isinstance(entries, list):
                entries = [entries] if entries else []
                
            processed = []
            for entry in entries:
                # Skip app info entries (they don't have im:rating)
                if 'im:rating' not in entry:
                    continue
                    
                try:
                    dt_str = entry['updated']['label']
                    # Handle Z and offset formats
                    if dt_str.endswith('Z'):
                        dt_str = dt_str.replace('Z', '+00:00')
                    
                    # fromisoformat handles +HH:MM and +HHMM
                    review_date = datetime.fromisoformat(dt_str)
                    
                    if not (self.start_date <= review_date.replace(tzinfo=None) <= self.end_date):
                        continue
                        
                    review_obj = ReviewSchema(
                        rating=int(entry['im:rating']['label']),
                        title=entry['title']['label'],
                        review_text=entry['content']['label'],
                        date=review_date.replace(tzinfo=None), # Keep naive for DB simplicity
                        platform="ios"
                    )
                    processed.append(review_obj.dict())
                except Exception as e:
                    logger.debug(f"Skipping App Store entry: {e}")
                    continue
                    
            logger.info(f"Fetched {len(processed)} reviews from App Store.")
            return processed
            
        except Exception as e:
            logger.error(f"App Store RSS scraping failed: {e}")
            return []

    def scrape_play_store(self, package_name: str, count: int = 100) -> List[Dict[str, Any]]:
        if not HAS_PLAY_SCRAPER:
            logger.error("google-play-scraper not installed.")
            return []
            
        logger.info(f"Scraping Play Store for package: {package_name}")
        try:
            result, _ = reviews(
                package_name,
                lang='en',
                country='in',
                sort=Sort.NEWEST,
                count=count
            )
            
            processed = []
            for r in result:
                review_date = r['at']
                if not (self.start_date <= review_date <= self.end_date):
                    continue
                    
                review_obj = ReviewSchema(
                    rating=r['score'],
                    title="",
                    review_text=r['content'],
                    date=review_date,
                    platform="android"
                )
                processed.append(review_obj.dict())
                
            logger.info(f"Fetched {len(processed)} reviews from Play Store.")
            return processed
        except Exception as e:
            logger.error(f"Play Store scraping failed: {e}")
            return []

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Pull app IDs from the applications table
    from src.data_manager import DataManager
    dm = DataManager()

    # Accept optional app name from CLI, otherwise use the first registered app
    if len(sys.argv) > 1:
        app = dm.get_application(sys.argv[1])
        if not app:
            print(f"Application '{sys.argv[1]}' not found in DB.")
            exit(1)
    else:
        apps = dm.get_all_applications()
        if not apps:
            print("No applications registered in DB. Please add one first.")
            exit(1)
        app = apps[0]

    appstore_id = app.get("appstore_id")
    playstore_id = app.get("playstore_id")
    print(f"Using app: {app['app_name']} | App Store: {appstore_id} | Play Store: {playstore_id}")

    se = ScraperEngine(weeks_back=52)

    ios = se.scrape_app_store(appstore_id) if appstore_id else []
    android = se.scrape_play_store(playstore_id) if playstore_id else []

    print(f"Total reviews: {len(ios) + len(android)}")
    # Save combined
    out_file = f"data/{app['app_name'].lower()}_reviews.json"
    with open(out_file, 'w') as f:
        json.dump(ios + android, f, indent=2, default=str)
    print(f"Saved to {out_file}")

