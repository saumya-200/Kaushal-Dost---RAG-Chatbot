import logging
import re
from difflib import SequenceMatcher
from src.config import load_config

logger = logging.getLogger(__name__)


class StaticLookup:
    """
    Stage 0: Instant factual lookup for UPSDM contact info, URLs, and procedures.
    
    Uses exact matching + fuzzy matching against a YAML knowledge base.
    No embedding model or LLM required. Target latency: <10ms.
    """

    def __init__(self):
        config = load_config()
        self.enabled = config.static_lookup_config.get("enabled", True)
        self.fuzzy_threshold = config.static_lookup_config.get("fuzzy_threshold", 0.80)
        
        # Load and index knowledge entries
        self.entries = config.static_knowledge.get("entries", [])
        
        # Build lookup index: alias → entry (for O(1) exact match)
        self._exact_index: dict[str, dict] = {}
        self._all_aliases: list[tuple[str, dict]] = []  # (alias, entry) for fuzzy search
        
        for entry in self.entries:
            for alias in entry.get("aliases", []):
                normalized = self._normalize(alias)
                self._exact_index[normalized] = entry
                self._all_aliases.append((normalized, entry))
        
        logger.info(f"StaticLookup initialized: {len(self.entries)} entries, "
                     f"{len(self._exact_index)} aliases indexed.")

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for matching: lowercase, strip punctuation, collapse whitespace."""
        text = text.strip().lower()
        # Remove common punctuation but keep Devanagari
        text = re.sub(r'[?!.,;:\'"()\[\]{}]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def lookup(self, query: str, lang: str = "en") -> tuple[bool, str, str]:
        """
        Attempts to match query against static knowledge base.
        
        Returns:
            (is_match, answer, intent)
            If no match: (False, "", "")
        """
        if not self.enabled or not self.entries:
            return False, "", ""

        normalized = self._normalize(query)
        
        if not normalized:
            return False, "", ""

        # Step 1: Exact match
        if normalized in self._exact_index:
            entry = self._exact_index[normalized]
            answer = self._get_answer(entry, lang)
            intent = entry.get("intent", "unknown")
            logger.info(f"StaticLookup EXACT match: query='{query}' → intent='{intent}'")
            return True, answer, intent

        # Step 2: Check if query contains an exact alias (for compound queries)
        # e.g., "what is the helpline number" contains "helpline number"
        for alias, entry in self._all_aliases:
            if len(alias) >= 4 and alias in normalized:
                answer = self._get_answer(entry, lang)
                intent = entry.get("intent", "unknown")
                logger.info(f"StaticLookup CONTAINS match: query='{query}' "
                            f"contains alias='{alias}' → intent='{intent}'")
                return True, answer, intent

        # Step 3: Fuzzy match
        best_score = 0.0
        best_entry = None
        for alias, entry in self._all_aliases:
            # Only fuzzy match if both strings are reasonably close in length
            # to avoid matching "email" against "helpline number"
            len_ratio = len(alias) / max(len(normalized), 1)
            if len_ratio < 0.3 or len_ratio > 3.0:
                continue
                
            score = SequenceMatcher(None, normalized, alias).ratio()
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= self.fuzzy_threshold and best_entry is not None:
            answer = self._get_answer(best_entry, lang)
            intent = best_entry.get("intent", "unknown")
            logger.info(f"StaticLookup FUZZY match: query='{query}' "
                        f"→ intent='{intent}' (score={best_score:.3f})")
            return True, answer, intent

        return False, "", ""

    @staticmethod
    def _get_answer(entry: dict, lang: str) -> str:
        """Returns the language-appropriate answer from an entry."""
        if lang == "hi" and "answer_hi" in entry:
            return entry["answer_hi"]
        return entry.get("answer", "")
