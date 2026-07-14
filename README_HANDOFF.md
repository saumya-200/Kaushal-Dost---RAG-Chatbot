# Technical Handover Guide — UPSDM RAG Chatbot Brain

This repository contains the optimized, containerized RAG-based Chatbot Brain for the Uttar Pradesh Skill Development Mission (UPSDM). It replaces the legacy SQL-based keyword overlap matcher with a modern, confidence-routed retrieval-augmented generation (RAG) pipeline.

---

## 🏗️ System Architecture Overview

The system runs as a group of containerized microservices:

1. **FastAPI Web Service (`rag-chatbot-brain`)**: Exposes the chatbot endpoint and orchestrates multi-stage confidence routing.
2. **FAISS Vector Index**: Performs high-performance similarity search over crawled UPSDM circulars, FAQs, and notices.
3. **Redis Cache (`upsdm-chatbot-redis`)**: Performs semantic vector caching to instantly answer matching queries without querying the LLM.
4. **Ollama LLM Engine (`upsdm-chatbot-ollama`)**: Serves locally hosted models (`qwen3:4b` and `qwen3:1.7b`) for answer synthesis.

### The Multi-Stage Routing Pipeline
1. **Greeting Router**: Greeting expressions (English, Hindi, Hinglish) are caught instantly and responded to using templates (`<1ms`).
2. **Semantic Cache Check**: If a query's E5 embedding matches a cached query's embedding with `>=0.92` similarity, it returns the cached response instantly (`<25ms`).
3. **FAISS Similarity Search**:
   - **High Relevance (Score >= 0.90)**: Returns the matching FAISS document chunk text directly, saving CPU/GPU cycles.
   - **Medium Relevance (0.65 <= Score < 0.90)**: Synthesizes a factual answer using `qwen3:4b` based strictly on retrieved chunks.
   - **Low Relevance (Score < 0.65)**: Returns a clean language-specific fallback message pointing users to contact the UPSDM helpline.

---

## 🚀 Quick Start Deployment

Deploy the entire stack (Redis, Ollama, automatic model setup, and the FastAPI application) with a single command:

```bash
docker-compose up --build -d
```

### Automatic Model Download
On container startup, the `upsdm-chatbot-model-setup` helper container automatically polls Ollama and pulls both `qwen3:4b` (primary model) and `qwen3:1.7b` (fallback model). No manual download commands are required.

---

## 🔌 API Contract Reference

### 1. Chat Endpoint (`POST /chat`)
- **Request Body Format (`application/json`)**:
  ```json
  {
    "message": "What is the helpline number of UPSDM?",
    "history": [
      { "query": "What is UPSDM?", "answer": "Uttar Pradesh Skill Development Mission..." }
    ]
  }
  ```
- **Response Body Format (`application/json`)**:
  ```json
  {
    "reply": "The official helpline number for UPSDM is 0522-4944200.",
    "stage": "llm",
    "source_ids": ["www.upsdm.gov.in/Home/SkillMitraIndex__chunk_000"],
    "latency_ms": 754.2
  }
  ```

### 2. Health Endpoint (`GET /health`)
- **Response Format (`application/json`)**:
  ```json
  {
    "status": "healthy",
    "primary_model": "qwen3:4b",
    "fallback_model": "qwen3:1.7b",
    "redis_cache": "connected"
  }
  ```

---

## 🛠️ C#.NET Web Integration
The `.NET` application needs to switch from SQL keyword matching to querying our FastAPI service. 

Refer to [integration_notes.md](file:///Users/ommakhija/Downloads/kaushal%20dost/Kaushal-Dost---RAG-Chatbot/integration_notes.md) for the exact step-by-step code modifications and class schemas required in:
- `ChatbotService.cs` (to implement the async HTTP Post and SQL failover)
- `ChatController.cs` (to invoke the async query)

---

## 🧪 Verification & Testing Commands

Verify the codebase functionality locally:

1. **Run Unit Tests (17 tests passing)**:
   ```bash
   .venv/bin/pytest tests/
   ```
2. **Run LLM Concurrency and Queue Limit Verification**:
   ```bash
   .venv/bin/python scripts/load_test.py
   ```
3. **Run C# Client-Side Fallback Simulation**:
   ```bash
   .venv/bin/python scripts/test_integration_fallback.py
   ```
