# Kaushal Dost — RAG Chatbot Testing Guide

> Step-by-step instructions to verify every layer of the UPSDM RAG chatbot,
> from environment setup through unit tests, integration tests, benchmark
> runs, and manual exploratory testing.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Start the Server](#3-start-the-server)
4. [Health Check](#4-health-check)
5. [Unit Tests (Offline — No Server Needed)](#5-unit-tests-offline--no-server-needed)
6. [Integration Tests (Server Required)](#6-integration-tests-server-required)
7. [Benchmark Testing (26-Question Bank)](#7-benchmark-testing-26-question-bank)
8. [Retrieval Quality Evaluation](#8-retrieval-quality-evaluation)
9. [Interactive Manual Testing](#9-interactive-manual-testing)
10. [Load / Stress Testing](#10-load--stress-testing)
11. [Benchmark Comparison & Reports](#11-benchmark-comparison--reports)
12. [Rebuilding After Code Changes](#12-rebuilding-after-code-changes)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Check Command |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Docker | 20+ | `docker --version` |
| Docker Compose | v2+ | `docker compose version` |
| pip | latest | `pip --version` |

Make sure **Docker Desktop** is running before proceeding.

---

## 2. Environment Setup

### 2.1 Create & Activate Virtual Environment

```bash
cd Kaushal-Dost---RAG-Chatbot
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Verify Key Packages Installed

```bash
python -c "import fastapi, uvicorn, scrapy, faiss, sentence_transformers; print('All OK')"
```

If this prints `All OK`, your environment is ready.

---

## 3. Start the Server

The chatbot runs as a Docker Compose stack with three services:

| Service | Container Name | Purpose |
|---|---|---|
| `redis` | `upsdm-chatbot-redis` | Semantic response caching |
| `ollama` | `upsdm-chatbot-ollama` | Local LLM inference (qwen3) |
| `rag-chatbot-brain` | `upsdm-chatbot-brain` | FastAPI RAG chatbot (port 8000) |

### 3.1 First-Time Start (Build + Pull Models)

```bash
docker compose up --build -d
```

> **Note:** On first run, the `model-setup` container will automatically pull
> `qwen3:0.6b` and `qwen3:1.7b` into Ollama. This can take 5–10 minutes
> depending on your internet speed. Monitor with:
>
> ```bash
> docker logs upsdm-chatbot-model-setup -f
> ```

### 3.2 Verify All Containers Are Running

```bash
docker compose ps
```

Expected output — all three services should show `running`:

```
NAME                    STATUS
upsdm-chatbot-redis     running
upsdm-chatbot-ollama    running
upsdm-chatbot-brain     running
```

### 3.3 View Server Logs (Live)

```bash
docker logs upsdm-chatbot-brain -f
```

Look for `Uvicorn running on http://0.0.0.0:8000` to confirm the server is ready.

---

## 4. Health Check

### 4.1 Via curl

```bash
curl http://localhost:8000/health
```

**Expected response:**

```json
{"status": "healthy", "model": "cpu-extractive-pipeline"}
```

### 4.2 Via Python

```bash
venv/bin/python -c "import httpx; print(httpx.get('http://localhost:8000/health').json())"
```

### 4.3 Quick Smoke Test (Single Query)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is UPSDM?"}'
```

You should get a JSON response with `reply`, `stage`, `source_ids`, `latency_ms`, etc.

---

## 5. Unit Tests (Offline — No Server Needed)

Unit tests run locally using the Python virtualenv. They load the embedding
model and FAISS index directly — **no Docker containers required** (though the
FAISS index files in `data/faiss_index/` must exist).

### 5.1 Run All Unit Tests

```bash
venv/bin/pytest tests/ -v
```

### 5.2 Run Specific Test Suites

| Test File | What It Covers | Command |
|---|---|---|
| `test_contract.py` | C# integration contract — security regex, greeting/fallback compliance | `venv/bin/pytest tests/test_contract.py -v` |
| `test_redesigned_router.py` | End-to-end routing: greetings, out-of-scope, static lookup, FAISS, persona, intent | `venv/bin/pytest tests/test_redesigned_router.py -v` |
| `test_extractive_generator.py` | Sentence-level extractive answer generation with precomputed embeddings | `venv/bin/pytest tests/test_extractive_generator.py -v` |
| `test_ingestion_quality.py` | Markdown link stripping, NFKC ligature normalization, administrative_list filtering | `venv/bin/pytest tests/test_ingestion_quality.py -v` |
| `test_locator_routing.py` | Locator intent detection (location-based queries with UP gazetteer) | `venv/bin/pytest tests/test_locator_routing.py -v` |
| `test_process_routing.py` | Process intent detection (reimbursement/empanelment queries) | `venv/bin/pytest tests/test_process_routing.py -v` |
| `test_ambiguity_clarification.py` | Ambiguous match response format — options instead of generic refusal | `venv/bin/pytest tests/test_ambiguity_clarification.py -v` |

### 5.3 Expected Output

```
==================== 17 passed, 9 warnings in ~90s ====================
```

> **Note:** First run takes ~60–90 seconds because the sentence-transformer
> model (`all-MiniLM-L6-v2`) is loaded into memory. Subsequent runs are faster
> if model caching is warm.

---

## 6. Integration Tests (Server Required)

These tests hit the **live Docker server** at `http://localhost:8000`.
Make sure the server is running (Step 3) before running these.

### 6.1 Manual API Query Test

```bash
venv/bin/python -c "
import httpx

queries = [
    'What is UPSDM?',
    'How can I enroll in a skill development course?',
    'Where can I find the list of training centers in Lucknow?',
    'How do I claim reimbursement for candidate training?',
    'What is the capital of France?',
    'Hello there!'
]

for q in queries:
    resp = httpx.post('http://localhost:8000/chat', json={'message': q}).json()
    print(f'Q: {q}')
    print(f'   Stage: {resp[\"stage\"]}  |  Latency: {resp[\"latency_ms\"]}ms')
    print(f'   Reply: {resp[\"reply\"][:80]}...')
    print()
"
```

### 6.2 Expected Stage Assignments

| Query | Expected Stage |
|---|---|
| "What is UPSDM?" | `faiss_direct` |
| "How can I enroll…?" | `static_lookup` |
| "…training centers in Lucknow?" | `static_lookup` (Locator intent) |
| "…claim reimbursement…?" | `static_lookup` (Process intent) |
| "What is the capital of France?" | `out_of_scope` |
| "Hello there!" | `greeting` |

---

## 7. Benchmark Testing (26-Question Bank)

The question bank (`scripts/test_question_bank.py`) runs all 26 curated
benchmark questions covering Student, Training Partner, Industrial Partner, and
Edge Case personas.

### 7.1 Run the Benchmark

```bash
venv/bin/python scripts/test_question_bank.py --output reports/benchmarks/run_YYYYMMDD.md
```

Replace `YYYYMMDD` with today's date (e.g. `run_20260721.md`).

### 7.2 What It Produces

- **Console output**: Per-question detail (stage, latency, source IDs, expected vs actual answer)
  plus a summary table.
- **File output**: Full markdown report saved to the `--output` path.

### 7.3 Key Metrics to Check

| Metric | Target |
|---|---|
| All 26 questions answered | No HTTP errors |
| `GREETING` stage latency | < 10 ms |
| `STATIC_LOOKUP` latency | < 60 ms |
| `FAISS_DIRECT` latency | < 100 ms |
| `OUT_OF_SCOPE` correctly classified | Q23, Q24 |
| No raw link fragments in answers | Q1, Q3, Q7 should be clean |

---

## 8. Retrieval Quality Evaluation

Evaluates raw FAISS retrieval quality (Recall@k, MRR) independently of routing.

### 8.1 Run Retrieval Evaluation

```bash
venv/bin/python scripts/eval_retrieval.py
```

### 8.2 What It Checks

- Uses the evaluation set at `tests/eval_set.csv` (query → expected chunk ID mappings).
- Reports Recall@1, Recall@3, Recall@5, and Mean Reciprocal Rank (MRR).
- Does **not** require the Docker server — runs directly against the local FAISS index.

---

## 9. Interactive Manual Testing

For exploratory testing where you want to type questions freely and see
responses in real-time.

### 9.1 Start Interactive Chat

```bash
venv/bin/python scripts/interactive_chat.py
```

### 9.2 Suggested Test Scenarios

Try each category below and observe the `Stage` and response quality:

**Greetings (should respond instantly, stage = GREETING):**
```
> Hello
> Namaste
> Hi there
```

**In-Scope Static Knowledge (stage = STATIC_LOOKUP):**
```
> What is the helpline number for UPSDM?
> How can I enroll in a skill development course?
> What is the Flexi MoU scheme?
```

**In-Scope FAISS Retrieval (stage = FAISS_DIRECT):**
```
> What is UPSDM?
> What are the eligibility criteria for the PMKVY scheme?
```

**Location-Based Queries (stage = STATIC_LOOKUP, Locator intent):**
```
> Where can I find the list of training centers in Lucknow?
> Find assessment centers in Varanasi
```

**Process Queries (stage = STATIC_LOOKUP, Process intent):**
```
> How do I claim reimbursement for candidate training?
> What is the empanelment process for new training programs?
```

**Out-of-Scope (stage = OUT_OF_SCOPE):**
```
> What is the capital of France?
> Who is the Prime Minister of Australia?
```

**Hindi Language Support:**
```
> UPSDM क्या है?
> नमस्ते
```

### 9.3 Exit

Type `exit`, `quit`, or press `Ctrl+C`.

---

## 10. Load / Stress Testing

Sends concurrent requests to measure throughput and latency under load.

### 10.1 Run Load Test

```bash
venv/bin/python scripts/load_test.py
```

### 10.2 What It Measures

- Sends multiple concurrent queries to `http://localhost:8000/chat`.
- Reports per-request latency, success rate, and throughput.
- Useful for checking if the concurrency queue and Redis caching hold up under pressure.

---

## 11. Benchmark Comparison & Reports

### 11.1 Compare Two Benchmark Runs

```bash
venv/bin/python scripts/compare_benchmarks.py \
  reports/benchmarks/baseline_run.md \
  reports/benchmarks/new_run.md
```

Prints a diff table showing per-question stage changes, latency deltas, and
regression flags.

### 11.2 Generate Full Comparison Report (Baseline vs Final)

```bash
venv/bin/python scripts/generate_full_comparison.py
```

Produces `reports/benchmarks/FULL_COMPARISON.md` with:
1. Per-question stage/latency comparison table
2. AMBIGUOUS_MATCH resolution count
3. Dirty-content (link fragments / blacklist) count
4. FAISS_DIRECT average and P95 latency metrics

> **Note:** Edit the `baseline_path` and `final_path` variables inside the
> script if your report filenames differ.

---

## 12. Rebuilding After Code Changes

If you modify any source code, you need to rebuild and restart:

### 12.1 Code Changes Only (No Data Changes)

```bash
docker compose up --build -d rag-chatbot-brain
```

### 12.2 Data / Index Changes (After Modifying Chunks or Seeds)

```bash
# Step 1: Rebuild the FAISS index + sentence embeddings
venv/bin/python scripts/build_index.py

# Step 2: Rebuild and restart the container
docker compose up --build -d rag-chatbot-brain
```

### 12.3 Full Pipeline Rebuild (Crawl → Extract → Chunk → Index)

```bash
# Step 1: Re-crawl the UPSDM website
venv/bin/python scripts/run_crawler.py

# Step 2: Rebuild FAISS index
venv/bin/python scripts/build_index.py

# Step 3: Rebuild container
docker compose up --build -d rag-chatbot-brain
```

---

## 13. Troubleshooting

| Problem | Solution |
|---|---|
| `Connection refused` on port 8000 | Check `docker compose ps` — the brain container may still be starting. Wait 10s and retry. |
| Tests fail with `ModuleNotFoundError` | Make sure you activated the venv: `source venv/bin/activate` |
| `FAISS index not found` | Run `venv/bin/python scripts/build_index.py` first. |
| `Tesseract not installed` warning | This is non-fatal. PDF OCR is optional. Ignore safely. |
| Ollama model not found | Run `docker logs upsdm-chatbot-model-setup -f` to check if model pull completed. |
| Slow first query (~5s) | Normal — the sentence-transformer model loads on first request. Subsequent queries are fast. |
| `Permission denied` on Docker | Make sure Docker Desktop is running and your user has Docker access. |
| Tests timeout (>120s) | The embedding model download may be in progress. Check `~/.cache/huggingface/` for download activity. |

---

## Quick Reference: Common Commands

```bash
# Start everything
docker compose up --build -d

# Check health
curl http://localhost:8000/health

# Run all unit tests
venv/bin/pytest tests/ -v

# Run 26-question benchmark
venv/bin/python scripts/test_question_bank.py --output reports/benchmarks/run_YYYYMMDD.md

# Interactive chat
venv/bin/python scripts/interactive_chat.py

# View server logs
docker logs upsdm-chatbot-brain -f

# Stop everything
docker compose down
```
