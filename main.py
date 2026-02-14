import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from src.scraper_engine import ScraperEngine
from src.theme_engine import ThemeClusteringEngine
from src.report_generator import PulseReportGenerator
from src.email_generator import EmailGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    weeks_back = int(os.getenv("WEEKS_BACK", 12))
    logger.info(f"Starting Weekly Pulse Flow (Lookback: {weeks_back} weeks)")

    # 1. Scrape & Cleanse
    # The ScraperEngine uses ReviewSchema internally, which invokes PIICleaner.
    scraper = ScraperEngine(weeks_back=weeks_back)
    
    logger.info("Fetching reviews from App Store and Play Store...")
    ios_reviews = scraper.scrape_app_store(app_id="1404871703")
    android_reviews = scraper.scrape_play_store(package_name="com.groww", count=150)
    
    all_reviews = ios_reviews + android_reviews
    logger.info(f"Total reviews fetched and cleaned: {len(all_reviews)}")

    if not all_reviews:
        logger.warning("No reviews found for the specified period. Exiting.")
        return

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Save cleaned reviews for reference/audit
    reviews_path = 'data/groww_reviews.json'
    with open(reviews_path, 'w', encoding='utf-8') as f:
        json.dump(all_reviews, f, indent=2, default=str)
    logger.info(f"Cleaned reviews saved to {reviews_path}")

    # 2. Semantic Theme Clustering & Insights
    logger.info("Starting semantic theme clustering and insight generation...")
    engine = ThemeClusteringEngine()
    themes_objs = engine.cluster_reviews(all_reviews)
    
    # Convert Pydantic models to dict for JSON serialization
    themes = [t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in themes_objs]

    # Save Final Pulse Analysis
    analysis_path = 'data/theme_analysis.json'
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(themes, f, indent=2)
    logger.info(f"Pulse analysis successfully saved to {analysis_path}")

    # 3. Executive Pulse Note
    logger.info("Generating executive pulse note...")
    generator = PulseReportGenerator()
    pulse_note = generator.generate_note(themes)

    note_path = 'data/weekly_pulse_note.md'
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(pulse_note)
    logger.info(f"Executive pulse note saved to {note_path}")

    # 4. Email Formatting
    logger.info("Formatting internal product email (HTML)...")
    email_html = EmailGenerator.generate_html(themes)
    email_path = 'data/weekly_pulse_email.html'
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(email_html)
    logger.info(f"Internal product email saved to {email_path}")

    # 5. User Feedback Output
    print("\n" + "="*50)
    print("WEEKLY APP REVIEW PULSE: SUMMARY")
    print("="*50)
    for i, theme in enumerate(themes[:3]):
        print(f"\n[{i+1}] {theme['label'].upper()} ({theme['review_count']} reviews)")
        print(f"    Summary: {theme['summary']}")
        print(f"    Primary Action: {theme['action_ideas'][0]}")
    print("\n" + "="*50)
    print(f"Full analysis available at: {os.path.abspath(analysis_path)}")

if __name__ == "__main__":
    main()
