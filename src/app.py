import time
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.routing.router import Router

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("chatbot_api")

app = FastAPI(title="UPSDM Chatbot RAG Service")

# Initialize global router instance
router = Router()

# Pydantic Schemas
class ChatMessage(BaseModel):
    query: str
    answer: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    reply: str
    stage: str
    source_ids: List[str]
    latency_ms: float
    # Extended routing metadata (optional — backward compatible with C# client)
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None
    routing_details: Optional[Dict[str, Any]] = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    t0 = time.time()
    
    # Clean message input
    query = request.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
    
    # Format history back to list[dict]
    history_dicts = []
    if request.history:
        for turn in request.history:
            history_dicts.append({
                "query": turn.query,
                "answer": turn.answer
            })
            
    try:
        # Route query through multi-stage pipeline
        stage, answer, metadata = await router.route(query, history=history_dicts)
        
        # Calculate latency
        latency_ms = (time.time() - t0) * 1000
        
        # Gather retrieved chunk IDs
        source_ids = []
        retrieved_chunks = metadata.get("retrieved_chunks", [])
        if retrieved_chunks:
            source_ids = [chunk.get("chunk_id", "unknown") for chunk in retrieved_chunks]
        
        # Build routing details for observability
        routing_details = {
            "detected_language": metadata.get("detected_language"),
            "stage_latency_ms": metadata.get("stage_latency_ms"),
            "embed_latency_ms": metadata.get("embed_latency_ms"),
        }
        
        # Add stage-specific details
        if "static_intent" in metadata:
            routing_details["static_intent"] = metadata["static_intent"]
        if "scope_score" in metadata:
            routing_details["scope_score"] = metadata["scope_score"]
            routing_details["scope_reason"] = metadata.get("scope_reason")
        if "cached_query_match" in metadata:
            routing_details["cached_query_match"] = metadata["cached_query_match"]
        if "confidence_signals" in metadata:
            routing_details["confidence_signals"] = metadata["confidence_signals"]
        if "llm_latency_ms" in metadata:
            routing_details["llm_latency_ms"] = metadata["llm_latency_ms"]
            
        # Structured JSON logging per response
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "stage_used": stage,
            "source_ids": source_ids,
            "latency_ms": round(latency_ms, 2),
            "confidence_level": metadata.get("confidence_level"),
            "confidence_score": metadata.get("confidence_score"),
        }
        logger.info(f"RESPONSE_METRICS: {json.dumps(log_entry)}")
        
        return ChatResponse(
            reply=answer,
            stage=stage,
            source_ids=source_ids,
            latency_ms=round(latency_ms, 2),
            confidence_score=metadata.get("confidence_score"),
            confidence_level=metadata.get("confidence_level"),
            routing_details=routing_details
        )
        
    except HTTPException as he:
        # Re-raise standard HTTPExceptions (like Concurrency Queue limits)
        raise he
    except Exception as e:
        logger.error(f"Error handling query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing the chat request.")

@app.get("/health")
def health_check():
    return {"status": "healthy", "model": router.generator.primary_model}
