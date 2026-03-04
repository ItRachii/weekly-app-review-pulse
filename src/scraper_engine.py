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
        processed = []
        
        for page in range(1, 11):
            url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    
                feed = data.get('feed', {})
                entries = feed.get('entry', [])
                
                if not isinstance(entries, list):
                    entries = [entries] if entries else []
                
                if not entries:
                    break
                    
                earliest_date = None
                for entry in entries:
                    # Skip app info entries (they don't have im:rating)
                    if 'im:rating' not in entry:
                        continue
                        
                    try:
                        dt_str = entry['updated']['label']
                        if dt_str.endswith('Z'):
                            dt_str = dt_str.replace('Z', '+00:00')
                        
                        review_date = datetime.fromisoformat(dt_str).replace(tzinfo=None)
                        if earliest_date is None or review_date < earliest_date:
                            earliest_date = review_date
                        
                        if not (self.start_date <= review_date <= self.end_date):
                            continue
                            
                        review_obj = ReviewSchema(
                            rating=int(entry['im:rating']['label']),
                            title=entry['title']['label'],
                            review_text=entry['content']['label'],
                            date=review_date,
                            platform="ios"
                        )
                        processed.append(review_obj.dict())
                    except Exception as e:
                        logger.debug(f"Skipping App Store entry: {e}")
                        continue
                
                if earliest_date and earliest_date < self.start_date:
                    break
                    
            except Exception as e:
                logger.error(f"App Store RSS scraping failed on page {page}: {e}")
                break
                
        logger.info(f"Fetched {len(processed)} reviews from App Store.")
        return processed

    def scrape_play_store(self, package_name: str, count: int = 100, country: str = 'in') -> List[Dict[str, Any]]:
        if not HAS_PLAY_SCRAPER:
            logger.error("google-play-scraper not installed.")
            return []
            
        logger.info(f"Scraping Play Store for package: {package_name} in country: {country}")
        processed = []
        try:
            continuation_token = None
            
            while True:
                result, continuation_token = reviews(
                    package_name,
                    lang='en',
                    country=country,
                    sort=Sort.NEWEST,
                    count=200,
                    continuation_token=continuation_token
                )
                
                if not result:
                    break
                    
                earliest_date = None
                for r in result:
                    review_date = r['at']
                    
                    if earliest_date is None or review_date < earliest_date:
                        earliest_date = review_date
                        
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
                    
                # If the earliest review in the batch is older than our start_date, we have gone far enough back
                if earliest_date and earliest_date < self.start_date:
                    break
                    
                if not continuation_token:
                    break
                
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

<<<<<<< HEAD
    regions_str = app.get("regions")
    if not regions_str:
        regions_str = "in"
    regions = [r.strip().lower() for r in str(regions_str).split(',') if r.strip()]

    ios = []
    android = []
    for r in regions:
        print(f"Scraping region: {r}")
        if appstore_id:
            ios.extend(se.scrape_app_store(appstore_id, country=r))
        if playstore_id:
            android.extend(se.scrape_play_store(playstore_id, count=100, country=r))
=======
    ios = se.scrape_app_store(appstore_id) if appstore_id else []
    android = se.scrape_play_store(playstore_id) if playstore_id else []
>>>>>>> cfa17394008e0805c1c38df84f999d6c423ea70c

    print(f"Total reviews: {len(ios) + len(android)}")
    # Save combined
    out_file = f"data/{app['app_name'].lower()}_reviews.json"
    with open(out_file, 'w') as f:
        json.dump(ios + android, f, indent=2, default=str)
    print(f"Saved to {out_file}")

