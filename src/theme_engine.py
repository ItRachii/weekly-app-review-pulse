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
    You are an expert NLP engineer. Your task is to analyze a list of user reviews for the GROWW app and group them into at most 5 semantic themes.
    
    ### Rules:
    1. Semantic Grouping: Group similar feedback (e.g., UI issues, payment failures, app performance).
    2. Labels: Use concise labels (2-4 words, e.g., "Payment Gateway Failures").
    3. Exclusivity: Ensure themes do not overlap.
    4. Coverage: Every major feedback point should fall into one of these 5 categories.
    5. Prioritization: Focus on the most frequent and impactful themes.
    
    ### Input Reviews:
    {reviews_text}
    
    ### Output Format:
    Return a JSON object with the following structure:
    {{
      "themes": [
        {{
          "label": "Theme Label",
          "review_count": 12,
          "summary": "Brief explanation of what users are saying about this theme."
        }}
      ]
    }}
    
    IMPORTANT: Maximum 5 themes. If more exist, merge the least frequent ones into a 'Miscellaneous' category or the closest existing theme.
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
                summary="Automated analysis failed. General review aggregation."
            )
            return [dummy_theme]

if __name__ == "__main__":
    # Test stub
    engine = ThemeClusteringEngine()
    # engine.cluster_reviews([...])
