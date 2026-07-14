import pytest
import numpy as np
import redis
from unittest.mock import MagicMock, patch

from src.routing.router import Router
from src.config import load_config

@pytest.fixture
def redis_client():
    """Connects to local Redis, clears it, and yields client."""
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    try:
        client.ping()
        client.flushdb()
        yield client
        client.flushdb()
    except redis.ConnectionError:
        pytest.skip("Local Redis container is not running or accessible on port 6379.")

@pytest.fixture
def router(redis_client):
    return Router()

def test_greeting_detection(router):
    # Test English greetings
    assert router.is_greeting("hello")
    assert router.is_greeting("Hello!")
    assert router.is_greeting("hey there")
    
    # Test Hindi greetings
    assert router.is_greeting("नमस्ते")
    assert router.is_greeting("namaste")
    assert router.is_greeting("राम राम")
    
    # Test non-greetings
    assert not router.is_greeting("what is upsdm")
    assert not router.is_greeting("how to register for courses")

def test_greeting_routing(router):
    stage, response, meta = router.route("hello")
    assert stage == "greeting"
    assert "Kaushal Dost" in response
    assert meta["detected_language"] == "en"
    
    stage_hi, response_hi, meta_hi = router.route("नमस्ते")
    assert stage_hi == "greeting"
    assert "नमस्ते" in response_hi or "सहायक" in response_hi
    assert meta_hi["detected_language"] == "hi"

def test_fallback_routing(router):
    # Mock FAISS to return no results
    with patch.object(router.faiss_index, 'search', return_value=[]):
        stage, response, meta = router.route("random gibberish queries that return nothing")
        assert stage == "fallback"
        assert "helpline" in response
        assert meta["detected_language"] == "en"

def test_semantic_cache_flow(router, redis_client):
    # Clear local memory cache cache list
    router.cached_queries = []
    router.cached_embeddings = []
    
    query = "What is the training eligibility?"
    q_emb = router.embedder.embed_query(query)
    response = "Candidates aged 14 to 35 are eligible."
    
    # Test Cache Miss initially
    is_hit, cached, matched = router.check_semantic_cache(q_emb)
    assert not is_hit
    
    # Add to cache
    router.add_to_cache(query, q_emb, response, "faiss_direct")
    
    # Test Cache Hit on exact match
    is_hit, cached, matched = router.check_semantic_cache(q_emb)
    assert is_hit
    assert cached == response
    assert matched == query
    
    # Test Cache Hit on paraphrase (semantic cache)
    paraphrase = "What is eligibility for training?"
    p_emb = router.embedder.embed_query(paraphrase)
    is_hit_p, cached_p, matched_p = router.check_semantic_cache(p_emb)
    # They should be highly semantically similar (e5-small cosine similarity > 0.92)
    assert is_hit_p
    assert cached_p == response
    assert matched_p == query

def test_confidence_threshold_routing(router):
    # Mock FAISS search to return a mock chunk with high score
    high_score_chunk = {
        "chunk_id": "test_chunk_001",
        "source_url": "https://www.upsdm.gov.in/Home/Test",
        "source_id": "www.upsdm.gov.in/Home/Test",
        "text": "Direct direct direct direct direct direct.",
        "score": 0.95
    }
    
    # Clear memory cache
    router.cached_queries = []
    router.cached_embeddings = []
    
    with patch.object(router.faiss_index, 'search', return_value=[high_score_chunk]):
        stage, response, meta = router.route("where is the direct chunk")
        assert stage == "faiss_direct"
        assert response == "Direct direct direct direct direct direct."
        assert meta["top_score"] == 0.95

    # Mock FAISS search to return medium score
    med_score_chunk = {
        "chunk_id": "test_chunk_002",
        "source_url": "https://www.upsdm.gov.in/Home/Test",
        "source_id": "www.upsdm.gov.in/Home/Test",
        "text": "Requires LLM formatting and synthesis.",
        "score": 0.78
    }
    
    with patch.object(router.faiss_index, 'search', return_value=[med_score_chunk]):
        # Mock LLM API call to avoid making a real external request in tests
        with patch.object(router, '_generate_llm_response', return_value="Synthesized LLM Response"):
            stage, response, meta = router.route("synthesis prompt details")
            assert stage == "llm"
            assert response == "Synthesized LLM Response"
            assert meta["top_score"] == 0.78

    # Mock FAISS search to return low score
    low_score_chunk = {
        "chunk_id": "test_chunk_003",
        "source_url": "https://www.upsdm.gov.in/Home/Test",
        "source_id": "www.upsdm.gov.in/Home/Test",
        "text": "Very low relevance.",
        "score": 0.45
    }
    
    with patch.object(router.faiss_index, 'search', return_value=[low_score_chunk]):
        stage, response, meta = router.route("completely irrelevant queries")
        assert stage == "fallback"
        assert "helpline" in response
