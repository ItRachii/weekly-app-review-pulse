import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.email_generator import EmailGenerator

def test_generate_email():
    themes = [
        {
            "label": "Login Issues",
            "summary": "Users are reporting frequent login failures after the latest update.",
            "review_count": 42
        },
        {
            "label": "Performance Lag",
            "summary": "The app feels sluggish when switching between tabs, especially on older devices.",
            "review_count": 28
        },
        {
            "label": "UI Compliments",
            "summary": "Many users appreciate the new dark mode and cleaner interface.",
            "review_count": 15
        }
    ]

    html_content = EmailGenerator.generate_html(themes)
    
    output_path = "test_email_output.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Generated email saved to {output_path}")

if __name__ == "__main__":
    test_generate_email()
