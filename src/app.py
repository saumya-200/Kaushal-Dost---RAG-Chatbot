import time
import json
import logging
from typing import Optional, List
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
            
        # Structured JSON logging per response
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "stage_used": stage,
            "source_ids": source_ids,
            "latency_ms": round(latency_ms, 2)
        }
        logger.info(f"RESPONSE_METRICS: {json.dumps(log_entry)}")
        
        return ChatResponse(
            reply=answer,
            stage=stage,
            source_ids=source_ids,
            latency_ms=round(latency_ms, 2)
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
