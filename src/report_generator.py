import logging
import os
from typing import List, Dict, Any
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class PulseReportGenerator:
    """
    Generates a concise executive pulse note (≤250 words) from theme analysis.
    """
    
    SYSTEM_PROMPT = """You are the Chief of Staff at GROWW. Your audience is the executive leadership team. 
    Summarize the weekly app review themes into a highly scannable, high-impact pulse note."""

    REPORT_PROMPT = """
    Summarize the following app review themes into an executive pulse note.

    Title: GROWW Weekly Review Pulse – Week of {current_date}

    Top Themes:
    1. [Theme Label]: [1-sentence summary emphasizing volume/impact]
    2. ...

    What Users Are Saying:
    - "[High-signal quote 1]"
    - "[High-signal quote 2]"
    - "[High-signal quote 3]"

    Recommended Actions:
    1. [Action Idea 1]
    2. [Action Idea 2]
    3. [Action Idea 3]

    ### Constraints:
    - WORD COUNT: Strictly ≤ 250 words total.
    - TONE: Executive, punchy, and objective. No fluff.
    - PRIVACY: No PII, no usernames.

    ### Input Data:
    {themes_json}
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate_note(self, themes: List[Dict[str, Any]]) -> str:
        if not themes:
            return "No review data available for this week."

        # Select top 3 themes if more exist
        top_themes = themes[:3]
        themes_json = json.dumps(top_themes, indent=2)
        current_date = datetime.now().strftime("%B %d, %Y")

        prompt = self.REPORT_PROMPT.format(
            current_date=current_date,
            themes_json=themes_json
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            report_text = response.choices[0].message.content.strip()
            
            # Enforcement Logic
            return self._enforce_constraints(report_text)

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return "Error generating pulse note. Please review data/theme_analysis.json directly."

    def _enforce_constraints(self, text: str, limit: int = 250) -> str:
        """Enforces word count and basic formatting."""
        words = text.split()
        if len(words) <= limit:
            return text
        
        logger.warning(f"Report exceeded {limit} words ({len(words)} words). Truncating.")
        truncated = " ".join(words[:limit])
        last_period = truncated.rfind('.')
        if last_period != -1:
             return truncated[:last_period+1] + "\n\n[Note: Truncated for brevity to stay under 250 words.]"
        return truncated + "...\n\n[Note: Truncated for brevity to stay under 250 words.]"

import json # Ensure json is available for the class method
