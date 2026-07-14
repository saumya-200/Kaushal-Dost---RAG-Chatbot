import pytest
from unittest.mock import patch, MagicMock
from src.llm.generator import LLMGenerator

def test_format_context():
    generator = LLMGenerator()
    chunks = [
        {"title": "Doc1", "text": "Content of Doc 1"},
        {"title": "Doc2", "text": "Content of Doc 2"},
        {"title": "Doc3", "text": "Content of Doc 3"},
        {"title": "Doc4", "text": "Content of Doc 4"}
    ]
    
    formatted = generator._format_context(chunks)
    
    # Assert at most 3 context chunks are selected
    assert "Doc1" in formatted
    assert "Doc2" in formatted
    assert "Doc3" in formatted
    assert "Doc4" not in formatted
    assert "Content of Doc 1" in formatted
    assert "Content of Doc 3" in formatted

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_answer_success(mock_post):
    # Mock successful response from Ollama
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": "This is the generated response from Qwen."
        }
    }
    # An async mock for the awaitable return value of post
    async def mock_post_coro(*args, **kwargs):
        return mock_response
    mock_post.side_effect = mock_post_coro

    generator = LLMGenerator()
    chunks = [{"title": "Doc1", "text": "Some context info."}]
    
    response = await generator.generate_answer("What is the registration process?", chunks)
    
    assert response == "This is the generated response from Qwen."
    mock_post.assert_called_once()
    
    # Check payload parameters
    called_args, called_kwargs = mock_post.call_args
    payload = called_kwargs["json"]
    assert payload["model"] == generator.primary_model
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.1
    assert len(payload["messages"]) == 2  # system + user prompt

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_answer_with_history(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Follow-up answer."}
    }
    async def mock_post_coro(*args, **kwargs):
        return mock_response
    mock_post.side_effect = mock_post_coro

    generator = LLMGenerator()
    chunks = [{"title": "Doc1", "text": "Some context info."}]
    history = [
        {"query": "Hello", "answer": "Hello! How can I help you?"},
        {"query": "What is UPSDM?", "answer": "UPSDM is Uttar Pradesh Skill Development Mission."}
    ]
    
    response = await generator.generate_answer("How to apply?", chunks, history=history)
    
    assert response == "Follow-up answer."
    
    called_args, called_kwargs = mock_post.call_args
    payload = called_kwargs["json"]
    messages = payload["messages"]
    
    # Messages should be: System Prompt, 2 History Turns (4 messages), and current User prompt
    assert len(messages) == 6
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hello"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["content"] == "Hello! How can I help you?"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "What is UPSDM?"
    assert messages[4]["role"] == "assistant"
    assert messages[4]["content"] == "UPSDM is Uttar Pradesh Skill Development Mission."
    assert messages[5]["role"] == "user"
    assert "How to apply?" in messages[5]["content"]

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_answer_failure_fallback(mock_post):
    # Mock Ollama post failing
    async def mock_post_coro(*args, **kwargs):
        raise Exception("Connection refused")
    mock_post.side_effect = mock_post_coro

    generator = LLMGenerator()
    chunks = [
        {"title": "Doc1", "text": "This is primary context for UPSDM registration."},
        {"title": "Doc2", "text": "Secondary context."}
    ]
    
    # It should fail primary call, then fail fallback model call, and then return hard fallback response
    response = await generator.generate_answer("What is the process?", chunks)
    
    assert "[Draft RAG Response]" in response
    assert "This is primary context for UPSDM registration." in response
    # It should have attempted twice (primary model, then fallback model)
    assert mock_post.call_count == 2
