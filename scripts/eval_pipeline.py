"""
UPSDM RAG Pipeline Evaluation Script
=====================================
Measures:
  - Static lookup accuracy
  - Scope detector accuracy
  - Cache hit rate
  - Extractive routing %
  - LLM routing %
  - End-to-end latency per stage
  - Hallucination detection (invented phone numbers / URLs)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import httpx
import time
import asyncio
import json
import re
from collections import defaultdict


# ============================================================
# TEST DATA
# ============================================================

# Static lookup queries — should be answered instantly without LLM
STATIC_LOOKUP_TESTS = [
    {"q": "What is the helpline number?", "expected_stage": "static_lookup", "expected_contains": "0522-4944200"},
    {"q": "UPSDM email id", "expected_stage": "static_lookup", "expected_contains": "mdssdm"},
    {"q": "official website", "expected_stage": "static_lookup", "expected_contains": "upsdm.gov.in"},
    {"q": "how to register", "expected_stage": "static_lookup", "expected_contains": "register"},
    {"q": "हेल्पलाइन नंबर", "expected_stage": "static_lookup", "expected_contains": "0522-4944200"},
    {"q": "download form", "expected_stage": "static_lookup", "expected_contains": "Downloads"},
    {"q": "training center near me", "expected_stage": "static_lookup", "expected_contains": "Search Centers"},
    {"q": "kaushal drishti", "expected_stage": "static_lookup", "expected_contains": "Kaushal Drishti"},
]

# Out-of-scope queries — should be rejected without LLM
SCOPE_TESTS = [
    {"q": "What is the capital of France?", "expected_stage": "out_of_scope"},
    {"q": "Explain quantum physics", "expected_stage": "out_of_scope"},
    {"q": "Who is the prime minister of Australia?", "expected_stage": "out_of_scope"},
    {"q": "Best cricket player in the world", "expected_stage": "out_of_scope"},
    {"q": "How to make butter chicken recipe", "expected_stage": "out_of_scope"},
    {"q": "stock market tips for today", "expected_stage": "out_of_scope"},
]

# In-scope UPSDM queries — should NOT be rejected
INSCOPE_TESTS = [
    {"q": "What is UPSDM?", "expected_in_scope": True},
    {"q": "What is PMKVY scheme?", "expected_in_scope": True},
    {"q": "DDU-GKY scheme details", "expected_in_scope": True},
    {"q": "How to become a training partner?", "expected_in_scope": True},
    {"q": "What courses are available?", "expected_in_scope": True},
]

# General pipeline queries — measures routing distribution
PIPELINE_TESTS = [
    {"q": "What is UPSDM?", "category": "about"},
    {"q": "UPSDM में रजिस्ट्रेशन कैसे करें?", "category": "registration"},
    {"q": "What are the eligibility criteria for PMKVY?", "category": "eligibility"},
    {"q": "What is DPMU?", "category": "about"},
    {"q": "Do you provide placement assistance?", "category": "placement"},
    {"q": "What is the TP grading system?", "category": "tp_grading"},
    {"q": "success stories dikhao", "category": "stories"},
    {"q": "privacy policy kya hai", "category": "policy"},
    {"q": "DDU-GKY scheme details", "category": "schemes"},
    {"q": "What is RPL?", "category": "about"},
]

# Known correct facts — for hallucination detection
KNOWN_FACTS = {
    "helpline": "0522-4944200",
    "email": "mdssdm-up",
    "website": "upsdm.gov.in",
}


def print_separator(char="=", width=80):
    print(char * width)


def print_section(title):
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


async def query_chatbot(client, question, timeout=200.0):
    """Sends a query to the chatbot and returns (response_data, latency_ms)."""
    t0 = time.time()
    try:
        response = await client.post(
            "http://localhost:8000/chat",
            json={"message": question, "history": []},
            timeout=timeout
        )
        latency = (time.time() - t0) * 1000
        if response.status_code == 200:
            return response.json(), latency
        else:
            return {"error": f"HTTP {response.status_code}"}, latency
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return {"error": str(e)[:200]}, latency


def check_hallucination(reply):
    """
    Checks if the response contains invented phone numbers or URLs
    that don't match known UPSDM facts.
    """
    issues = []

    # Check for phone numbers that aren't the real helpline
    phone_matches = re.findall(r'\b\d{3,4}[-\s]?\d{6,7}\b', reply)
    for phone in phone_matches:
        normalized = phone.replace("-", "").replace(" ", "")
        if "05224944200" not in normalized and len(normalized) >= 10:
            issues.append(f"Invented phone: {phone}")

    # Check for URLs that aren't upsdm.gov.in
    url_matches = re.findall(r'https?://\S+', reply)
    for url in url_matches:
        if "upsdm.gov.in" not in url and "lmsupsdm.com" not in url:
            issues.append(f"Unknown URL: {url}")

    return issues


async def run_evaluation():
    print_section("UPSDM RAG PIPELINE EVALUATION")
    print(f"  Server: http://localhost:8000")
    print(f"  Starting evaluation...\n")

    results = {
        "static_lookup": {"total": 0, "correct_stage": 0, "correct_content": 0, "latencies": []},
        "scope_reject": {"total": 0, "correct": 0, "latencies": []},
        "scope_accept": {"total": 0, "correct": 0, "latencies": []},
        "pipeline": {"total": 0, "stages": defaultdict(int), "latencies": [], "hallucinations": 0},
        "cache": {"first_pass": 0, "second_pass_hits": 0},
    }

    async with httpx.AsyncClient() as client:
        # ─────────────────────────────────────────────
        # TEST 1: Static Lookup Accuracy
        # ─────────────────────────────────────────────
        print_section("TEST 1: Static Lookup Accuracy")

        for test in STATIC_LOOKUP_TESTS:
            data, latency = await query_chatbot(client, test["q"])
            results["static_lookup"]["total"] += 1
            results["static_lookup"]["latencies"].append(latency)

            stage = data.get("stage", "unknown")
            reply = data.get("reply", "")
            stage_ok = stage == test["expected_stage"]
            content_ok = test["expected_contains"].lower() in reply.lower()

            if stage_ok:
                results["static_lookup"]["correct_stage"] += 1
            if content_ok:
                results["static_lookup"]["correct_content"] += 1

            status = "✅" if (stage_ok and content_ok) else "❌"
            print(f"  {status} [{latency:7.1f}ms] [{stage:15s}] {test['q']}")
            if not stage_ok:
                print(f"     Expected stage: {test['expected_stage']}, got: {stage}")
            if not content_ok:
                print(f"     Expected '{test['expected_contains']}' in response")

            await asyncio.sleep(0.3)

        # ─────────────────────────────────────────────
        # TEST 2: Scope Detector — Out of Scope
        # ─────────────────────────────────────────────
        print_section("TEST 2: Scope Detector — Out of Scope Rejection")

        for test in SCOPE_TESTS:
            data, latency = await query_chatbot(client, test["q"])
            results["scope_reject"]["total"] += 1
            results["scope_reject"]["latencies"].append(latency)

            stage = data.get("stage", "unknown")
            correct = stage in ("out_of_scope", "fallback")

            if correct:
                results["scope_reject"]["correct"] += 1

            status = "✅" if correct else "❌"
            print(f"  {status} [{latency:7.1f}ms] [{stage:15s}] {test['q']}")

            await asyncio.sleep(0.3)

        # ─────────────────────────────────────────────
        # TEST 3: Scope Detector — In Scope Acceptance
        # ─────────────────────────────────────────────
        print_section("TEST 3: Scope Detector — In-Scope Acceptance")

        for test in INSCOPE_TESTS:
            data, latency = await query_chatbot(client, test["q"])
            results["scope_accept"]["total"] += 1
            results["scope_accept"]["latencies"].append(latency)

            stage = data.get("stage", "unknown")
            correct = stage not in ("out_of_scope",)

            if correct:
                results["scope_accept"]["correct"] += 1

            status = "✅" if correct else "❌"
            print(f"  {status} [{latency:7.1f}ms] [{stage:15s}] {test['q']}")

            await asyncio.sleep(0.3)

        # ─────────────────────────────────────────────
        # TEST 4: Pipeline Routing + Hallucination
        # ─────────────────────────────────────────────
        print_section("TEST 4: Pipeline Routing Distribution + Hallucination Check")

        for test in PIPELINE_TESTS:
            data, latency = await query_chatbot(client, test["q"])
            results["pipeline"]["total"] += 1
            results["pipeline"]["latencies"].append(latency)

            stage = data.get("stage", "unknown")
            reply = data.get("reply", "")
            results["pipeline"]["stages"][stage] += 1

            hall_issues = check_hallucination(reply)
            if hall_issues:
                results["pipeline"]["hallucinations"] += 1

            hall_flag = " ⚠️HALL" if hall_issues else ""
            print(f"  [{latency:7.1f}ms] [{stage:15s}] {test['q']}{hall_flag}")
            for issue in hall_issues:
                print(f"     Hallucination: {issue}")

            await asyncio.sleep(0.5)

        # ─────────────────────────────────────────────
        # TEST 5: Cache Hit Rate (run same queries twice)
        # ─────────────────────────────────────────────
        print_section("TEST 5: Semantic Cache Hit Rate")

        cache_queries = [t["q"] for t in PIPELINE_TESTS[:5]]
        results["cache"]["first_pass"] = len(cache_queries)

        # Second pass — should hit cache
        print("  Running second pass on same queries...")
        for q in cache_queries:
            data, latency = await query_chatbot(client, q)
            stage = data.get("stage", "unknown")
            is_cached = stage == "semantic_cache"
            if is_cached:
                results["cache"]["second_pass_hits"] += 1
            status = "✅ CACHE HIT" if is_cached else f"❌ {stage}"
            print(f"  {status} [{latency:7.1f}ms] {q}")
            await asyncio.sleep(0.3)

    # ─────────────────────────────────────────────
    # SUMMARY REPORT
    # ─────────────────────────────────────────────
    print_section("EVALUATION SUMMARY REPORT")

    # Static Lookup
    sl = results["static_lookup"]
    sl_stage_acc = (sl["correct_stage"] / sl["total"] * 100) if sl["total"] > 0 else 0
    sl_content_acc = (sl["correct_content"] / sl["total"] * 100) if sl["total"] > 0 else 0
    sl_avg_lat = sum(sl["latencies"]) / len(sl["latencies"]) if sl["latencies"] else 0

    print(f"\n  Static Lookup:")
    print(f"    Stage accuracy:   {sl_stage_acc:.0f}% ({sl['correct_stage']}/{sl['total']})")
    print(f"    Content accuracy: {sl_content_acc:.0f}% ({sl['correct_content']}/{sl['total']})")
    print(f"    Avg latency:      {sl_avg_lat:.1f}ms")

    # Scope Detection
    sr = results["scope_reject"]
    sr_acc = (sr["correct"] / sr["total"] * 100) if sr["total"] > 0 else 0
    sr_avg_lat = sum(sr["latencies"]) / len(sr["latencies"]) if sr["latencies"] else 0

    sa = results["scope_accept"]
    sa_acc = (sa["correct"] / sa["total"] * 100) if sa["total"] > 0 else 0

    print(f"\n  Scope Detection:")
    print(f"    Out-of-scope rejection:  {sr_acc:.0f}% ({sr['correct']}/{sr['total']})")
    print(f"    In-scope acceptance:     {sa_acc:.0f}% ({sa['correct']}/{sa['total']})")
    print(f"    Avg reject latency:      {sr_avg_lat:.1f}ms")

    # Pipeline Distribution
    pl = results["pipeline"]
    print(f"\n  Pipeline Routing Distribution:")
    for stage, count in sorted(pl["stages"].items(), key=lambda x: -x[1]):
        pct = (count / pl["total"] * 100) if pl["total"] > 0 else 0
        print(f"    {stage:20s}: {count:3d} ({pct:.0f}%)")

    pl_avg_lat = sum(pl["latencies"]) / len(pl["latencies"]) if pl["latencies"] else 0
    print(f"    Avg end-to-end latency:  {pl_avg_lat:.1f}ms")
    print(f"    Hallucination count:     {pl['hallucinations']}/{pl['total']}")

    # Cache
    ca = results["cache"]
    cache_rate = (ca["second_pass_hits"] / ca["first_pass"] * 100) if ca["first_pass"] > 0 else 0
    print(f"\n  Semantic Cache:")
    print(f"    Hit rate (2nd pass):     {cache_rate:.0f}% ({ca['second_pass_hits']}/{ca['first_pass']})")

    # Overall
    total_queries = sl["total"] + sr["total"] + sa["total"] + pl["total"] + ca["first_pass"]
    llm_count = pl["stages"].get("llm_generation", 0)
    non_llm_pct = ((pl["total"] - llm_count) / pl["total"] * 100) if pl["total"] > 0 else 0

    print(f"\n  Overall:")
    print(f"    Total queries evaluated:  {total_queries}")
    print(f"    LLM bypass rate:          {non_llm_pct:.0f}% of pipeline queries avoided LLM")

    print_separator()
    print("  Evaluation complete!")
    print_separator()


if __name__ == "__main__":
    asyncio.run(run_evaluation())
