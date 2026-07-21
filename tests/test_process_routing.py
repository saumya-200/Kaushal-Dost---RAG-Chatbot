import pytest
from unittest.mock import patch
from src.routing.router import Router


@pytest.mark.asyncio
async def test_process_intent_and_routing():
    with patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        router = Router()
        
        test_queries = [
            ("How do I claim reimbursement for candidate training?", "Process", "Reimbursement claims are processed"),
            ("What is the empanelment process for new training programs?", "Process", "New training programs must be NSQF-compliant")
        ]
        
        for query, expected_intent, expected_snippet in test_queries:
            stage, response, metadata = await router.route(query, test_id=f"test_proc_{expected_intent}")
            
            assert stage == "static_lookup", f"Query '{query}' expected stage 'static_lookup' but got '{stage}'"
            assert metadata.get("detected_intent") == expected_intent, f"Query '{query}' expected intent '{expected_intent}' but got '{metadata.get('detected_intent')}'"
            assert expected_snippet in response, f"Query '{query}' expected response containing '{expected_snippet}' but got '{response}'"
