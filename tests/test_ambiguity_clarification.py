import pytest
from unittest.mock import patch
from src.routing.router import Router
from tests.test_contract import contains_scripting_symbols


@pytest.mark.asyncio
async def test_ambiguity_clarification_response_options():
    with patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        router = Router()
        
        match_meta = {
            "top_match_intent": "Enroll",
            "runner_up_intent": "Training Center",
            "score_diff": 0.01,
            "top_score": 0.75,
            "runner_up_score": 0.74,
            "top_answer": "To register for UPSDM skill development courses, visit upsdm.gov.in.",
            "runner_up_answer": "To find training centers near you, visit upsdm.gov.in."
        }
        
        with patch.object(router.template_matcher, "match", return_value=("ambiguous", "", match_meta)):
            stage, response, metadata = await router.route("enroll in training centers", test_id="test_ambiguity_options")
            
            assert stage == "ambiguous_match"
            assert "(1)" in response and "(2)" in response, f"Expected options format '(1) ... (2) ...' in response: {response}"
            assert "To register for UPSDM skill development courses" in response
            assert "To find training centers near you" in response
            assert not contains_scripting_symbols(response), f"Ambiguity response failed C# security regex: {response}"
            
            generic_fallback = "I detected multiple possible topics in your question"
            assert generic_fallback not in response, "Response should contain specific candidate options instead of generic refusal"
