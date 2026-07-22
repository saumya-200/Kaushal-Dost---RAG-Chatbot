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
    assert router.greeting_detector.is_greeting("hello")
    assert router.greeting_detector.is_greeting("Hello!")
    assert router.greeting_detector.is_greeting("hey there")
    
    # Test Hindi greetings
    assert router.greeting_detector.is_greeting("नमस्ते")
    assert router.greeting_detector.is_greeting("namaste")
    assert router.greeting_detector.is_greeting("राम राम")
    
    # Test non-greetings
    assert not router.greeting_detector.is_greeting("what is upsdm")
    assert not router.greeting_detector.is_greeting("how to register for courses")

@pytest.mark.asyncio
async def test_greeting_routing(router):
    stage, response, meta = await router.route("hello")
    assert stage == "greeting"
    assert "Kaushal Dost" in response or "Hello" in response or "Hi" in response
    assert meta["detected_language"] == "en"
    
    stage_hi, response_hi, meta_hi = await router.route("नमस्ते")
    assert stage_hi == "greeting"
    assert "नमस्ते" in response_hi or "सहायक" in response_hi
    assert meta_hi["detected_language"] == "hi"

@pytest.mark.asyncio
async def test_fallback_routing(router):
    # Force in-scope, but return empty FAISS results to trigger fallback stage
    with patch.object(router.scope_detector, 'is_in_scope', return_value=(True, 0.8, "in_scope")):
        with patch.object(router.faiss_index, 'search', return_value=[]):
            stage, response, meta = await router.route("random query that is forced in scope but yields no documents")
            assert stage == "fallback"
            assert "locate" in response or "documents" in response
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

@pytest.mark.asyncio
async def test_confidence_threshold_routing(router):
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
    
    # Force in-scope and template matcher bypass
    with patch.object(router.scope_detector, 'is_in_scope', return_value=(True, 0.8, "in_scope")):
        with patch.object(router.template_matcher, 'match', return_value=("low_confidence", "", {})):
            with patch.object(router.faiss_index, 'search', return_value=[high_score_chunk]):
                stage, response, meta = await router.route("where is the direct chunk")
                assert stage == "faiss_direct"
                assert "Direct direct direct direct direct direct." in response
                assert meta["confidence_level"] == "HIGH"

    # Mock FAISS search to return low score
    low_score_chunk = {
        "chunk_id": "test_chunk_003",
        "source_url": "https://www.upsdm.gov.in/Home/Test",
        "source_id": "www.upsdm.gov.in/Home/Test",
        "text": "Very low relevance.",
        "score": 0.45
    }
    
    with patch.object(router.scope_detector, 'is_in_scope', return_value=(True, 0.8, "in_scope")):
        with patch.object(router.template_matcher, 'match', return_value=("low_confidence", "", {})):
            with patch.object(router.faiss_index, 'search', return_value=[low_score_chunk]):
                stage, response, meta = await router.route("completely irrelevant queries")
                assert stage == "fallback"
                assert "locate" in response


@pytest.mark.asyncio
async def test_regression_kaushal_drishti_definition(router):
    if router.use_cache:
        router.redis_client.flushdb()
    router.cached_queries = []
    router.cached_embeddings = []
    stage, response, meta = await router.route("What is Kaushal Drishti?")
    assert stage == "faiss_direct"
    assert "portal" in response.lower() or "candidate" in response.lower() or "registration" in response.lower() or "tracking" in response.lower()
    assert "table of contents" not in response.lower()


@pytest.mark.asyncio
async def test_regression_pmkvy_eligibility_criteria(router):
    if router.use_cache:
        router.redis_client.flushdb()
    router.cached_queries = []
    router.cached_embeddings = []
    stage, response, meta = await router.route("What are the eligibility criteria for the PMKVY scheme?")
    assert stage == "faiss_direct"
    
    expected_terms = ["14-35", "nsqf", "30%", "women", "minorities"]
    matches = sum(1 for term in expected_terms if term in response.lower())
    assert matches >= 2
    assert "steering committee" not in response.lower()
    assert "approval" not in response.lower()


@pytest.mark.asyncio
async def test_flexi_mou_template_matching(router):
    stage, response, meta = await router.route("What is the Flexi MoU scheme?")
    assert stage == "static_lookup"
    assert "flexible partnership agreements" in response.lower() or "flexi mou is a scheme" in response.lower()
    assert "companies can collaborate" not in response.lower()


@pytest.mark.asyncio
async def test_curriculum_customization_template_matching(router):
    stage, response, meta = await router.route("Can we customize the training curriculum for our industry needs?")
    assert stage == "static_lookup"
    assert "sector skill councils" in response.lower() or "nsqf standards" in response.lower()

