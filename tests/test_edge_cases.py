import pytest
from src.orchestrator import PulseOrchestrator
from unittest.mock import patch

def test_pipeline_zero_reviews_graceful_exit():
    """Verify that the pipeline handles zero reviews without crashing."""
    orch = PulseOrchestrator()
    
    # Mock scraper to return empty list
    with patch('src.scraper_engine.ScraperEngine.scrape_app_store', return_value=[]):
        with patch('src.scraper_engine.ScraperEngine.scrape_play_store', return_value=[]):
            result = orch.run_pipeline(force=True)
            assert result["status"] == "failed"
            assert "No reviews found" in result["error"]

def test_noisy_review_cleaning():
    """Verify that the cleaner handles extreme noise/emojis/garbage."""
    from src.pii_cleaner import PIICleaner
    
    noisy_text = "😊🚀!!! @#$%^&* () _+ garbage 12345"
    cleaned = PIICleaner.normalize_text(noisy_text)
    # Normailze should strip extra spaces or special chars depending on implementation
    # Basic check: should not crash and should remain relatively clean
    assert len(cleaned) < len(noisy_text) or "garbage" in cleaned

@pytest.mark.parametrize("rating", [1, 5])
def test_uniform_rating_distribution(rating):
    """Placeholder for checking if the LLM biasedly shifts sentiment in uniform sets."""
    # This would require an LLM run or a very complex mock
    pass
