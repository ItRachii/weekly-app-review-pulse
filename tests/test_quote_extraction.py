import pytest
from src.theme_engine import Theme, ThemeOutput
from pydantic import ValidationError

def test_theme_model_with_quotes():
    """Test that Theme model correctly requires and validates high_signal_quotes."""
    # Valid case
    valid_data = {
        "label": "Test Theme",
        "review_count": 10,
        "summary": "This is a test summary.",
        "high_signal_quotes": ["Quote 1", "Quote 2", "Quote 3"]
    }
    theme = Theme(**valid_data)
    assert len(theme.high_signal_quotes) == 3

    # Invalid case (too few quotes) - should fallback to dummy quotes via validator
    invalid_data = {
        "label": "Test Theme",
        "review_count": 10,
        "summary": "This is a test summary.",
        "high_signal_quotes": ["Quote 1"]
    }
    theme = Theme(**invalid_data)
    assert len(theme.high_signal_quotes) == 3
    assert theme.high_signal_quotes[1] == "No relevant quote found"

def test_quote_length_constraint():
    """
    Test that we can track quote lengths. 
    Note: The Pydantic model doesn't strictly enforce length yet, 
    but we can add a validator if needed.
    """
    long_quote = "This is a very long quote that definitely exceeds twenty five words in total length to test if our logic or prompts are working correctly as expected by the user."
    data = {
        "label": "Test Theme",
        "review_count": 5,
        "summary": "Summary",
        "high_signal_quotes": [long_quote, "Short quote", "Another one"]
    }
    theme = Theme(**data)
    # Check words
    words = theme.high_signal_quotes[0].split()
    assert len(words) > 25 
    # This test confirms that we might need a validator if we want hard enforcement
    # For now, we rely on the LLM prompt, but let's add a soft check or just document it.

def test_theme_output_validation():
    """Test ThemeOutput validation for multiple themes."""
    data = {
        "themes": [
            {
                "label": "Theme 1",
                "review_count": 5,
                "summary": "S1",
                "high_signal_quotes": ["Q1", "Q2", "Q3"]
            },
            {
                "label": "Theme 2",
                "review_count": 3,
                "summary": "S2",
                "high_signal_quotes": ["Q1", "Q2", "Q3"]
            }
        ]
    }
    output = ThemeOutput(**data)
    assert len(output.themes) == 2
    assert output.themes[0].label == "Theme 1"
