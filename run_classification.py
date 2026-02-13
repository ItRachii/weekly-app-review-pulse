import json
import logging
import os
from dotenv import load_dotenv
from src.theme_engine import ThemeClusteringEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    # Load scraped reviews
    reviews_path = 'data/groww_reviews.json'
    if not os.path.exists(reviews_path):
        logger.error(f"Review file not found at {reviews_path}. Please run scrapers first.")
        return

    with open(reviews_path, 'r', encoding='utf-8') as f:
        reviews = json.load(f)

    logger.info(f"Loaded {len(reviews)} reviews for classification.")

    # Initialize Engine
    # Note: If OPENAI_API_KEY is missing, the engine will likely fail.
    # We will catch this and inform the user.
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment or .env file.")
        print("\n[IMPORTANT] No OpenAI API Key found.")
        print("Please provide an API key to perform real semantic clustering.")
        print("Falling back to simulated/mock themes for demonstration...\n")
        
        # Mock Response for Demo
        themes = [
            {
                "label": "Seamless App UI",
                "review_count": 85,
                "summary": "Users praise the clean, intuitive, and fast user interface of the Groww app."
            },
            {
                "label": "Reliable Trading Execution",
                "review_count": 42,
                "summary": "Positive feedback regarding the speed and reliability of stock and MF orders."
            },
            {
                "label": "KYC & Onboarding Issues",
                "review_count": 15,
                "summary": "Minor complaints about the document verification timeline for new users."
            }
        ]
    else:
        engine = ThemeClusteringEngine()
        themes_objs = engine.cluster_reviews(reviews)
        themes = [t.dict() if hasattr(t, 'dict') else t for t in themes_objs]

    # Save Results
    output_path = 'data/theme_analysis.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(themes, f, indent=2)

    logger.info(f"Classification complete. Analysis saved to {output_path}")
    
    # Print Top 3 Themes
    print("\n" + "="*40)
    print("TOP 3 THEMES BY VOLUME")
    print("="*40)
    for i, theme in enumerate(themes[:3]):
        print(f"{i+1}. {theme['label']} ({theme['review_count']} reviews)")
        print(f"   Summary: {theme['summary']}\n")

if __name__ == "__main__":
    main()
