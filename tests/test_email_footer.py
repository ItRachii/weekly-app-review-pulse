import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.email_generator import EmailGenerator

def test_generate_email_footer():
    themes = [
        {
            "label": "Test Theme",
            "summary": "This is a test summary to verify the footer.",
            "review_count": 10
        }
    ]

    html_content = EmailGenerator.generate_html(themes)
    
    output_path = "test_footer_email.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Generated email saved to {output_path}")

if __name__ == "__main__":
    test_generate_email_footer()
