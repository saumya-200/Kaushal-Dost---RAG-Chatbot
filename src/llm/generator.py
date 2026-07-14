import logging
import httpx
import time
from src.config import load_config

logger = logging.getLogger(__name__)

class LLMGenerator:
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.config = load_config()
        self.ollama_url = f"{ollama_host}/api/chat"
        self.primary_model = self.config.llm_config.get("primary_model", "qwen3:4b")
        self.fallback_model = self.config.llm_config.get("fallback_model", "qwen3:1.7b")
        self.timeout = float(self.config.llm_config.get("timeout_seconds", 180))

    def _format_context(self, chunks: list[dict]) -> str:
        """Formats retrieved FAISS chunks into a single context string."""
        max_chunks = self.config.response_config.get("max_context_chunks", 3)
        selected_chunks = chunks[:max_chunks]
        
        context_parts = []
        for chunk in selected_chunks:
            title = chunk.get("title", "Document")
            text = chunk.get("text", "")
            context_parts.append(f"Source [{title}]: {text}")
            
        return "\n\n".join(context_parts)

    def generate_answer(self, query: str, chunks: list[dict], history: list[dict] = None, use_fallback_model: bool = False) -> str:
        """
        Generates a grounded response based on context chunks and conversation history.
        history format: list of dicts with keys 'query' and 'answer'.
        """
        # Format the context chunks
        context_text = self._format_context(chunks)
        
        # Build the system prompt
        system_prompt = self.config.system_prompt
        
        # Build prompt body
        prompt = (
            f"Context information is below.\n"
            f"---------------------\n"
            f"{context_text}\n"
            f"---------------------\n"
            f"Given the context information and not prior knowledge, answer the query.\n"
            f"Query: {query}\n"
            f"Answer:"
        )
        
        # Compile messages array for chat completion
        messages = [{"role": "system", "content": system_prompt}]
        
        # Append history if present
        if history:
            max_turns = self.config.response_config.get("max_history_turns", 4)
            recent_history = history[-max_turns:]
            for turn in recent_history:
                messages.append({"role": "user", "content": turn.get("query", "")})
                messages.append({"role": "assistant", "content": turn.get("answer", "")})
                
        # Append current user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Select model
        model = self.fallback_model if use_fallback_model else self.primary_model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for factual consistency
                "num_predict": 2048  # Large enough token budget to support reasoning + answer
            }
        }
        
        t0 = time.time()
        try:
            logger.info(f"Sending request to Ollama model '{model}' with timeout {self.timeout}s...")
            r = httpx.post(self.ollama_url, json=payload, timeout=self.timeout)
            
            if r.status_code == 200:
                result = r.json()
                answer = result.get("message", {}).get("content", "").strip()
                if answer:
                    latency = time.time() - t0
                    logger.info(f"LLM generation successful in {latency:.2f} seconds.")
                    return answer
                else:
                    logger.warning("Ollama returned an empty response content.")
            else:
                logger.error(f"Ollama returned error status: {r.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to query Ollama model '{model}': {e}")
            
        # Fallback handling
        if not use_fallback_model:
            # If primary failed, we can optionally try the fallback model (qwen3:1.7b)
            logger.info("Attempting backup generation using fallback model...")
            return self.generate_answer(query, chunks, history, use_fallback_model=True)
            
        # Hard fallback response based on the top context chunk
        if chunks:
            top_chunk = chunks[0]
            return f"[Draft RAG Response] Based on the official details, {top_chunk.get('text', '')[:180]}..."
            
        return "I'm sorry, I couldn't process your request at this time."
