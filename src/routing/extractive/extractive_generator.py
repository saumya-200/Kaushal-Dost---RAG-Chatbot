import re
import logging
import numpy as np
from src.config import load_config
from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex
from src.ingestion.sentence_splitter import split_into_sentences

logger = logging.getLogger(__name__)

class ExtractiveGenerator:
    """
    Computes Retrieval Confidence and extracts the most relevant sentences
    from FAISS search chunks to form a factual, CPU-only answer without LLM generation.
    Uses precomputed sentence embeddings when available to eliminate live encoding latency.
    """
    def __init__(self, embedder: Embedder = None, faiss_index: FAISSIndex = None):
        self.config = load_config()
        self.embedder = embedder if embedder is not None else Embedder()
        self.faiss_index = faiss_index if faiss_index is not None else FAISSIndex()
        
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
        # Exclude administrative_list chunks from FAISS_DIRECT retrieval candidates
        valid_results = [r for r in results if r.get("content_type") != "administrative_list"]
        if not valid_results:
            return "LOW", 0.0, {}
            
        scores = [r.get("score", 0.0) for r in valid_results]
        
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
        total_meta = len(valid_results[:3]) * 2
        for r in valid_results[:3]:
            if r.get("chunk_id"): meta_count += 1
            if r.get("source_url"): meta_count += 1
        meta_score = meta_count / max(total_meta, 1)
        
        # Signal 5: Chunk length (if top chunks have sufficient context, e.g. >120 chars)
        len_score = 0.0
        for r in valid_results[:3]:
            if len(r.get("text", "")) > 120:
                len_score += 1.0
        len_score = len_score / len(valid_results[:3])
        
        # Signal 6: Source diversity (unique source files/URLs in top-k)
        sources = set()
        for r in valid_results[:3]:
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
        """Splits English and Hindi paragraphs into sentences using shared splitter."""
        return split_into_sentences(text)

    def generate_extractive_answer(self, query: str, query_embedding: np.ndarray, results: list[dict]) -> str:
        """
        Extracts and joins the most relevant sentences from the top FAISS chunks.
        Avoids hallucination and preserves official wording.
        """
        valid_results = [r for r in results if r.get("content_type") != "administrative_list"]
        if not valid_results:
            return ""
            
        top_chunks = valid_results[:2] # extract from top 2 chunks
        chunk_ids = [c.get("chunk_id") for c in top_chunks if c.get("chunk_id")]
        
        # Fetch precomputed sentence embeddings from FAISSIndex
        found_sentences, missing_chunk_ids = self.faiss_index.get_sentences_for_chunks(chunk_ids)
        
        all_sentences = []
        seen_sentences = set()
        
        for idx, chunk in enumerate(top_chunks):
            cid = chunk.get("chunk_id")
            if cid in missing_chunk_ids or not cid:
                # Fallback path: live encoding for chunks missing from precomputed sentence index
                logger.warning(f"Chunk {cid} missing from precomputed sentence index; falling back to live encoding.")
                chunk_text = chunk.get("text", "")
                sentences = split_into_sentences(chunk_text)
                for s in sentences:
                    s_normalized = s.lower().strip()
                    if s_normalized not in seen_sentences:
                        seen_sentences.add(s_normalized)
                        emb = self.embedder.embed_query(s) # live encoding fallback
                        all_sentences.append({
                            "text": s,
                            "source": chunk.get("source_url", "upsdm.gov.in"),
                            "chunk_index": idx,
                            "embedding": emb.flatten()
                        })
            else:
                # Fast path: precomputed sentence embeddings
                chunk_sents = [s for s in found_sentences if s["chunk_id"] == cid]
                for s in chunk_sents:
                    s_text = s["text"]
                    s_normalized = s_text.lower().strip()
                    if s_normalized not in seen_sentences:
                        seen_sentences.add(s_normalized)
                        all_sentences.append({
                            "text": s_text,
                            "source": chunk.get("source_url", "upsdm.gov.in"),
                            "chunk_index": idx,
                            "embedding": s["embedding"].flatten()
                        })
                        
        if not all_sentences:
            return ""
            
        # Score each sentence for relevance to the query
        query_words = set(query.lower().strip().split())
        query_vec = query_embedding.flatten()
        scored_sentences = []
        
        for item in all_sentences:
            sentence_text = item["text"]
            sentence_embedding = item["embedding"]
            
            # Signal 1: Cosine similarity of sentence to query via dot product (vectors are normalized)
            sim = float(np.dot(sentence_embedding, query_vec))
            
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
        primary_source = valid_results[0].get("source_url", "upsdm.gov.in")
        source_display = primary_source.replace("https://www.", "").replace("https://", "").replace("http://", "")
        
        answer = f"According to official UPSDM guidelines from {source_display}:\n{extracted_text}\n\n(Source: {source_display})"
        return answer
