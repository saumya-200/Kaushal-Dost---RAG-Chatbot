import pytest
import redis
import uuid
import httpx
from scripts.test_question_bank import QUESTION_BANK

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

# Flatten the QUESTION_BANK dictionary to parameterize individual test cases
all_queries = []
for category, questions in QUESTION_BANK.items():
    for idx, item in enumerate(questions, 1):
        all_queries.append((category, idx, item["q"], item["expected"]))

@pytest.mark.asyncio
@pytest.mark.parametrize("category, idx, question, expected", all_queries)
async def test_miss_path_query(test_id, category, idx, question, expected):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/chat",
            json={"message": question, "history": [], "test_id": test_id},
            timeout=100.0
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify cache status is strictly "MISS" due to test run namespacing
        assert data.get("cache_status") == "MISS", f"Expected cache MISS for '{question}' but got HIT!"
