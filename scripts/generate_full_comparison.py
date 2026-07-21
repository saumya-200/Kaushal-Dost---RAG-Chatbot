"""
Generate FULL_COMPARISON.md: baseline vs final benchmark evidence pack.

Parses both the SUMMARY TABLE (for stage/latency) and the per-question
detailed blocks (for actual answer text, needed for dirty-content checks).
"""

import re
import numpy as np
from pathlib import Path

# ── Parsing helpers ──────────────────────────────────────────────────────────

KNOWN_STAGES = {"FAISS_DIRECT", "STATIC_LOOKUP", "AMBIGUOUS_MATCH", "GREETING",
                 "OUT_OF_SCOPE", "FALLBACK", "CACHED"}

def parse_summary_table(content: str) -> list[dict]:
    """Extract rows from the fixed-width SUMMARY TABLE at the bottom of a report."""
    table_match = re.search(r'SUMMARY TABLE\n={40,}\n(.*?)={40,}', content, re.DOTALL)
    if not table_match:
        raise ValueError("Could not find SUMMARY TABLE in report")

    table_text = table_match.group(1)
    rows = []
    # Pattern: anchor on known stage name followed by latency float at end of line
    pat = re.compile(
        r'^\s{2}(.+?)\s{2,}(.+?)\s+'
        r'(' + '|'.join(KNOWN_STAGES) + r')'
        r'\s+([\d.]+)\s*$'
    )
    for line in table_text.strip().splitlines():
        if re.match(r'\s*(Category|─)', line):
            continue
        m = pat.match(line)
        if m:
            rows.append({
                "category": m.group(1).strip(),
                "question": m.group(2).strip(),
                "stage": m.group(3).strip(),
                "latency": float(m.group(4)),
            })
    return rows


def parse_actual_answers(content: str) -> dict[str, str]:
    """Extract per-question ACTUAL ANSWER blocks, keyed by question text."""
    answers = {}
    blocks = re.split(r'\n(?=\s*Q\d+\.)', content)
    for block in blocks:
        q_match = re.search(r'Q\d+\.\s*(.*?)\n', block)
        if not q_match:
            continue
        q_text = q_match.group(1).strip()
        ans_match = re.search(r'ACTUAL ANSWER:\s*\n(.*?)(?:\n\s*─|\Z)', block, re.DOTALL)
        if ans_match:
            answers[q_text] = ans_match.group(1).strip()
    return answers


def check_dirty_content(answer: str) -> bool:
    """Return True if an answer contains raw link syntax or blacklist content."""
    has_md_link = bool(re.search(r'\[.*?\]\(.*?\)', answer))
    has_raw_href = bool(re.search(r'<a\s+href', answer, re.IGNORECASE))
    has_link_leads_to = bool(re.search(r'leads to\s+/', answer))
    has_blacklist = bool(re.search(r'BlackList|De-empanelled|Debarred', answer, re.IGNORECASE))
    return has_md_link or has_raw_href or has_link_leads_to or has_blacklist

# ── Main ─────────────────────────────────────────────────────────────────────

def generate_comparison():
    baseline_path = Path("reports/benchmarks/baseline_20260721_1303.md")
    final_path = Path("reports/benchmarks/final_20260721.md")
    output_path = Path("reports/benchmarks/FULL_COMPARISON.md")

    base_content = baseline_path.read_text(encoding="utf-8")
    final_content = final_path.read_text(encoding="utf-8")

    base_rows = parse_summary_table(base_content)
    final_rows = parse_summary_table(final_content)

    base_answers = parse_actual_answers(base_content)
    final_answers = parse_actual_answers(final_content)

    # Build lookup for final rows by question text
    final_by_q = {}
    for r in final_rows:
        final_by_q[r["question"]] = r

    # ── Section 1: Per-Question Table ─────────────────────────────────────
    lines = [
        "# UPSDM RAG Chatbot — Full Optimization Evidence Pack",
        "",
        f"**Baseline**: `{baseline_path}`  ",
        f"**Final**: `{final_path}`  ",
        f"**Questions**: {len(base_rows)}",
        "",
        "---",
        "",
        "## 1. Per-Question Stage & Latency Comparison",
        "",
        "| # | Category | Question | Baseline Stage | Final Stage | Baseline (ms) | Final (ms) | Improvement |",
        "|---|---|---|---|---|---|---|---|",
    ]

    ambiguous_baseline = 0
    ambiguous_resolved = 0

    faiss_base_lats = []
    faiss_final_lats = []

    base_dirty = 0
    final_dirty = 0

    for idx, b in enumerate(base_rows, 1):
        f = final_by_q.get(b["question"], {})
        f_stage = f.get("stage", "???")
        f_lat = f.get("latency", 0.0)

        improvement = ((b["latency"] - f_lat) / b["latency"]) * 100 if b["latency"] > 0 else 0
        imp_str = f"+{improvement:.1f}%" if improvement >= 0 else f"{improvement:.1f}%"

        stage_col = f'`{b["stage"]}`' if b["stage"] == f_stage else f'`{b["stage"]}` → `{f_stage}`'

        short_q = b["question"][:55] + "…" if len(b["question"]) > 55 else b["question"]
        lines.append(
            f'| {idx} | {b["category"]} | {short_q} | `{b["stage"]}` | `{f_stage}` '
            f'| {b["latency"]:.2f} | {f_lat:.2f} | {imp_str} |'
        )

        # ── Tracking: AMBIGUOUS_MATCH ──
        if b["stage"] == "AMBIGUOUS_MATCH":
            ambiguous_baseline += 1
            if f_stage != "AMBIGUOUS_MATCH":
                ambiguous_resolved += 1

        # ── Tracking: FAISS_DIRECT latency ──
        if b["stage"] == "FAISS_DIRECT":
            faiss_base_lats.append(b["latency"])
        if f_stage == "FAISS_DIRECT":
            faiss_final_lats.append(f_lat)

        # ── Tracking: dirty content ──
        b_ans = base_answers.get(b["question"], "")
        f_ans = final_answers.get(b["question"], "")
        if b["stage"] == "FAISS_DIRECT" and check_dirty_content(b_ans):
            base_dirty += 1
        if f_stage == "FAISS_DIRECT" and check_dirty_content(f_ans):
            final_dirty += 1

    lines.append("")

    # ── Section 2: AMBIGUOUS_MATCH Resolution ─────────────────────────────
    lines += [
        "---",
        "",
        "## 2. AMBIGUOUS_MATCH Query Resolution",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Baseline AMBIGUOUS_MATCH questions | **{ambiguous_baseline}** |",
        f"| Resolved (no longer AMBIGUOUS_MATCH in final) | **{ambiguous_resolved}** |",
        f"| Still AMBIGUOUS_MATCH in final | **{ambiguous_baseline - ambiguous_resolved}** |",
        "",
    ]

    # ── Section 3: Dirty Content ──────────────────────────────────────────
    lines += [
        "---",
        "",
        "## 3. FAISS_DIRECT Answers with Raw Link Syntax / Blacklist Content",
        "",
        "| Metric | Baseline | Final |",
        "|---|---|---|",
        f"| FAISS_DIRECT answers containing link fragments or blacklist content | **{base_dirty}** | **{final_dirty}** |",
        "",
    ]

    # ── Section 4: FAISS_DIRECT Latency Stats ────────────────────────────
    b_avg = float(np.mean(faiss_base_lats)) if faiss_base_lats else 0
    b_p95 = float(np.percentile(faiss_base_lats, 95)) if faiss_base_lats else 0
    f_avg = float(np.mean(faiss_final_lats)) if faiss_final_lats else 0
    f_p95 = float(np.percentile(faiss_final_lats, 95)) if faiss_final_lats else 0

    avg_drop = b_avg - f_avg
    p95_drop = b_p95 - f_p95
    avg_pct = (avg_drop / b_avg) * 100 if b_avg else 0
    p95_pct = (p95_drop / b_p95) * 100 if b_p95 else 0

    lines += [
        "---",
        "",
        "## 4. FAISS_DIRECT Latency — Baseline vs Final",
        "",
        "| Metric | Baseline (ms) | Final (ms) | Drop (ms) | Speedup |",
        "|---|---|---|---|---|",
        f"| **Average** | {b_avg:.2f} | {f_avg:.2f} | −{avg_drop:.2f} | **{avg_pct:.1f}%** |",
        f"| **P95** | {b_p95:.2f} | {f_p95:.2f} | −{p95_drop:.2f} | **{p95_pct:.1f}%** |",
        f"| **Question count** | {len(faiss_base_lats)} | {len(faiss_final_lats)} | — | — |",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅  Written {output_path}  ({len(base_rows)} baseline × {len(final_rows)} final questions)")
    print()

    # ── Console summary ──────────────────────────────────────────────────
    print("═" * 70)
    print("  EVIDENCE PACK SUMMARY")
    print("═" * 70)
    print(f"  FAISS_DIRECT avg latency:   {b_avg:.1f} ms → {f_avg:.1f} ms  ({avg_pct:+.1f}% speedup)")
    print(f"  FAISS_DIRECT P95 latency:   {b_p95:.1f} ms → {f_p95:.1f} ms  ({p95_pct:+.1f}% speedup)")
    print(f"  AMBIGUOUS_MATCH resolved:   {ambiguous_resolved} / {ambiguous_baseline}")
    print(f"  Dirty FAISS answers:        {base_dirty} → {final_dirty}")
    print("═" * 70)


if __name__ == "__main__":
    generate_comparison()
