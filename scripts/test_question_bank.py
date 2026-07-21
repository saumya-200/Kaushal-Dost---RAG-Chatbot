import httpx
import time
import asyncio
import json
import os
import uuid
from pathlib import Path

# ============================================================
# UPSDM RAG CHATBOT - QUESTION BANK WITH EXPECTED ANSWERS
# ============================================================
# Each question includes an "expected" answer summary so you can
# compare the chatbot's actual reply against what it SHOULD say.
# ============================================================

QUESTION_BANK = {
    "Student": [
        {
            "q": "What is UPSDM?",
            "expected": "UPSDM stands for Uttar Pradesh Skill Development Mission. It aims to train eligible youth aged 14-35 in preferred trades, upgrade skills of unskilled/semi-skilled workforce, and provide provisions for women, PWD, and minorities."
        },
        {
            "q": "How can I enroll in a skill development course?",
            "expected": "Candidates can register through the Kaushal Drishti portal or the Candidate Registration link on upsdm.gov.in. They need to visit a nearby Skill Development Center."
        },
        {
            "q": "What are the eligibility criteria for the PMKVY scheme?",
            "expected": "Eligible youth in the 14-35 age group can enroll. Trainings are in NSQF-compliant courses only. 30% targets are earmarked for women and 20% for minorities."
        },
        {
            "q": "Do you provide placement assistance after training?",
            "expected": "Yes, UPSDM has Placement Partners who assist trained candidates in finding jobs. The system tracks enrolled, trained, assessed, and appointed candidates."
        },
        {
            "q": "Where can I find the list of training centers in Lucknow?",
            "expected": "You can find training centers using the 'Search Centers' link on upsdm.gov.in or by visiting the Skill Development Centers page."
        },
        {
            "q": "What courses are available under UPSDM?",
            "expected": "UPSDM offers both Traditional and Futuristic job role courses across multiple sectors. Details are available on the Sector & Course page at upsdm.gov.in."
        },
        {
            "q": "What is Kaushal Drishti?",
            "expected": "Kaushal Drishti is a portal for candidate registration and skill development tracking under UPSDM."
        },
        {
            "q": "What is the helpline number for UPSDM?",
            "expected": "The UPSDM Toll Free Helpline Number is 0522-4944200. Email: mdssdm-up[at]nic[dot]in."
        }
    ],
    "Training Partner (TP)": [
        {
            "q": "How can I register my institute as a Training Partner with UPSDM?",
            "expected": "Training Partners can register through the Training Partners section on upsdm.gov.in. There are categories of TPs listed on the portal."
        },
        {
            "q": "What are the infrastructure requirements for a training center?",
            "expected": "Training centers must meet NSQF-compliant infrastructure standards. Specific requirements depend on the sector and course being offered."
        },
        {
            "q": "How do I claim reimbursement for candidate training?",
            "expected": "Reimbursement claims are processed through the UPSDM portal. TPs need to submit training completion and assessment records."
        },
        {
            "q": "What is the empanelment process for new training programs?",
            "expected": "New training programs must be NSQF-compliant. TPs can apply through the RFP Registration portal on upsdm.gov.in."
        },
        {
            "q": "How to upload student attendance on the portal?",
            "expected": "Attendance is uploaded through the Skill Development Center Live Capture mobile app, available for download on the UPSDM portal."
        },
        {
            "q": "What is the TP grading system?",
            "expected": "UPSDM grades Training Partners annually. Grading reports for 2024-25 and 2025-26 are available as PDF downloads on upsdm.gov.in."
        },
        {
            "q": "What happens if a TP is de-empanelled?",
            "expected": "De-empanelled TPs are listed on the De-empanelled TP List page on upsdm.gov.in. They lose the right to conduct training under UPSDM schemes."
        }
    ],
    "Industrial Partner": [
        {
            "q": "How can our company collaborate with UPSDM for hiring skilled workforce?",
            "expected": "Companies can collaborate as Placement Partners through the Placement Partner section on upsdm.gov.in."
        },
        {
            "q": "What is the Flexi MoU scheme?",
            "expected": "The Flexi MoU is a scheme under UPSDM that allows flexible partnership agreements for skill development between industry and the mission."
        },
        {
            "q": "Can we customize the training curriculum for our industry needs?",
            "expected": "Training courses follow NSQF standards. Industry partners can work with Sector Skill Councils (SSC) to influence curriculum relevant to their sector."
        },
        {
            "q": "Are there any financial benefits or subsidies for hiring apprentices through UPSDM?",
            "expected": "UPSDM schemes like DDU-GKY and PMKVY provide government-funded training. Financial details are available in the scheme guidelines PDFs on the portal."
        },
        {
            "q": "Who is the nodal officer for industry tie-ups?",
            "expected": "Contact the SPMU (State Project Management Unit) via the Contact Us page on upsdm.gov.in or call 0522-4944200."
        },
        {
            "q": "What sectors does UPSDM cover for skill training?",
            "expected": "UPSDM covers multiple sectors including traditional and futuristic job roles. Full sector and course details are available on the Sector & Course page."
        }
    ],
    "General / Edge Cases": [
        {
            "q": "Hello there!",
            "expected": "[GREETING] Should return instant greeting template like 'Hello! I'm Kaushal Dost, your UPSDM assistant.'"
        },
        {
            "q": "Namaste!",
            "expected": "[GREETING] Should return a Hindi greeting template response instantly."
        },
        {
            "q": "Who is the Prime Minister of Australia?",
            "expected": "[OUT OF SCOPE] Should trigger low-confidence fallback. Not related to UPSDM."
        },
        {
            "q": "What is the capital of France?",
            "expected": "[OUT OF SCOPE] Should trigger low-confidence fallback. Not related to UPSDM."
        },
        {
            "q": "Is there a helpline number for UPSDM?",
            "expected": "Toll Free Helpline Number 0522-4944200. Email: mdssdm-up[at]nic[dot]in."
        }
    ]
}


def print_separator():
    print("=" * 80)


def print_result(category, idx, question, expected, stage, latency_ms, actual_answer, server_latency_ms, source_ids):
    print(f"\n  Q{idx}. {question}")
    print(f"  {'─' * 76}")
    print(f"  Stage:          {stage.upper()}")
    print(f"  Client Latency: {latency_ms:.2f} ms")
    print(f"  Server Latency: {server_latency_ms:.2f} ms")
    if source_ids:
        print(f"  Source IDs:     {', '.join(source_ids[:3])}")
    print(f"  {'─' * 76}")
    print(f"  EXPECTED ANSWER:")
    # Word-wrap expected answer
    for line in _wrap_text(expected, 74):
        print(f"    {line}")
    print(f"  {'─' * 76}")
    print(f"  ACTUAL ANSWER:")
    for line in _wrap_text(actual_answer[:500], 74):
        print(f"    {line}")
    print(f"  {'─' * 76}")


def _wrap_text(text, width):
    """Simple word-wrap for terminal display."""
    words = text.replace("\n", " ").split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 <= width:
            current = f"{current} {w}" if current else w
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines if lines else ["(empty)"]


async def test_question(client, category, idx, item):
    question = item["q"]
    expected = item["expected"]
    test_id = f"test-run-{uuid.uuid4()}"

    url = "http://localhost:8000/chat"
    payload = {"message": question, "history": [], "test_id": test_id}

    t0 = time.time()
    try:
        response = await client.post(url, json=payload, timeout=200.0)
        latency = (time.time() - t0) * 1000

        if response.status_code == 200:
            data = response.json()
            stage = data.get("stage", "unknown")
            actual_answer = data.get("reply", "(no reply field)")
            server_latency = data.get("latency_ms", 0.0)
            source_ids = data.get("source_ids", [])
            print_result(category, idx, question, expected, stage, latency, actual_answer, server_latency, source_ids)
        else:
            print(f"\n  Q{idx}. {question}")
            print(f"  => ERROR: HTTP {response.status_code} | Latency: {latency:.2f} ms")

    except Exception as e:
        latency = (time.time() - t0) * 1000
        print(f"\n  Q{idx}. {question}")
        print(f"  => FAILED: {str(e)[:100]} | Latency: {latency:.2f} ms")


async def main():
    print_separator()
    print("  UPSDM RAG CHATBOT - QUESTION BANK LATENCY & ACCURACY TEST")
    print_separator()
    print("  Server: http://localhost:8000")
    print("  Ensure Docker containers are running (redis, ollama, brain).")
    print(f"  Total questions: {sum(len(qs) for qs in QUESTION_BANK.values())}")
    print_separator()
    print("  Starting test in 3 seconds...\n")
    time.sleep(3)

    results_summary = []

    async with httpx.AsyncClient() as client:
        for category, questions in QUESTION_BANK.items():
            print_separator()
            print(f"  PERSONA: {category.upper()} ({len(questions)} questions)")
            print_separator()

            for idx, item in enumerate(questions, 1):
                t0 = time.time()
                test_id = f"test-run-{uuid.uuid4()}"
                try:
                    response = await client.post(
                        "http://localhost:8000/chat",
                        json={"message": item["q"], "history": [], "test_id": test_id},
                        timeout=200.0
                    )
                    latency = (time.time() - t0) * 1000

                    if response.status_code == 200:
                        data = response.json()
                        stage = data.get("stage", "unknown")
                        actual = data.get("reply", "(no reply)")
                        server_lat = data.get("latency_ms", 0.0)
                        sources = data.get("source_ids", [])
                        print_result(category, idx, item["q"], item["expected"], stage, latency, actual, server_lat, sources)
                        results_summary.append({
                            "category": category,
                            "question": item["q"],
                            "stage": stage,
                            "latency_ms": round(latency, 2),
                            "server_latency_ms": round(server_lat, 2)
                        })
                    else:
                        print(f"\n  Q{idx}. {item['q']}")
                        print(f"  => ERROR: HTTP {response.status_code}")

                except Exception as e:
                    latency = (time.time() - t0) * 1000
                    print(f"\n  Q{idx}. {item['q']}")
                    print(f"  => FAILED: {str(e)[:100]}")

                await asyncio.sleep(0.5)

    # Print summary table
    print("\n")
    print_separator()
    print("  SUMMARY TABLE")
    print_separator()
    print(f"  {'Category':<25} {'Question':<55} {'Stage':<18} {'Latency (ms)':>12}")
    print(f"  {'─'*25} {'─'*55} {'─'*18} {'─'*12}")
    for r in results_summary:
        q_short = r['question'][:52] + "..." if len(r['question']) > 55 else r['question']
        print(f"  {r['category']:<25} {q_short:<55} {r['stage'].upper():<18} {r['latency_ms']:>12.2f}")

    print_separator()
    print(f"  Total questions tested: {len(results_summary)}")
    print_separator()


import argparse
import sys

class TeeLogger:
    def __init__(self, filepath):
        self.stream = sys.__stdout__
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        self.file = open(filepath, "w", encoding="utf-8")

    def write(self, data):
        self.stream.write(data)
        self.file.write(data)

    def flush(self):
        self.stream.flush()
        self.file.flush()

    def close(self):
        self.file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UPSDM RAG Chatbot Question Bank Test")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save full output markdown file")
    args = parser.parse_args()

    tee = None
    if args.output:
        tee = TeeLogger(args.output)
        sys.stdout = tee

    try:
        asyncio.run(main())
    finally:
        if tee:
            sys.stdout = sys.__stdout__
            tee.close()

