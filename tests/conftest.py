import pytest
from unittest.mock import MagicMock
import json

@pytest.fixture
def mock_openai_response():
    """Fixture to provide a mock OpenAI chat completion response."""
    def _create_mock(content: str):
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response
    return _create_mock

@pytest.fixture
def mock_themes_output():
    """Standard mock themes for testing downstream generators."""
    return [
        {
            "label": "User Experience",
            "review_count": 10,
            "summary": "Users love the UI.",
            "high_signal_quotes": ["The UI is great!", "Very intuitive interface."],
            "action_ideas": ["Optimize UI performance", "Conduct user interviews"]
        }
    ]

@pytest.fixture
def raw_reviews_sample():
    """Sample raw reviews for grounding tests."""
    return [
        {"review_text": "The UI is great!", "rating": 5, "date": "2024-01-01", "platform": "ios"},
        {"review_text": "Very intuitive interface.", "rating": 4, "date": "2024-01-02", "platform": "android"},
        {"review_text": "Slow loading on 4G.", "rating": 2, "date": "2024-01-03", "platform": "android"}
    ]
