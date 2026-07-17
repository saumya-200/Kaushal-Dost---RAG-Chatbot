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
from src.llm.generator import LLMGenerator
from src.routing.static_lookup import StaticLookup
from src.routing.scope_detector import ScopeDetector
from src.routing.confidence import ConfidenceScorer, ConfidenceResult

logger = logging.getLogger(__name__)

class Router:
    def __init__(self, db_host: str = None, db_port: int = None):
        import os
        if db_host is None:
            db_host = os.environ.get("REDIS_HOST", "localhost")
        if db_port is None:
            try:
                db_port = int(os.environ.get("REDIS_PORT", 6379))
            except ValueError:
                db_port = 6379

        self.config = load_config()
        self.embedder = Embedder()
        self.faiss_index = FAISSIndex()
        self.extractor = TextExtractor()
        
        # New Stage 0: Static Lookup
        self.static_lookup = StaticLookup()
        
        # New Stage 1: Scope Detector
        self.scope_detector = ScopeDetector()
        
        # New Stage 3: Confidence Scorer
        self.confidence_scorer = ConfidenceScorer()
        
        # Stage 4: LLM Generator
        ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.generator = LLMGenerator(ollama_host=ollama_host)
        
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

    async def route(self, query: str, history: list[dict] = None) -> tuple[str, str, dict]:
        """
        Routes the user query through the 5-stage LLM-last pipeline.
        
        Stage 0a: Greeting detection (instant)
        Stage 0b: Static factual lookup (instant)
        Stage 1:  Scope detection (embedding-based, no LLM)
        Stage 2:  Semantic cache check
        Stage 3:  FAISS retrieval + confidence scoring → extractive or LLM
        Stage 4:  LLM synthesis (last resort)
        
        Returns: (stage_used, answer, metadata)
        """
        t_start = time.time()
        metadata = {}
        
        # Detect language
        lang = self.extractor.detect_language(query)
        metadata["detected_language"] = lang
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 0a: Greeting / Small-Talk (<5ms)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self.is_greeting(query):
            response = self.get_greeting_response(lang)
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=greeting, latency={metadata['stage_latency_ms']}ms")
            return "greeting", response, metadata
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 0b: Static Factual Lookup (<10ms)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        is_static, static_answer, intent = self.static_lookup.lookup(query, lang)
        if is_static:
            metadata["static_intent"] = intent
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=static_lookup, intent={intent}, "
                        f"latency={metadata['stage_latency_ms']}ms")
            return "static_lookup", static_answer, metadata
            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # EMBED QUERY (once, reused across stages)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        t_embed = time.time()
        q_emb = self.embedder.embed_query(query)
        metadata["embed_latency_ms"] = round((time.time() - t_embed) * 1000, 2)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 1: Scope Detection (<100ms)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Run a lightweight FAISS search for scope check (top_k=3 — reused later)
        results = self.faiss_index.search(q_emb, top_k=3)
        metadata["retrieved_chunks"] = results
        
        in_scope, scope_score, scope_reason = self.scope_detector.is_in_scope(query, results)
        metadata["scope_score"] = scope_score
        metadata["scope_reason"] = scope_reason
        
        if not in_scope:
            response = self.get_fallback_response(lang)
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=out_of_scope, reason={scope_reason}, "
                        f"score={scope_score:.4f}, latency={metadata['stage_latency_ms']}ms")
            # Do NOT cache scope rejections to avoid polluting the cache
            return "out_of_scope", response, metadata
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 2: Semantic Cache (<50ms)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        is_hit, cached_response, matched_query = self.check_semantic_cache(q_emb)
        if is_hit:
            metadata["cached_query_match"] = matched_query
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=semantic_cache, matched='{matched_query}', "
                        f"latency={metadata['stage_latency_ms']}ms")
            return "semantic_cache", cached_response, metadata
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 3: FAISS Retrieval + Confidence
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Results already fetched in Stage 1 — reuse them
        if not results:
            response = self.get_fallback_response(lang)
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=fallback (no results), "
                        f"latency={metadata['stage_latency_ms']}ms")
            return "fallback", response, metadata
        
        # Compute multi-signal confidence
        confidence = self.confidence_scorer.score(results)
        metadata["confidence_level"] = confidence.level
        metadata["confidence_score"] = confidence.score
        metadata["confidence_signals"] = confidence.signals
        metadata["top_score"] = results[0].get("score", 0.0)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # HIGH CONFIDENCE → Extractive Mode
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if confidence.level == "HIGH":
            top_chunk = results[0]
            response = ConfidenceScorer.format_extractive_answer(top_chunk)
            self.add_to_cache(query, q_emb, response, "faiss_direct")
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=faiss_direct (extractive), "
                        f"confidence={confidence.score:.4f}, "
                        f"latency={metadata['stage_latency_ms']}ms")
            return "faiss_direct", response, metadata
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # MEDIUM CONFIDENCE → LLM Synthesis (Stage 4)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if confidence.level == "MEDIUM":
            t_llm = time.time()
            response = await self.generator.generate_answer(query, results, history)
            metadata["llm_latency_ms"] = round((time.time() - t_llm) * 1000, 2)
            self.add_to_cache(query, q_emb, response, "llm_generation")
            metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
            logger.info(f"ROUTING: stage=llm_generation, "
                        f"confidence={confidence.score:.4f}, "
                        f"llm_latency={metadata['llm_latency_ms']}ms, "
                        f"total_latency={metadata['stage_latency_ms']}ms")
            return "llm_generation", response, metadata
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LOW CONFIDENCE → Fallback
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        response = self.get_fallback_response(lang)
        metadata["stage_latency_ms"] = round((time.time() - t_start) * 1000, 2)
        logger.info(f"ROUTING: stage=fallback (low confidence), "
                    f"confidence={confidence.score:.4f}, "
                    f"latency={metadata['stage_latency_ms']}ms")
        # Do NOT cache fallback responses to avoid polluting semantic cache
        return "fallback", response, metadata
