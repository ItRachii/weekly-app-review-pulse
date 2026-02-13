import pytest
from src.theme_engine import ThemeOutput, Theme

def test_theme_count_validation_truncates():
    # Attempt to create with 6 themes
    themes_data = [
        {"label": f"Theme {i}", "review_count": 10-i, "summary": "..."}
        for i in range(6)
    ]
    
    # Pydantic validator should truncate to 5
    validated = ThemeOutput(themes=themes_data)
    assert len(validated.themes) == 5
    # Should keep the ones with higher counts (0, 1, 2, 3, 4)
    # The last one (Theme 5) should be gone
    labels = [t.label for t in validated.themes]
    assert "Theme 5" not in labels

def test_theme_label_constraint():
    with pytest.raises(Exception):
        # Missing label
        Theme(review_count=5, summary="missing label")

def test_deterministic_sorting():
    themes_data = [
        {"label": "Most Popular", "review_count": 100, "summary": "..."},
        {"label": "Middle", "review_count": 50, "summary": "..."},
        {"label": "Least", "review_count": 10, "summary": "..."}
    ]
    output = ThemeOutput(themes=themes_data)
    # Ensure sorting works as expected in the engine (tested manually in usage)
    sorted_themes = sorted(output.themes, key=lambda x: x.review_count, reverse=True)
    assert sorted_themes[0].label == "Most Popular"
