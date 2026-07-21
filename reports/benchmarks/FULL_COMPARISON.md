# UPSDM RAG Chatbot — Full Optimization Evidence Pack

**Baseline**: `reports/benchmarks/baseline_20260721_1303.md`  
**Final**: `reports/benchmarks/final_20260721.md`  
**Questions**: 26

---

## 1. Per-Question Stage & Latency Comparison

| # | Category | Question | Baseline Stage | Final Stage | Baseline (ms) | Final (ms) | Improvement |
|---|---|---|---|---|---|---|---|
| 1 | Student | What is UPSDM? | `FAISS_DIRECT` | `FAISS_DIRECT` | 273.59 | 97.79 | +64.3% |
| 2 | Student | How can I enroll in a skill development course? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 50.25 | 47.59 | +5.3% |
| 3 | Student | What are the eligibility criteria for the PMKVY scheme? | `FAISS_DIRECT` | `FAISS_DIRECT` | 934.38 | 47.17 | +95.0% |
| 4 | Student | Do you provide placement assistance after training? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 45.63 | 46.64 | -2.2% |
| 5 | Student | Where can I find the list of training centers in Luc... | `AMBIGUOUS_MATCH` | `STATIC_LOOKUP` | 50.02 | 47.84 | +4.4% |
| 6 | Student | What courses are available under UPSDM? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 53.60 | 47.11 | +12.1% |
| 7 | Student | What is Kaushal Drishti? | `FAISS_DIRECT` | `FAISS_DIRECT` | 387.11 | 50.94 | +86.8% |
| 8 | Student | What is the helpline number for UPSDM? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 49.55 | 45.91 | +7.3% |
| 9 | Training Partner (TP) | How can I register my institute as a Training Partne... | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 44.03 | 46.96 | -6.7% |
| 10 | Training Partner (TP) | What are the infrastructure requirements for a train... | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 45.79 | 45.74 | +0.1% |
| 11 | Training Partner (TP) | How do I claim reimbursement for candidate training? | `AMBIGUOUS_MATCH` | `STATIC_LOOKUP` | 44.40 | 58.74 | -32.3% |
| 12 | Training Partner (TP) | What is the empanelment process for new training pro... | `AMBIGUOUS_MATCH` | `STATIC_LOOKUP` | 53.47 | 47.42 | +11.3% |
| 13 | Training Partner (TP) | How to upload student attendance on the portal? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 38.78 | 51.44 | -32.6% |
| 14 | Training Partner (TP) | What is the TP grading system? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 49.63 | 42.34 | +14.7% |
| 15 | Training Partner (TP) | What happens if a TP is de-empanelled? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 42.33 | 47.57 | -12.4% |
| 16 | Industrial Partner | How can our company collaborate with UPSDM for hirin... | `FAISS_DIRECT` | `FAISS_DIRECT` | 295.42 | 51.56 | +82.5% |
| 17 | Industrial Partner | What is the Flexi MoU scheme? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 43.75 | 43.78 | -0.1% |
| 18 | Industrial Partner | Can we customize the training curriculum for our ind... | `AMBIGUOUS_MATCH` | `AMBIGUOUS_MATCH` | 56.04 | 45.88 | +18.1% |
| 19 | Industrial Partner | Are there any financial benefits or subsidies for hi... | `FAISS_DIRECT` | `FAISS_DIRECT` | 317.68 | 39.51 | +87.6% |
| 20 | Industrial Partner | Who is the nodal officer for industry tie-ups? | `FAISS_DIRECT` | `FAISS_DIRECT` | 275.64 | 67.49 | +75.5% |
| 21 | Industrial Partner | What sectors does UPSDM cover for skill training? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 44.21 | 44.84 | -1.4% |
| 22 | General / Edge Cases | Hello there! | `GREETING` | `GREETING` | 4.30 | 8.28 | -92.6% |
| 23 | General / Edge Cases | Namaste! | `GREETING` | `GREETING` | 7.27 | 7.12 | +2.1% |
| 24 | General / Edge Cases | Who is the Prime Minister of Australia? | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | 41.22 | 38.13 | +7.5% |
| 25 | General / Edge Cases | What is the capital of France? | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | 42.48 | 36.56 | +13.9% |
| 26 | General / Edge Cases | Is there a helpline number for UPSDM? | `STATIC_LOOKUP` | `STATIC_LOOKUP` | 45.06 | 47.54 | -5.5% |

---

## 2. AMBIGUOUS_MATCH Query Resolution

| Metric | Count |
|---|---|
| Baseline AMBIGUOUS_MATCH questions | **4** |
| Resolved (no longer AMBIGUOUS_MATCH in final) | **3** |
| Still AMBIGUOUS_MATCH in final | **1** |

---

## 3. FAISS_DIRECT Answers with Raw Link Syntax / Blacklist Content

| Metric | Baseline | Final |
|---|---|---|
| FAISS_DIRECT answers containing link fragments or blacklist content | **2** | **0** |

---

## 4. FAISS_DIRECT Latency — Baseline vs Final

| Metric | Baseline (ms) | Final (ms) | Drop (ms) | Speedup |
|---|---|---|---|---|
| **Average** | 413.97 | 59.08 | −354.89 | **85.7%** |
| **P95** | 797.56 | 90.22 | −707.35 | **88.7%** |
| **Question count** | 6 | 6 | — | — |
