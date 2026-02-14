import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator, ValidationError
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Theme(BaseModel):
    label: str = Field(..., description="Concise 2-4 word theme label")
    review_count: int = Field(..., description="Number of reviews in this theme")
    summary: str = Field(..., description="Brief summary of the theme's core message")
    high_signal_quotes: List[str] = Field(..., description="3 representative, high-signal, non-PII quotes (max 25 words each)")
    action_ideas: List[str] = Field(..., description="3 specific, realistic, and implementable action ideas for the product team")

    @validator('high_signal_quotes')
    def validate_quotes(cls, v):
        if len(v) != 3:
             return (v + ["No relevant quote found"] * 3)[:3]
        return v

    @validator('action_ideas')
    def validate_action_ideas(cls, v):
        if len(v) != 3:
             return (v + ["No specific action identified"] * 3)[:3]
        return v

class ThemeOutput(BaseModel):
    themes: List[Theme]

    @validator('themes')
    def validate_theme_count(cls, v):
        if len(v) > 5:
            # Fallback logic: Keep top 5 by review count
            logger.warning(f"LLM returned {len(v)} themes. Truncating to 5 top themes.")
            v.sort(key=lambda x: x.review_count, reverse=True)
            return v[:5]
        return v

class ThemeClusteringEngine:
    """
    Groups reviews into semantic themes using LLM.
    """
    
    CLUSTERING_PROMPT = """
    You are a Senior Product Manager. Your task is to analyze a list of user reviews for the GROWW app and group them into at most 5 semantic themes.
    For each theme, you must also select 3 high-signal quotes and propose 3 specific action ideas.

    ### Rules:
    1. Semantic Grouping: Group similar feedback (e.g., UI issues, payment failures).
    2. Labels: Use concise labels (2-4 words, e.g., "Payment Gateway Failures").
    3. Exclusivity: Ensure themes do not overlap.
    4. Coverage: Every major feedback point should fall into one of these 5 categories.
    5. Prioritization: Focus on the most frequent and impactful themes.

    ### Quote Selection Criteria:
    Select EXACTLY 3 quotes per theme that are clear, representative, non-PII, and ≤ 25 words.

    ### Action Ideas Criteria:
    Propose EXACTLY 3 action ideas per theme that are:
    - SPECIFIC: Avoid generic terms like "Improve User Experience". Use "Add a status tracker for withdrawals".
    - REALISTIC: Focus on incremental, high-impact changes. Avoid massive architectural overhauls (e.g., Do NOT suggest "Rewrite the entire backend").
    - IMPLEMENTABLE: Clear enough for a Jira ticket. Can be completed in a 2-week sprint.
    - CONCISE: Max 15 words per idea.

    ### Deduplication & Bias Mitigation:
    - Deduplication: Ensure quotes and action ideas represent distinct perspectives.
    - Bias Mitigation: Avoid 'extreme-only' bias in quote selection.
    
    ### Input Reviews:
    {reviews_text}
    
    ### Output Format:
    Return a JSON object with the following structure:
    {{
      "themes": [
        {{
          "label": "Theme Label",
          "review_count": 12,
          "summary": "Brief explanation.",
          "high_signal_quotes": ["Quote 1", "Quote 2", "Quote 3"],
          "action_ideas": ["Action 1", "Action 2", "Action 3"]
        }}
      ]
    }}
    
    IMPORTANT: Maximum 5 themes. Enforce exactly 3 quotes and 3 action ideas per theme.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def cluster_reviews(self, reviews: List[Dict[str, Any]]) -> List[Theme]:
        if not reviews:
            logger.warning("No reviews to cluster.")
            return []

        # Prepare text for LLM (limit to avoid token overflow)
        # In a real production system, we might use embeddings + local clustering first,
        # but for this pulse report requirements, we send a rich sample.
        reviews_sample = reviews[:100] # Take first 100 for clustering
        formatted_reviews = "\n".join([
            f"- [{r['rating']}*] {r['title']}: {r['review_text']}"
            for r in reviews_sample
        ])

        prompt = self.CLUSTERING_PROMPT.format(reviews_text=formatted_reviews)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a deterministic NLP assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2, # Low temperature for deterministic output
                response_format={"type": "json_object"}
            )

            result_json = json.loads(response.choices[0].message.content)
            
            # Validation via Pydantic
            validated_output = ThemeOutput(**result_json)
            
            # Sort by volume and return top 3 as per requirements (though we keep 5 in internal storage)
            sorted_themes = sorted(validated_output.themes, key=lambda x: x.review_count, reverse=True)
            return sorted_themes

        except Exception as e:
            logger.error(f"LLM clustering failed: {e}")
            # Fallback: create a generic theme
            dummy_theme = Theme(
                label="General Feedback",
                review_count=len(reviews),
                summary="Automated analysis failed. General review aggregation.",
                high_signal_quotes=["Review analysis failed.", "No quotes available.", "Please check logs."],
                action_ideas=["Fix the extraction pipeline.", "Check OpenAI API status.", "Verify input review format."]
            )
            return [dummy_theme]

if __name__ == "__main__":
    # Test stub
    engine = ThemeClusteringEngine()
    # engine.cluster_reviews([...])
