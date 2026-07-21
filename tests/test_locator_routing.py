import pytest
from unittest.mock import patch
from src.routing.router import Router


@pytest.mark.asyncio
async def test_locator_intent_and_routing():
    with patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        router = Router()
        
        test_queries = [
            ("Where can I find the list of training centers in Lucknow?", "Lucknow"),
            ("List of training centers in Kanpur", "Kanpur"),
            ("Find skill development training centers near Varanasi", "Varanasi"),
            ("Where is the training center in Agra?", "Agra"),
            ("Search training centres in Prayagraj", "Prayagraj")
        ]
        
        for query, expected_location in test_queries:
            stage, response, metadata = await router.route(query, test_id=f"test_loc_{expected_location}")
            
            assert stage == "static_lookup", f"Query '{query}' expected stage 'static_lookup' but got '{stage}'"
            assert metadata.get("detected_intent") == "Locator", f"Query '{query}' expected intent 'Locator' but got '{metadata.get('detected_intent')}'"
            assert metadata.get("detected_location") == expected_location, f"Query '{query}' expected location '{expected_location}' but got '{metadata.get('detected_location')}'"
            assert "Search Centers" in response or "visit upsdm.gov.in" in response
