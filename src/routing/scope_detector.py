import logging
import numpy as np
from src.config import load_config

logger = logging.getLogger(__name__)


class ScopeDetector:
    """
    Stage 1: Lightweight scope detector using embedding similarity.
    
    Determines whether a query is within the UPSDM domain by checking
    FAISS top-1 similarity against a threshold. Also supports instant 
    rejection via anti-scope keywords.
    
    No LLM required. Reuses query embedding already computed by the router.
    """

    def __init__(self):
        config = load_config()
        scope_config = config.scope_config
        
        self.enabled = scope_config.get("enabled", True)
        self.similarity_threshold = scope_config.get("similarity_threshold", 0.45)
        self.anti_scope_keywords = [
            kw.lower() for kw in scope_config.get("anti_scope_keywords", [])
        ]
        
        logger.info(f"ScopeDetector initialized: threshold={self.similarity_threshold}, "
                     f"anti_keywords={len(self.anti_scope_keywords)}")

    def is_in_scope(self, query: str, faiss_results: list[dict]) -> tuple[bool, float, str]:
        """
        Checks if a query is within the UPSDM scope.
        
        Args:
            query: The raw user query string.
            faiss_results: Results from FAISS search (top_k=1 is sufficient).
        
        Returns:
            (in_scope, best_score, reason)
            - in_scope: True if the query is about UPSDM
            - best_score: The top FAISS similarity score
            - reason: Why the decision was made (for logging)
        """
        if not self.enabled:
            return True, 1.0, "scope_disabled"

        query_lower = query.strip().lower()

        # Step 1: Anti-scope keyword check (instant rejection, <1ms)
        for keyword in self.anti_scope_keywords:
            if keyword in query_lower:
                logger.info(f"ScopeDetector REJECT (anti-keyword): "
                            f"query='{query}' matched keyword='{keyword}'")
                return False, 0.0, f"anti_keyword:{keyword}"

        # Step 2: FAISS similarity check
        if not faiss_results:
            logger.info(f"ScopeDetector REJECT (no results): query='{query}'")
            return False, 0.0, "no_faiss_results"

        best_score = faiss_results[0].get("score", 0.0)

        if best_score < self.similarity_threshold:
            logger.info(f"ScopeDetector REJECT (low similarity): "
                        f"query='{query}', score={best_score:.4f} < {self.similarity_threshold}")
            return False, best_score, f"low_similarity:{best_score:.4f}"

        logger.info(f"ScopeDetector ACCEPT: query='{query}', score={best_score:.4f}")
        return True, best_score, "in_scope"
