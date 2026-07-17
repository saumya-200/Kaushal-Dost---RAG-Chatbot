import logging
import re
from dataclasses import dataclass
from src.config import load_config

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceResult:
    """Result from the multi-signal confidence scorer."""
    level: str          # "HIGH", "MEDIUM", "LOW"
    score: float        # Weighted composite score (0.0 - 1.0)
    signals: dict       # Individual signal values for logging/debugging


class ConfidenceScorer:
    """
    Stage 3: Multi-signal retrieval confidence scorer.
    
    Combines three signals to determine retrieval confidence:
    1. top_score:  Cosine similarity of the best chunk
    2. score_gap:  Gap between #1 and #2 (high gap = clear winner)
    3. avg_top_k:  Average similarity across top-k (high = dense match)
    
    Classifies into HIGH, MEDIUM, or LOW confidence.
    """

    def __init__(self):
        config = load_config()
        thresholds = config.retrieval_thresholds
        weights_config = thresholds.get("confidence_weights", {})
        
        self.high_threshold = thresholds.get("high_confidence", 0.88)
        self.medium_threshold = thresholds.get("medium_confidence", 0.62)
        
        self.weight_top = weights_config.get("top_score", 0.50)
        self.weight_gap = weights_config.get("score_gap", 0.30)
        self.weight_avg = weights_config.get("avg_top_k", 0.20)
        
        logger.info(f"ConfidenceScorer initialized: high={self.high_threshold}, "
                     f"medium={self.medium_threshold}, "
                     f"weights=[top={self.weight_top}, gap={self.weight_gap}, avg={self.weight_avg}]")

    def score(self, results: list[dict]) -> ConfidenceResult:
        """
        Computes a weighted confidence score from FAISS search results.
        
        Args:
            results: List of FAISS search result dicts, each containing 'score' key.
        
        Returns:
            ConfidenceResult with level, composite score, and individual signals.
        """
        if not results:
            return ConfidenceResult(level="LOW", score=0.0, signals={
                "top_score": 0.0, "score_gap": 0.0, "avg_top_k": 0.0
            })

        scores = [r.get("score", 0.0) for r in results]
        
        # Signal 1: Top score
        top_score = scores[0]
        
        # Signal 2: Score gap between #1 and #2
        if len(scores) >= 2:
            score_gap = scores[0] - scores[1]
        else:
            # Only one result → treat as a definitive match
            score_gap = 0.3  # Moderate default gap
        
        # Signal 3: Average of top-k scores
        avg_top_k = sum(scores) / len(scores)
        
        # Composite weighted score
        composite = (
            self.weight_top * top_score +
            self.weight_gap * min(score_gap / 0.3, 1.0) +  # Normalize gap (0.3 max gap → 1.0)
            self.weight_avg * avg_top_k
        )
        
        # Classify
        if composite >= self.high_threshold:
            level = "HIGH"
        elif composite >= self.medium_threshold:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        signals = {
            "top_score": round(top_score, 4),
            "score_gap": round(score_gap, 4),
            "avg_top_k": round(avg_top_k, 4),
            "composite": round(composite, 4)
        }
        
        logger.info(f"ConfidenceScorer: level={level}, composite={composite:.4f}, "
                     f"top={top_score:.4f}, gap={score_gap:.4f}, avg={avg_top_k:.4f}")
        
        return ConfidenceResult(level=level, score=composite, signals=signals)

    @staticmethod
    def format_extractive_answer(chunk: dict) -> str:
        """
        Formats a raw chunk for direct extractive response.
        
        Cleans up the raw text:
        - Strips markdown links
        - Removes raw URLs and file paths
        - Normalizes whitespace
        - Adds source citation
        """
        text = chunk.get("text", "")
        
        # Strip markdown links: [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove raw URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove file paths like /Content/xxx.pdf
        text = re.sub(r'/\S+\.\w+', '', text)
        
        # Remove link metadata patterns like 'Link: "text" leads to /path'
        text = re.sub(r'- Link:\s*"[^"]*"\s*leads to\s*\S+', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Trim to reasonable length
        if len(text) > 500:
            # Cut at last sentence boundary
            truncated = text[:500]
            last_period = max(truncated.rfind('.'), truncated.rfind('।'))
            if last_period > 200:
                text = truncated[:last_period + 1]
            else:
                text = truncated + "..."
        
        # Add source citation
        source_url = chunk.get("source_url", "upsdm.gov.in")
        # Simplify the source URL for display
        source_display = source_url.replace("https://www.", "").replace("https://", "").replace("http://", "")
        
        if text:
            return f"{text}\n\n(Source: {source_display})"
        
        return text
