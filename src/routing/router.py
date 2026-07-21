import hashlib
import json
import logging
import re
import time
from pathlib import Path
import numpy as np
import redis

from src.config import load_config
from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex
from src.ingestion.text_extractor import TextExtractor

# Import redesigned modules
from src.routing.greetings.greeting_detector import GreetingDetector
from src.routing.persona.persona_classifier import PersonaClassifier
from src.routing.intent.intent_classifier import IntentClassifier
from src.routing.template_matching.template_matcher import TemplateMatcher
from src.routing.extractive.extractive_generator import ExtractiveGenerator
from src.routing.sanitizer.sanitizer import ResponseSanitizer
from src.routing.scope_detector import ScopeDetector

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
        
        # Redesigned modules
        self.greeting_detector = GreetingDetector()
        self.persona_classifier = PersonaClassifier(self.embedder)
        self.intent_classifier = IntentClassifier(self.embedder)
        self.template_matcher = TemplateMatcher(self.embedder)
        self.extractive_generator = ExtractiveGenerator(self.embedder, self.faiss_index)
        self.sanitizer = ResponseSanitizer()
        self.scope_detector = ScopeDetector()
        
        # Load FAISS index
        try:
            self.faiss_index.load()
        except Exception as e:
            logger.warning(f"Could not load FAISS index during router initialization: {e}")
            
        # Connect to Redis for cache
        self.redis_client = None
        self.use_cache = False
        try:
            self.redis_client = redis.Redis(
                host=db_host, 
                port=db_port, 
                decode_responses=True,
                socket_timeout=2.0
            )
            self.redis_client.ping()
            self.use_cache = True
            logger.info("Connected to Redis semantic cache successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis. Semantic cache will be disabled: {e}")
            
        # In-memory synchronization of cached queries and embeddings for fast vector search
        self.cached_queries = []
        self.cached_embeddings = []
        
        if self.use_cache:
            self._sync_cache_from_redis()

        # Policy Responses (English and Hindi)
        self.policy_responses = {
            "out_of_scope": {
                "en": "I am the UPSDM Assistant. I can answer questions related to UPSDM schemes, registration, training partners, candidates, assessments and industry collaboration.",
                "hi": "मैं यूपीएसडीएम (UPSDM) सहायक हूँ। मैं यूपीएसडीएम योजनाओं, पंजीकरण, प्रशिक्षण भागीदारों, उम्मीदवारों, मूल्यांकन और उद्योग सहयोग से संबंधित प्रश्नों के उत्तर दे सकता हूँ।"
            },
            "fallback": {
                "en": "I couldn't locate this information in the available UPSDM documents.",
                "hi": "मैं उपलब्ध यूपीएसडीएम दस्तावेजों में यह जानकारी नहीं ढूंढ सका।"
            },
            "ambiguous_match": {
                "en": "I detected multiple possible topics in your question. Could you please rephrase or be more specific?",
                "hi": "मुझे आपके प्रश्न में कई संभावित विषय मिले हैं। क्या आप कृपया अपने प्रश्न को फिर से लिख सकते हैं या अधिक विशिष्ट हो सकते हैं?"
            },
            "low_confidence": {
                "en": "I could not confidently identify your question.",
                "hi": "मैं विश्वास के साथ आपके प्रश्न की पहचान नहीं कर सका।"
            }
        }

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
                    test_id = data.get("test_id")
                    
                    if query and response and embedding_list:
                        self.cached_queries.append({
                            "query": query,
                            "response": response,
                            "stage": stage,
                            "key": key,
                            "test_id": test_id
                        })
                        self.cached_embeddings.append(np.array(embedding_list, dtype="float32"))
            
            logger.info(f"Cache sync complete. Total in-memory cache size: {len(self.cached_queries)}")
        except Exception as e:
            logger.error(f"Error syncing semantic cache from Redis: {e}")

    def check_semantic_cache(self, query_embedding: np.ndarray, test_id: str = None) -> tuple[bool, str, str]:
        """Compares query embedding against all cached query embeddings."""
        if not self.use_cache or not self.cached_queries:
            return False, "", ""
            
        threshold = self.config.cache_config.get("similarity_threshold", 0.92)
        
        # Filter candidate indices by matching test_id
        filtered_indices = [
            idx for idx, q in enumerate(self.cached_queries)
            if q.get("test_id") == test_id
        ]
        
        if not filtered_indices:
            return False, "", ""
            
        filtered_embeddings = [self.cached_embeddings[idx] for idx in filtered_indices]
        embeddings_matrix = np.vstack(filtered_embeddings)
        similarities = np.dot(embeddings_matrix, query_embedding.flatten())
        
        max_sub_idx = np.argmax(similarities)
        max_score = similarities[max_sub_idx]
        
        if max_score >= threshold:
            max_idx = filtered_indices[max_sub_idx]
            match = self.cached_queries[max_idx]
            try:
                # Check if the cache key still exists in Redis
                if self.redis_client and not self.redis_client.exists(match["key"]):
                    self.cached_queries.pop(max_idx)
                    self.cached_embeddings.pop(max_idx)
                    logger.info(f"Cache key {match['key']} expired or was deleted from Redis. Evicted from in-memory cache.")
                    return False, "", ""
            except Exception as e:
                logger.warning(f"Error checking cache key existence in Redis: {e}")
                
            logger.info(f"Semantic Cache HIT. Score: {max_score:.4f}. Matched: '{match['query']}'")
            return True, match["response"], match["query"]
            
        return False, "", ""

    def add_to_cache(self, query: str, query_embedding: np.ndarray, response: str, stage_used: str, test_id: str = None):
        """Stores a query, its embedding, and response in Redis and in-memory cache."""
        if not self.use_cache:
            return
            
        try:
            max_entries = self.config.cache_config.get("max_entries", 10000)
            if len(self.cached_queries) >= max_entries:
                evict_item = self.cached_queries.pop(0)
                self.cached_embeddings.pop(0)
                try:
                    self.redis_client.delete(evict_item["key"])
                except Exception:
                    pass
            
            query_hash = hashlib.md5(query.lower().strip().encode('utf-8')).hexdigest()
            if test_id:
                key = f"semantic_cache:item:{test_id}:{query_hash}"
            else:
                key = f"semantic_cache:item:global:{query_hash}"
            ttl = self.config.cache_config.get("ttl_seconds", 3600)
            
            data = {
                "query": query,
                "embedding": query_embedding.flatten().tolist(),
                "response": response,
                "stage_used": stage_used,
                "timestamp": time.time(),
                "test_id": test_id
            }
            
            self.redis_client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
            
            self.cached_queries.append({
                "query": query,
                "response": response,
                "stage": stage_used,
                "key": key,
                "test_id": test_id
            })
            self.cached_embeddings.append(query_embedding.flatten())
            logger.info(f"Added to semantic cache with test_id '{test_id}': '{query}'")
            
        except Exception as e:
            logger.error(f"Error adding to Redis semantic cache: {e}")

    def _get_policy_response(self, policy_type: str, lang: str) -> str:
        """Helper to get clean policy response text based on language."""
        responses = self.policy_responses.get(policy_type, {})
        return responses.get(lang, responses.get("en", ""))

    async def route(self, query: str, history: list[dict] = None, test_id: str = None) -> tuple[str, str, dict]:
        """
        Routes the user query through the redesigned CPU-first pipeline.
        No LLM generation is utilized.
        
        Returns: (stage_used, answer, metadata)
        """
        t_start = time.time()
        metadata = {"cache_status": "MISS"}
        
        # Detect Language
        lang = self.extractor.detect_language(query)
        metadata["detected_language"] = lang
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 0: Multilingual Greeting Detection
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self.greeting_detector.is_greeting(query):
            response = self.greeting_detector.get_greeting_response(query, lang)
            response = self.sanitizer.sanitize(response)
            latency_ms = round((time.time() - t_start) * 1000, 2)
            metadata["stage_latency_ms"] = latency_ms
            
            # Log metrics
            self._write_routing_log(query, "Unknown", "General", 1.0, 1.0, 1.0, 0.0, "greeting", latency_ms, "greeting")
            return "greeting", response, metadata
            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # EMBED QUERY
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        t_embed = time.time()
        q_emb = self.embedder.embed_query(query)
        metadata["embed_latency_ms"] = round((time.time() - t_embed) * 1000, 2)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 1: Scope Detection
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        results = self.faiss_index.search(q_emb, top_k=3)
        metadata["retrieved_chunks"] = results
        
        in_scope, scope_score, scope_reason = self.scope_detector.is_in_scope(query, results)
        metadata["scope_score"] = scope_score
        metadata["scope_reason"] = scope_reason
        
        if not in_scope:
            response = self._get_policy_response("out_of_scope", lang)
            response = self.sanitizer.sanitize(response)
            latency_ms = round((time.time() - t_start) * 1000, 2)
            metadata["stage_latency_ms"] = latency_ms
            
            self._write_routing_log(query, "Unknown", "General", 0.0, 0.0, 0.0, 0.0, "out_of_scope", latency_ms, "out_of_scope")
            return "out_of_scope", response, metadata
            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 2: Semantic Cache
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        is_hit, cached_response, matched_query = self.check_semantic_cache(q_emb, test_id=test_id)
        if is_hit:
            metadata["cache_status"] = "HIT"
            cached_response = self.sanitizer.sanitize(cached_response)
            metadata["cached_query_match"] = matched_query
            latency_ms = round((time.time() - t_start) * 1000, 2)
            metadata["stage_latency_ms"] = latency_ms
            
            self._write_routing_log(query, "Unknown", "General", 1.0, 1.0, 1.0, 0.0, "semantic_cache", latency_ms, "semantic_cache")
            return "semantic_cache", cached_response, metadata
            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 3: Persona & Intent Classification
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        detected_persona, persona_score = self.persona_classifier.classify(query, q_emb)
        metadata["detected_persona"] = detected_persona
        metadata["persona_score"] = persona_score
        
        detected_intent, intent_score = self.intent_classifier.classify(query, q_emb, detected_persona)
        detected_location = self.intent_classifier.detect_location(query)
        metadata["detected_intent"] = detected_intent
        metadata["intent_score"] = intent_score
        if detected_location:
            metadata["detected_location"] = detected_location
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 4: Multi-Signal Template Matcher
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        status, template_answer, match_meta = self.template_matcher.match(
            query, q_emb, detected_persona, detected_intent, lang
        )
        
        if status == "success":
            response = self.sanitizer.sanitize(template_answer)
            self.add_to_cache(query, q_emb, response, "static_lookup", test_id=test_id)
            latency_ms = round((time.time() - t_start) * 1000, 2)
            metadata["stage_latency_ms"] = latency_ms
            metadata.update(match_meta)
            
            self._write_routing_log(
                query, detected_persona, detected_intent, persona_score, intent_score, 
                match_meta["score"], 0.0, "static_lookup", latency_ms, "static_lookup"
            )
            return "static_lookup", response, metadata
            
        elif status == "ambiguous":
            top_ans = match_meta.get("top_answer", "").strip()
            runner_ans = match_meta.get("runner_up_answer", "").strip()
            if lang == "hi":
                top_ans = match_meta.get("top_answer_hi", "").strip() or top_ans
                runner_ans = match_meta.get("runner_up_answer_hi", "").strip() or runner_ans
                
            top_short = top_ans.split('.')[0].strip() if top_ans else ""
            runner_short = runner_ans.split('.')[0].strip() if runner_ans else ""
            
            if top_short and runner_short:
                if lang == "hi":
                    response = f"मुझे आपके प्रश्न से मिलते-जुलते विषय मिले हैं: (1) {top_short} (2) {runner_short}। कृपया स्पष्ट करें कि आप किस विषय के बारे में पूछना चाहते हैं।"
                else:
                    response = f"I found a couple of topics that might match your question: (1) {top_short} (2) {runner_short}. Which one are you asking about?"
            else:
                response = self._get_policy_response("ambiguous_match", lang)
                
            response = self.sanitizer.sanitize(response)
            latency_ms = round((time.time() - t_start) * 1000, 2)
            metadata["stage_latency_ms"] = latency_ms
            metadata["ambiguity_details"] = match_meta
            
            self._write_routing_log(
                query, detected_persona, detected_intent, persona_score, intent_score, 
                match_meta["top_score"], 0.0, "ambiguous_match", latency_ms, "ambiguous_match"
            )
            return "ambiguous_match", response, metadata
            
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 5: FAISS Retrieval & Extractive answer
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Exclude administrative_list chunks from FAISS_DIRECT retrieval candidates
        valid_results = [r for r in results if r.get("content_type") != "administrative_list"]
        ret_level, ret_score, ret_signals = self.extractive_generator.compute_retrieval_confidence(valid_results)
        metadata["confidence_level"] = ret_level
        metadata["confidence_score"] = ret_score
        metadata["confidence_signals"] = ret_signals
        
        if ret_level == "HIGH":
            extractive_answer = self.extractive_generator.generate_extractive_answer(query, q_emb, valid_results)
            if extractive_answer:
                response = self.sanitizer.sanitize(extractive_answer)
                self.add_to_cache(query, q_emb, response, "faiss_direct", test_id=test_id)
                latency_ms = round((time.time() - t_start) * 1000, 2)
                metadata["stage_latency_ms"] = latency_ms
                
                self._write_routing_log(
                    query, detected_persona, detected_intent, persona_score, intent_score, 
                    0.0, ret_score, "faiss_direct", latency_ms, "faiss_direct"
                )
                return "faiss_direct", response, metadata
                
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STAGE 6: Fail-Closed Fallback
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Return fallback answer according to policy
        response = self._get_policy_response("fallback", lang)
        response = self.sanitizer.sanitize(response)
        latency_ms = round((time.time() - t_start) * 1000, 2)
        metadata["stage_latency_ms"] = latency_ms
        
        self._write_routing_log(
            query, detected_persona, detected_intent, persona_score, intent_score, 
            0.0, ret_score, "fallback", latency_ms, "fallback"
        )
        return "fallback", response, metadata

    def _write_routing_log(self, query, persona, intent, p_conf, i_conf, t_score, r_score, decision, latency, ans_type):
        """Appends routing metrics to reports/routing.jsonl file."""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "persona": persona,
            "intent": intent,
            "persona_confidence": round(p_conf, 4),
            "intent_confidence": round(i_conf, 4),
            "template_match_score": round(t_score, 4),
            "retrieved_score": round(r_score, 4),
            "routing_decision": decision,
            "latency_ms": round(latency, 2),
            "final_answer_type": ans_type
        }
        try:
            # Ensure reports folder exists
            reports_dir = Path(self.config.thresholds.get("reports_dir", "reports"))
            if not reports_dir.is_absolute():
                reports_dir = Path(__file__).resolve().parent.parent.parent / reports_dir
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            with open(reports_dir / "routing.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write routing log: {e}")
