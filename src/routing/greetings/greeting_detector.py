import re
from src.config import load_config

class GreetingDetector:
    """
    Detects multilingual greetings and returns language-matched greeting responses.
    Supports Hello, Hi, Hey, Good Morning, Namaste, Namaskar, नमस्ते, नमस्कार, सलाम,
    राम राम, जय श्री राम, Good Evening, Good Afternoon, etc.
    """
    def __init__(self):
        self.config = load_config()
        # Core greeting tokens in lowercase
        self.greeting_words = {
            # English
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon", 
            "good evening", "welcome", "howdy", "hi there", "hello there",
            # Hindi (Latin/Romanized)
            "namaste", "pranam", "namaskar", "ram ram", "radhe radhe", "pranaam", 
            "salaam", "jay shree ram", "jai shree ram", "jai shri ram",
            # Hindi (Devanagari)
            "नमस्ते", "नमस्कार", "प्रणाम", "राम राम", "राधे राधे", "हेलो", "हाय", 
            "सलाम", "जय श्री राम"
        }

    def _normalize(self, text: str) -> str:
        """Normalize query text for matching."""
        text = text.strip().lower()
        text = re.sub(r'[?!.,;:\'"()\[\]{}]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def is_greeting(self, query: str) -> bool:
        """Determines if query is a greeting."""
        cleaned = self._normalize(query)
        if not cleaned:
            return False
            
        if cleaned in self.greeting_words:
            return True
            
        # Check if the query starts with a greeting word or is very short and contains one
        words = cleaned.split()
        if len(words) <= 3 and any(w in self.greeting_words for w in words):
            return True
            
        # Check substring match for compound greetings
        for gw in self.greeting_words:
            if cleaned == gw or cleaned.startswith(gw + " "):
                return True
                
        return False

    def get_greeting_response(self, query: str, lang: str = "en") -> str:
        """Retrieves greeting response in appropriate language."""
        # Simple heuristics for Hindi vs English query greeting
        cleaned = self._normalize(query)
        
        # Check if any Devanagari characters or clear Hindi words are used
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', query))
        is_hindi_latin = any(w in {"namaste", "namaskar", "pranam", "ram ram", "radhe radhe", "salaam"} for w in cleaned.split())
        
        detected_lang = "hi" if (has_devanagari or is_hindi_latin or lang == "hi") else "en"
        
        responses = self.config.greeting_responses.get(detected_lang, self.config.greeting_responses.get("en", []))
        if responses:
            return responses[0]
        return "Hello! How can I help you today?"
