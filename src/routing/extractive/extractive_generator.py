import re
import logging
import numpy as np
from src.config import load_config
from src.embeddings.embed import Embedder

logger = logging.getLogger(__name__)

class ExtractiveGenerator:
    """
    Computes Retrieval Confidence and extracts the most relevant sentences
    from FAISS search chunks to form a factual, CPU-only answer without LLM generation.
    """
    def __init__(self, embedder: Embedder = None):
        self.config = load_config()
        self.embedder = embedder if embedder is not None else Embedder()
        
        # Load weights and thresholds from thresholds.yaml under 'routing' key
        routing_config = self.config.routing_config
        self.extraction_threshold = routing_config.get("extraction_threshold", 0.65)
        
        weights = routing_config.get("retrieval_weights", {})
        self.weight_top = weights.get("top_score", 0.40)
        self.weight_avg = weights.get("avg_top_k", 0.20)
        self.weight_gap = weights.get("score_gap", 0.15)
        self.weight_meta = weights.get("metadata_quality", 0.10)
        self.weight_len = weights.get("chunk_length", 0.05)
        self.weight_diversity = weights.get("source_diversity", 0.10)

    def compute_retrieval_confidence(self, results: list[dict]) -> tuple[str, float, dict]:
        """
        Computes a composite retrieval confidence score from FAISS results.
        Returns: (confidence_level, composite_score, signals)
        """
        if not results:
            return "LOW", 0.0, {}
            
        scores = [r.get("score", 0.0) for r in results]
        
        # Signal 1: Top-1 similarity
        top_score = scores[0]
        
        # Signal 2: Average similarity across top-k (max top-3)
        top_k_scores = scores[:3]
        avg_top_k = sum(top_k_scores) / len(top_k_scores)
        
        # Signal 3: Gap between top-1 and top-2
        if len(scores) >= 2:
            score_gap = scores[0] - scores[1]
        else:
            score_gap = 0.25 # default fallback
        normalized_gap = min(score_gap / 0.25, 1.0)
        
        # Signal 4: Metadata quality (presence of chunk_id and source_url)
        meta_count = 0
        total_meta = len(results[:3]) * 2
        for r in results[:3]:
            if r.get("chunk_id"): meta_count += 1
            if r.get("source_url"): meta_count += 1
        meta_score = meta_count / max(total_meta, 1)
        
        # Signal 5: Chunk length (if top chunks have sufficient context, e.g. >120 chars)
        len_score = 0.0
        for r in results[:3]:
            if len(r.get("text", "")) > 120:
                len_score += 1.0
        len_score = len_score / len(results[:3])
        
        # Signal 6: Source diversity (unique source files/URLs in top-k)
        sources = set()
        for r in results[:3]:
            sources.add(r.get("source_url", r.get("source_id", "")))
        diversity_score = min(len(sources) / 2.0, 1.0) # max 2 sources = 1.0
        
        # Composite score
        composite = (
            self.weight_top * top_score +
            self.weight_avg * avg_top_k +
            self.weight_gap * normalized_gap +
            self.weight_meta * meta_score +
            self.weight_len * len_score +
            self.weight_diversity * diversity_score
        )
        
        level = "HIGH" if composite >= self.extraction_threshold else "LOW"
        
        signals = {
            "top_score": round(top_score, 4),
            "avg_top_k": round(avg_top_k, 4),
            "score_gap": round(score_gap, 4),
            "meta_score": round(meta_score, 4),
            "len_score": round(len_score, 4),
            "diversity_score": round(diversity_score, 4),
            "composite": round(composite, 4)
        }
        
        return level, composite, signals

    def _split_into_sentences(self, text: str) -> list[str]:
        """Splits English and Hindi paragraphs into sentences."""
        # Split on period, question mark, exclamation, or Devanagari danda ।
        raw_sentences = re.split(r'(?<=[.!?।])\s+', text)
        sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if s_clean and len(s_clean) > 8:
                sentences.append(s_clean)
        return sentences

    def generate_extractive_answer(self, query: str, query_embedding: np.ndarray, results: list[dict]) -> str:
        """
        Extracts and joins the most relevant sentences from the top FAISS chunks.
        Avoids hallucination and preserves official wording.
        """
        if not results:
            return ""
            
        top_chunks = results[:2] # extract from top 2 chunks
        
        all_sentences = []
        seen_sentences = set()
        
        for idx, chunk in enumerate(top_chunks):
            chunk_text = chunk.get("text", "")
            sentences = self._split_into_sentences(chunk_text)
            for s in sentences:
                s_normalized = s.lower().strip()
                if s_normalized not in seen_sentences:
                    seen_sentences.add(s_normalized)
                    all_sentences.append({
                        "text": s,
                        "source": chunk.get("source_url", "upsdm.gov.in"),
                        "chunk_index": idx
                    })
                    
        if not all_sentences:
            return ""
            
        # Score each sentence for relevance to the query
        query_words = set(query.lower().strip().split())
        scored_sentences = []
        
        for item in all_sentences:
            sentence_text = item["text"]
            # Signal 1: Cosine similarity of sentence to query
            sentence_embedding = self.embedder.embed_query(sentence_text)
            sim = float(np.dot(sentence_embedding.flatten(), query_embedding.flatten()))
            
            # Signal 2: Word overlap
            sent_words = set(sentence_text.lower().strip().split())
            overlap = len(query_words & sent_words) / max(len(query_words), 1)
            
            # Composite relevance
            relevance = 0.6 * sim + 0.4 * overlap
            scored_sentences.append((relevance, item))
            
        # Sort sentences by relevance score descending
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        # Pick top 2-3 sentences. Preserve original chunk order if possible, or source order.
        selected_items = []
        for relevance, item in scored_sentences[:3]:
            # Minimum relevance filter to keep sentences on-topic
            if relevance > 0.35:
                selected_items.append(item)
                
        # If no sentences pass the relevance filter, fall back to the top chunk's raw sentences
        if not selected_items:
            selected_items = all_sentences[:2]
            
        # Sort by chunk_index to maintain reading flow/narrative of the source text
        selected_items.sort(key=lambda x: (x["chunk_index"], all_sentences.index(x)))
        
        extracted_text = " ".join([item["text"] for item in selected_items])
        
        # Clean formatting
        extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
        
        # Get source metadata from top chunk
        primary_source = results[0].get("source_url", "upsdm.gov.in")
        source_display = primary_source.replace("https://www.", "").replace("https://", "").replace("http://", "")
        
        answer = f"According to official UPSDM guidelines from {source_display}:\n{extracted_text}\n\n(Source: {source_display})"
        return answer
