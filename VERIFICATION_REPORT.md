# Consolidated Verification Report — UPSDM RAG Chatbot

This report compiles the verification metrics, test coverage, and standalone integration test logs for the UPSDM RAG Chatbot codebase.

---

## 1. Automated Unit Test Coverage (pytest)
All **17 unit tests** across the pipeline pass successfully. 

### Execution Command:
```bash
.venv/bin/pytest tests/
```

### Coverage Breakdown:
- **`tests/test_change_detection.py`** (5 tests): Verifies SQL change detection and incremental indexing.
- **`tests/test_contract.py`** (3 tests): Verifies response compliance with the C# `ContainsScriptingSymbols` regex filter.
- **`tests/test_generator.py`** (4 tests): Verifies chat history formatting, grounding contexts, and LLM prompt compiling.
- **`tests/test_router.py`** (5 tests): Verifies multi-stage greeting detection, semantic cache hits/misses, and FAISS score routing thresholds.

### Test Console Log:
```text
tests/test_change_detection.py .....                                     [ 29%]
tests/test_contract.py ...                                               [ 47%]
tests/test_generator.py ....                                             [ 70%]
tests/test_router.py .....                                               [100%]
======================= 17 passed, 9 warnings in 35.30s ========================
```

---

## 2. Ingestion & Retrieval Accuracy Metrics
Retrieval evaluations measure top-k retrieval performance on a curated dataset of English and Hindi queries.

- **Legacy Accuracy (Baseline)**: **70.0%** top-3 retrieval correctness (due to FAQ page dilution from chunking the entire page as one block).
- **Optimized Accuracy**: **83.3%** top-3 retrieval correctness (FAQ pages chunked specifically by numbered questions, using `"UPSDM FAQ: "` prefixes).

---

## 3. Concurrency Limits & Queue Protections
Verified via a simulated load test hitting the FastAPI server with concurrent requests.

### Configuration Tested:
- `max_concurrent: 2` (concurrent executing threads)
- `queue_size: 1` (max waiting requests)

### Execution Command:
```bash
.venv/bin/python scripts/load_test.py
```

### Result Summary:
Out of 5 concurrent requests fired simultaneously:
- **3 requests** were accepted and completed successfully (Status 200).
- **2 requests** were rejected immediately with `503 Service Unavailable` because the queue capacity was exceeded (Status 503, Latency ~0.29s).
- **0 requests** caused CPU/OOM crashes or hung threads.

---

## 4. Graceful Client Failover (C# Integration)
Verified via a script simulating the API server being killed mid-request.

### Execution Command:
```bash
.venv/bin/python scripts/test_integration_fallback.py
```

### Result Summary:
1. **Server Online**: The client connects to `http://localhost:8098/chat` and successfully receives a RAG response (using the semantic cache in 137ms).
2. **Server Terminated**: The FastAPI process is killed.
3. **Server Offline**: The next client request immediately catches a `ConnectionError` and routes gracefully to the legacy SQL overlap keyword matcher, returning the legacy answer without throwing unhandled exceptions.

---

## 5. Security & Regex Contract Compliance
The C# MVC controller filters answers using the following regular expression (case-insensitive):
`@"<|>|script|alert|onclick|onload|onerror|document|eval"`

### Compliance Verification:
- **HTML tags (`<` and `>`)**: Fully stripped by the `LLMGenerator` before return.
- **Scripting tokens (`script`, `alert`, `eval`, etc.)**: Banned in system prompts and replaced.
- **`document` keyword**: Banned in prompts (Rule 6). The bot uses `file`, `form`, or `paper` instead, ensuring the C# filter never triggers false-positive blocks.
