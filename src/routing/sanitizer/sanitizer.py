import re

class ResponseSanitizer:
    """
    Cleans up the final generated response text to remove any debug prefixes,
    internal markers, developer comments, JSON remnants, or logging labels.
    """
    def sanitize(self, text: str) -> str:
        if not text:
            return ""
            
        # 1. Remove draft and debug prefixes
        text = re.sub(r'\[Draft RAG Response\]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Debug:[^\]]*\]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Template Match:[^\]]*\]\s*', '', text, flags=re.IGNORECASE)
        
        # 2. Remove developer/inline TODO comments
        text = re.sub(r'#\s*TODO.*', '', text)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # 3. Clean up JSON brackets/keys that may have leaked
        text = re.sub(r'\{\s*"reply"\s*:\s*', '', text, flags=re.IGNORECASE)
        
        # 4. Remove logging/debugging marker labels
        text = re.sub(r'(Metadata|Route Stage|Latency|Sources):\s*.*', '', text, flags=re.IGNORECASE)
        
        # 5. Clean up markdown links formatting if empty: []()
        text = re.sub(r'\[\]\([^\)]*\)', '', text)
        
        # 6. Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
