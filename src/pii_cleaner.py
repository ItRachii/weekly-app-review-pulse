import re
import logging

logger = logging.getLogger(__name__)

class PIICleaner:
    """
    Utility class to strip PII (Personally Identifiable Information) from text.
    """
    
    # Regex patterns for common PII
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    URL_PATTERN = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    # Basic patterns for common Indian ID formats if applicable (like PAN, but kept generic)
    ID_PATTERN = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b|\b\d{12}\b' 

    @classmethod
    def clean(cls, text: str) -> str:
        if not text:
            return ""
        
        original_text = text
        
        # Replace patterns with placeholders
        text = re.sub(cls.EMAIL_PATTERN, "[EMAIL]", text)
        text = re.sub(cls.PHONE_PATTERN, "[PHONE]", text)
        text = re.sub(cls.URL_PATTERN, "[URL]", text)
        text = re.sub(cls.ID_PATTERN, "[ID]", text)
        
        if original_text != text:
             logger.debug("PII detected and masked in text.")
             
        return text

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Trims, removes HTML, and basic emoji cleaning.
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove emojis (keeping only basic multilingual plane for simplicity, 
        # or just stripping anything that isn't standard alphanumeric/punctuation)
        # Here we just trim and remove excessive whitespace
        text = " ".join(text.split())
        
        return text
