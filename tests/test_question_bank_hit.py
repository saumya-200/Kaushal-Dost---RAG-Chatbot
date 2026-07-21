import pytest
import redis
import uuid
import httpx

@pytest.fixture(scope="function", autouse=True)
def clear_cache():
    r = redis.Redis(host="localhost", port=6379)
    try:
        r.flushall()
    except redis.ConnectionError:
        pass
    yield
    try:
        r.flushall()
    except redis.ConnectionError:
        pass

@pytest.fixture
def test_id():
    return f"test-run-{uuid.uuid4()}"

@pytest.mark.asyncio
async def test_intentional_cache_hit_flow(test_id):
    query_a = "What is the helpline number for UPSDM?"
    query_b = "What is the helpline number for UPSDM?" # Exact match
    paraphrase = "Is there a helpline contact number for UPSDM?" # Semantic match
    
    async with httpx.AsyncClient() as client:
        # 1. Warm cache with query A (should be a MISS)
        resp_a = await client.post(
            "http://localhost:8000/chat",
            json={"message": query_a, "history": [], "test_id": test_id},
            timeout=100.0
        )
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a.get("cache_status") == "MISS", "Expected initial query to be a MISS"
        
        # 2. Query B with the SAME test_id (should be a HIT)
        resp_b = await client.post(
            "http://localhost:8000/chat",
            json={"message": query_b, "history": [], "test_id": test_id},
            timeout=100.0
        )
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b.get("cache_status") == "HIT", "Expected duplicate query to be a HIT"
        assert data_b.get("stage") == "semantic_cache"
        
        # 3. Paraphrase with the SAME test_id (should be a HIT due to semantic cache similarity)
        resp_p = await client.post(
            "http://localhost:8000/chat",
            json={"message": paraphrase, "history": [], "test_id": test_id},
            timeout=100.0
        )
        assert resp_p.status_code == 200
        data_p = resp_p.json()
        assert data_p.get("cache_status") == "HIT", "Expected paraphrase query to be a HIT"
        assert data_p.get("stage") == "semantic_cache"
        
        # 4. Same paraphrase query with a DIFFERENT test_id (should be a MISS due to namespace isolation)
        other_test_id = f"test-run-{uuid.uuid4()}"
        resp_p_diff = await client.post(
            "http://localhost:8000/chat",
            json={"message": paraphrase, "history": [], "test_id": other_test_id},
            timeout=100.0
        )
        assert resp_p_diff.status_code == 200
        data_p_diff = resp_p_diff.json()
        assert data_p_diff.get("cache_status") == "MISS", "Expected paraphrase with different test_id to be a MISS"
