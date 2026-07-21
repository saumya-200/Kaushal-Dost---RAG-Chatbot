import re
import logging
import numpy as np
from difflib import SequenceMatcher
from src.config import load_config
from src.embeddings.embed import Embedder

logger = logging.getLogger(__name__)

class TemplateMatcher:
    """
    Finds the best matching static template for a query using multi-signal scoring:
    Score = 0.40 * Embedding + 0.25 * Keyword + 0.20 * Intent + 0.15 * Persona.
    
    Includes Ambiguity Detection and Fail-Closed thresholding.
    """
    def __init__(self, embedder: Embedder = None):
        self.config = load_config()
        self.embedder = embedder if embedder is not None else Embedder()
        
        # Load configs
        routing_config = self.config.routing_config
        self.template_threshold = routing_config.get("template_threshold", 0.70)
        self.ambiguity_margin = routing_config.get("ambiguity_margin", 0.03)
        
        weights = routing_config.get("template_weights", {})
        self.weight_emb = weights.get("embedding_similarity", 0.40)
        self.weight_kw = weights.get("keyword_match", 0.25)
        self.weight_intent = weights.get("intent_confidence", 0.20)
        self.weight_persona = weights.get("persona_confidence", 0.15)
        
        self.entries = self.config.static_knowledge.get("entries", [])
        
        # Pre-embed and index all aliases for all templates
        self.template_embeddings = []  # list of tuples: (entry, alias, normalized_alias, embedding_vector)
        for entry in self.entries:
            for alias in entry.get("aliases", []):
                norm_alias = self._normalize(alias)
                emb = self.embedder.embed_query(alias)
                self.template_embeddings.append({
                    "entry": entry,
                    "alias": alias,
                    "norm_alias": norm_alias,
                    "embedding": emb.flatten()
                })
        
        logger.info(f"TemplateMatcher initialized: {len(self.entries)} templates with "
                    f"{len(self.template_embeddings)} aliases embedded.")

    def _normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r'[?!.,;:\'"()\[\]{}]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _calculate_keyword_score(self, query: str, query_words: set[str], norm_alias: str) -> float:
        """Computes overlap ratio and sequence matcher ratio."""
        alias_words = set(norm_alias.split())
        if not alias_words:
            return 0.0
        
        # Word overlap
        overlap = len(query_words & alias_words) / len(alias_words)
        
        # Sequence matcher ratio (for fuzzy matching)
        seq_ratio = SequenceMatcher(None, query, norm_alias).ratio()
        
        # Take the maximum/weighted combination
        return max(overlap, seq_ratio)

    def match(self, query: str, query_embedding: np.ndarray, detected_persona: str, detected_intent: str, lang: str = "en") -> tuple[str, str, dict]:
        """
        Matches a query against templates belonging to the detected persona.
        
        Returns:
            (match_status, answer, metadata)
            match_status can be: "success", "ambiguous", "low_confidence"
        """
        if not self.entries:
            return "low_confidence", "", {}
            
        norm_query = self._normalize(query)
        query_words = set(norm_query.split())
        
        candidate_scores = []
        
        # We group scores by template (entry) so a template with multiple aliases gets its best alias score.
        for entry in self.entries:
            entry_persona = entry.get("persona", "General Public")
            entry_intent = entry.get("intent", "General")
            
            # Persona Filtering:
            # If a query is classified into a specific persona (like Student, TP, Industry, Assessment),
            # we should ONLY allow templates of that persona or templates belonging to "General Public".
            # This isolates the intents and prevents wrong-persona templates from matching!
            if detected_persona not in ("Unknown", "General Public"):
                if entry_persona not in (detected_persona, "General Public"):
                    continue
            
            # Calculate Persona match score
            if entry_persona == detected_persona:
                persona_score = 1.0
            elif entry_persona == "General Public":
                persona_score = 0.5
            else:
                persona_score = 0.0
                
            # Calculate Intent match score
            if entry_intent == detected_intent:
                intent_score = 1.0
            elif entry_intent == "General":
                intent_score = 0.5
            else:
                intent_score = 0.0
                
            # Find the best alias match for this template
            best_alias_score = -1.0
            best_alias_emb_similarity = 0.0
            best_alias_kw_overlap = 0.0
            
            # Filter aliases for this entry
            aliases_for_entry = [te for te in self.template_embeddings if te["entry"] == entry]
            
            for te in aliases_for_entry:
                # 1. Cosine similarity
                emb_similarity = float(np.dot(te["embedding"], query_embedding.flatten()))
                
                # 2. Keyword overlap
                kw_overlap = self._calculate_keyword_score(norm_query, query_words, te["norm_alias"])
                
                # Composite score for this alias
                alias_composite = (
                    self.weight_emb * emb_similarity +
                    self.weight_kw * kw_overlap +
                    self.weight_intent * intent_score +
                    self.weight_persona * persona_score
                )
                
                if alias_composite > best_alias_score:
                    best_alias_score = alias_composite
                    best_alias_emb_similarity = emb_similarity
                    best_alias_kw_overlap = kw_overlap
                    
            if best_alias_score >= 0:
                candidate_scores.append({
                    "entry": entry,
                    "score": best_alias_score,
                    "emb_similarity": best_alias_emb_similarity,
                    "kw_overlap": best_alias_kw_overlap,
                    "intent_score": intent_score,
                    "persona_score": persona_score
                })
                
        if not candidate_scores:
            return "low_confidence", "", {}
            
        # Sort candidates by score descending
        candidate_scores.sort(key=lambda x: x["score"], reverse=True)
        
        top_match = candidate_scores[0]
        top_score = top_match["score"]
        
        # Check Ambiguity
        if len(candidate_scores) >= 2:
            runner_up = candidate_scores[1]
            runner_up_score = runner_up["score"]
            score_diff = top_score - runner_up_score
            
            if score_diff < self.ambiguity_margin:
                logger.warning(f"Ambiguity detected: top score={top_score:.4f} "
                               f"('{top_match['entry'].get('intent')}') vs runner-up score={runner_up_score:.4f} "
                               f"('{runner_up['entry'].get('intent')}')")
                return "ambiguous", "", {
                    "top_match_intent": top_match["entry"].get("intent"),
                    "runner_up_intent": runner_up["entry"].get("intent"),
                    "score_diff": score_diff,
                    "top_score": top_score,
                    "runner_up_score": runner_up_score
                }
                
        # Check Fail-Closed Threshold
        if top_score < self.template_threshold:
            logger.info(f"TemplateMatch low confidence: score={top_score:.4f} < threshold={self.template_threshold}")
            return "low_confidence", "", {"top_score": top_score, "intent_matched": top_match["entry"].get("intent")}
            
        # Success matching! Get the answer in the correct language
        entry = top_match["entry"]
        answer = entry.get("answer", "")
        if lang == "hi" and "answer_hi" in entry and entry["answer_hi"]:
            answer = entry["answer_hi"]
            
        meta = {
            "score": round(top_score, 4),
            "intent": entry.get("intent"),
            "persona": entry.get("persona"),
            "emb_similarity": round(top_match["emb_similarity"], 4),
            "kw_overlap": round(top_match["kw_overlap"], 4)
        }
        
        return "success", answer, meta
