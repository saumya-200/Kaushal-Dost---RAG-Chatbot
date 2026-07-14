# Kaushal Dost RAG Chatbot — Scope

## What we are building
A multilingual RAG (Retrieval-Augmented Generation) pipeline that replaces the
keyword-intersection matcher in ChatbotService.cs with semantic search + local
LLM generation, while preserving the exact HTTP contract the .NET front-end
already calls.

## What we are NOT building
- No UI/UX changes to the chat widget
- No changes to ChatController.cs beyond one line (HttpClient redirect)
- No new database tables or stored procedures
- No cloud API calls (everything runs locally via Ollama)
- No production deployment (this is a handoff package)

## Technology stack
- Python 3.11+ (FastAPI, sentence-transformers, FAISS, Scrapy)
- Ollama (qwen3:4b primary, qwen3:1.7b fallback)
- Redis (semantic cache, via Docker)
- SQLite (ingestion state tracking)
- Docker Compose (packaging for handoff)

## Languages supported
- English
- Devanagari Hindi (हिन्दी)
- Romanized Hindi (transliterated)
- Hinglish (mixed English+Hindi)

## Verified tool versions
- Python: 3.13.7
- Docker: 29.6.1
- Ollama: 0.31.2
- Git: 2.50.1
- qwen3:4b: already pulled (2.5 GB)
