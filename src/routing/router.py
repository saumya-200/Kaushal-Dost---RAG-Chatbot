import hashlib
import json
import logging
import re
import time
import numpy as np
import redis
from pathlib import Path

from src.config import load_config
from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex
from src.ingestion.text_extractor import TextExtractor

logger = logging.getLogger(__name__)

class Router:
    def __init__(self, db_host: str = "localhost", db_port: int = 6379):
        self.config = load_config()
        self.embedder = Embedder()
        self.faiss_index = FAISSIndex()
        self.extractor = TextExtractor()
        
        # Load FAISS index if it exists
        try:
            self.faiss_index.load()
        except Exception as e:
            logger.warning(f"Could not load FAISS index during router initialization: {e}")
            
        # Connect to Redis
        self.redis_client = None
        self.use_cache = False
        try:
            self.redis_client = redis.Redis(
                host=db_host, 
                port=db_port, 
                decode_responses=True,
                socket_timeout=2.0
            )
            # Test connection
            self.redis_client.ping()
            self.use_cache = True
            logger.info("Connected to Redis semantic cache successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis. Semantic cache will be disabled: {e}")
            
        # In-memory synchronization of cached queries and embeddings for fast vector search
        self.cached_queries = []      # list of dicts: {'query': str, 'response': str, 'stage': str, 'key': str}
        self.cached_embeddings = []   # list of np.ndarray: embeddings of shape (384,)
        
        if self.use_cache:
            self._sync_cache_from_redis()

    def _sync_cache_from_redis(self):
        """Loads all cached items from Redis to memory for fast vector comparison."""
        try:
            keys = self.redis_client.keys("semantic_cache:item:*")
            logger.info(f"Syncing {len(keys)} cached entries from Redis...")
            
            for key in keys:
                data_str = self.redis_client.get(key)
                if data_str:
                    data = json.loads(data_str)
                    query = data.get("query")
                    response = data.get("response")
                    embedding_list = data.get("embedding")
                    stage = data.get("stage_used", "semantic_cache")
                    
                    if query and response and embedding_list:
                        self.cached_queries.append({
                            "query": query,
                            "response": response,
                            "stage": stage,
                            "key": key
                        })
                        self.cached_embeddings.append(np.array(embedding_list, dtype="float32"))
            
            logger.info(f"Cache sync complete. Total in-memory cache size: {len(self.cached_queries)}")
        except Exception as e:
            logger.error(f"Error syncing semantic cache from Redis: {e}")

    def is_greeting(self, query: str) -> bool:
        """Detects if the query is a simple greeting or small talk."""
        cleaned = query.strip().lower().replace("?", "").replace("!", "")
        
        # Core greeting tokens
        greeting_words = {
            # English
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "welcome", "howdy",
            # Hindi (Latin/Romanized)
            "namaste", "pranam", "namaskar", "ram ram", "radhe radhe", "pranaam",
            # Hindi (Devanagari)
            "नमस्ते", "नमस्कार", "प्रणाम", "राम राम", "राधे राधे", "हेलो", "हाय"
        }
        
        # If the query itself is a greeting word
        if cleaned in greeting_words:
            return True
            
        # Check if the query is short (1-2 words) and contains any of the greeting words
        words = cleaned.split()
        if len(words) <= 2 and any(w in greeting_words for w in words):
            return True
            
        return False

    def get_greeting_response(self, lang: str) -> str:
        """Retrieves a configured greeting response based on language."""
        responses = self.config.greeting_responses.get(lang, self.config.greeting_responses.get("en", []))
        if responses:
            # Deterministic/semi-deterministic select (or random)
            # We return the first one for consistency in test runs, or we can use random
            return responses[0]
        return "Hello! How can I help you today?"

    def get_fallback_response(self, lang: str) -> str:
        """Retrieves the configured fallback response based on language."""
        return self.config.fallback_responses.get(lang, self.config.fallback_responses.get("en", ""))

    def check_semantic_cache(self, query_embedding: np.ndarray) -> tuple[bool, str, str]:
        """
        Compares query embedding against all cached query embeddings.
        Returns: (is_hit, cached_response, matched_query)
        """
        if not self.use_cache or not self.cached_queries:
            return False, "", ""
            
        threshold = self.config.cache_config.get("similarity_threshold", 0.92)
        
        # Stack all cached embeddings: shape (N, 384)
        embeddings_matrix = np.vstack(self.cached_embeddings)
        
        # Calculate cosine similarity (dot product since embeddings are normalized)
        # query_embedding shape is (1, 384)
        similarities = np.dot(embeddings_matrix, query_embedding.flatten())
        
        max_idx = np.argmax(similarities)
        max_score = similarities[max_idx]
        
        if max_score >= threshold:
            match = self.cached_queries[max_idx]
            logger.info(f"Semantic Cache HIT. Score: {max_score:.4f}. Matched: '{match['query']}'")
            return True, match["response"], match["query"]
            
        return False, "", ""

    def add_to_cache(self, query: str, query_embedding: np.ndarray, response: str, stage_used: str):
        """Stores a query, its embedding, and response in Redis and in-memory cache."""
        if not self.use_cache:
            return
            
        try:
            # Check size limits
            max_entries = self.config.cache_config.get("max_entries", 10000)
            if len(self.cached_queries) >= max_entries:
                # Simple eviction: evict first item
                evict_item = self.cached_queries.pop(0)
                self.cached_embeddings.pop(0)
                try:
                    self.redis_client.delete(evict_item["key"])
                except Exception:
                    pass
            
            # Save to Redis
            query_hash = hashlib.md5(query.lower().strip().encode('utf-8')).hexdigest()
            key = f"semantic_cache:item:{query_hash}"
            
            ttl = self.config.cache_config.get("ttl_seconds", 3600)
            
            data = {
                "query": query,
                "embedding": query_embedding.flatten().tolist(),
                "response": response,
                "stage_used": stage_used,
                "timestamp": time.time()
            }
            
            self.redis_client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
            
            # Sync in memory
            self.cached_queries.append({
                "query": query,
                "response": response,
                "stage": stage_used,
                "key": key
            })
            self.cached_embeddings.append(query_embedding.flatten())
            logger.info(f"Added to semantic cache: '{query}'")
            
        except Exception as e:
            logger.error(f"Error adding to Redis semantic cache: {e}")

    def route(self, query: str) -> tuple[str, str, dict]:
        """
        Routes the user query through the multi-stage pipeline.
        Returns: (stage_used, answer, metadata)
        """
        metadata = {}
        
        # Detect language
        lang = self.extractor.detect_language(query)
        metadata["detected_language"] = lang
        
        # Stage 1: Greeting/Small-Talk
        if self.is_greeting(query):
            response = self.get_greeting_response(lang)
            return "greeting", response, metadata
            
        # Embed query
        q_emb = self.embedder.embed_query(query)
        
        # Stage 2: Semantic Cache
        is_hit, cached_response, matched_query = self.check_semantic_cache(q_emb)
        if is_hit:
            metadata["cached_query_match"] = matched_query
            return "semantic_cache", cached_response, metadata
            
        # Stage 3: FAISS Confidence-Based Retrieval
        results = self.faiss_index.search(q_emb, top_k=3)
        metadata["retrieved_chunks"] = results
        
        high_thresh = self.config.retrieval_thresholds.get("high_confidence", 0.90)
        med_thresh = self.config.retrieval_thresholds.get("medium_confidence", 0.65)
        
        if not results:
            fallback = self.get_fallback_response(lang)
            return "fallback", fallback, metadata
            
        top_chunk = results[0]
        score = top_chunk["score"]
        metadata["top_score"] = score
        
        # FAISS Direct Answer (High Confidence)
        if score >= high_thresh:
            response = top_chunk["text"]
            # Save to semantic cache
            self.add_to_cache(query, q_emb, response, "faiss_direct")
            return "faiss_direct", response, metadata
            
        # Route to LLM (Medium Confidence)
        elif score >= med_thresh:
            # LLM prompt and generation (Phase 5).
            # We call Ollama if it's running and retrieve/generate.
            response = self._generate_llm_response(query, results, lang)
            self.add_to_cache(query, q_emb, response, "llm")
            return "llm", response, metadata
            
        # Fallback (Low Confidence)
        else:
            response = self.get_fallback_response(lang)
            # Do NOT cache fallback responses to avoid polluting semantic cache
            return "fallback", response, metadata

    def _generate_llm_response(self, query: str, chunks: list[dict], lang: str) -> str:
        """Queries the local Ollama instance with context chunks."""
        import httpx
        
        # Format context chunks
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"Source [{chunk.get('title', 'Document')}]: {chunk.get('text')}")
        context_text = "\n\n".join(context_parts)
        
        # Load prompt and system prompt rules
        system_prompt = self.config.system_prompt
        
        # Generate prompt
        prompt = f"Context information is below.\n---------------------\n{context_text}\n---------------------\nGiven the context information and not prior knowledge, answer the query.\nQuery: {query}\nAnswer:"
        
        primary_model = self.config.llm_config.get("primary_model", "qwen3:4b")
        timeout = float(self.config.llm_config.get("timeout_seconds", 30))
        
        try:
            # Standard Ollama chat API request
            url = "http://localhost:11434/api/chat"
            payload = {
                "model": primary_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for factual consistency
                    "num_predict": 2048  # Large enough token budget to support thinking + response
                }
            }
            
            logger.info(f"Calling Ollama model {primary_model}...")
            r = httpx.post(url, json=payload, timeout=timeout)
            if r.status_code == 200:
                result = r.json()
                answer = result.get("message", {}).get("content", "").strip()
                if answer:
                    return answer
                    
            logger.warning(f"Ollama returned status {r.status_code}. Falling back to default mock answer.")
        except Exception as e:
            logger.error(f"Error calling local Ollama instance: {e}")
            
        # Mock LLM answer if Ollama call fails (e.g. timeout or down)
        # Returns the text of the first chunk to maintain context
        return f"[Draft RAG Response] Based on the official details, {chunks[0]['text'][:150]}..."
