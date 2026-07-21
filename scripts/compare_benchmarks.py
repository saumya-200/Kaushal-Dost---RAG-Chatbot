#!/usr/bin/env python3
"""
Compare two benchmark markdown reports produced by test_question_bank.py.

Usage:
    python scripts/compare_benchmarks.py <old_benchmark.md> <new_benchmark.md>
"""

import sys
import re
import argparse
from pathlib import Path

# Stage hierarchy ranks (higher = better / more definitive response)
STAGE_RANKS = {
    "GREETING": 4,
    "STATIC_LOOKUP": 4,
    "FAISS_DIRECT": 4,
    "OUT_OF_SCOPE": 3,
    "AMBIGUOUS_MATCH": 2,
    "FALLBACK": 1,
    "LOW_CONFIDENCE": 1,
    "UNKNOWN": 0,
    "ERROR": 0
}


def parse_benchmark_report(filepath: str) -> list[dict]:
    """Parses a benchmark markdown report into structured question records."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match individual question result blocks
    pattern = r"Q(\d+)\.\s+(.*?)\n\s*─+\n\s*Stage:\s+(\S+)\n\s*Client Latency:\s+([\d\.]+)\s*ms\n\s*Server Latency:\s+([\d\.]+)\s*ms"
    matches = re.findall(pattern, content)

    records = []
    for idx_str, question_text, stage, client_lat_str, server_lat_str in matches:
        records.append({
            "index": int(idx_str),
            "question": question_text.strip(),
            "stage": stage.strip().upper(),
            "client_latency": float(client_lat_str),
            "server_latency": float(server_lat_str)
        })

    if not records:
        print(f"Warning: No valid question records found in {filepath}", file=sys.stderr)

    return records


def is_stage_regressed(old_stage: str, new_stage: str) -> bool:
    """
    Returns True if stage changed from a higher-quality stage to a worse stage
    (e.g., FAISS_DIRECT -> AMBIGUOUS_MATCH, or STATIC_LOOKUP -> AMBIGUOUS_MATCH).
    """
    old_s = old_stage.upper()
    new_s = new_stage.upper()

    if old_s == new_s:
        return False

    old_rank = STAGE_RANKS.get(old_s, 0)
    new_rank = STAGE_RANKS.get(new_s, 0)

    return new_rank < old_rank


def compare_benchmarks(old_path: str, new_path: str) -> bool:
    old_records = parse_benchmark_report(old_path)
    new_records = parse_benchmark_report(new_path)

    if not old_records or not new_records:
        print("Error: Could not load valid records from one or both files.", file=sys.stderr)
        sys.exit(1)

    # Index new records by question text
    new_map = {r["question"]: r for r in new_records}

    diff_rows = []
    total_latency_pct_sum = 0.0
    regressions_count = 0

    for global_idx, old_rec in enumerate(old_records, 1):
        q_text = old_rec["question"]
        new_rec = new_map.get(q_text)

        if not new_rec:
            # Fall back to index matching if question text differs slightly
            idx = old_rec["index"] - 1
            if idx < len(new_records):
                new_rec = new_records[idx]

        if not new_rec:
            print(f"Warning: Question missing in new report: '{q_text}'", file=sys.stderr)
            continue

        old_stage = old_rec["stage"]
        new_stage = new_rec["stage"]

        old_lat = old_rec["client_latency"]
        new_lat = new_rec["client_latency"]

        delta_ms = new_lat - old_lat
        delta_pct = ((new_lat - old_lat) / old_lat * 100.0) if old_lat > 0 else 0.0

        regressed = is_stage_regressed(old_stage, new_stage)
        if regressed:
            regressions_count += 1

        total_latency_pct_sum += delta_pct

        diff_rows.append({
            "index": global_idx,
            "question": q_text,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "old_lat": old_lat,
            "new_lat": new_lat,
            "delta_ms": delta_ms,
            "delta_pct": delta_pct,
            "regressed": regressed
        })


    # Print Diff Table
    sep = "=" * 125
    line_sep = "─" * 125
    print(sep)
    print("  BENCHMARK COMPARISON DIFF TABLE")
    print(sep)
    print(f"  Old Report: {old_path}")
    print(f"  New Report: {new_path}")
    print(sep)
    print(f"  {'#':<4} {'Question':<45} {'Stage (Old -> New)':<32} {'Old (ms)':>10} {'New (ms)':>10} {'Delta (ms)':>12} {'Delta (%)':>10} {'REGRESSED':>10}")
    print(f"  {'─'*4} {'─'*45} {'─'*32} {'─'*10} {'─'*10} {'─'*12} {'─'*10} {'─'*10}")

    for r in diff_rows:
        q_short = r['question'][:43] + ".." if len(r['question']) > 45 else r['question']
        stage_str = f"{r['old_stage']} -> {r['new_stage']}" if r['old_stage'] != r['new_stage'] else r['old_stage']
        delta_ms_str = f"{r['delta_ms']:+.2f}"
        delta_pct_str = f"{r['delta_pct']:+.1f}%"
        reg_str = "TRUE" if r['regressed'] else "False"

        print(f"  {r['index']:<4} {q_short:<45} {stage_str:<32} {r['old_lat']:>10.2f} {r['new_lat']:>10.2f} {delta_ms_str:>12} {delta_pct_str:>10} {reg_str:>10}")

    avg_latency_pct = total_latency_pct_sum / max(len(diff_rows), 1)

    print(sep)
    print(f"SUMMARY: Total Questions: {len(diff_rows)} | Avg Latency Delta: {avg_latency_pct:+.2f}% | STAGE_REGRESSED Count: {regressions_count}")
    print(sep)

    return regressions_count > 0


def main():
    parser = argparse.ArgumentParser(description="Compare two benchmark markdown reports for stage regressions and latency deltas.")
    parser.add_argument("old_report", type=str, help="Path to old benchmark markdown report")
    parser.add_argument("new_report", type=str, help="Path to new benchmark markdown report")

    args = parser.parse_args()

    has_regressions = compare_benchmarks(args.old_report, args.new_report)

    if has_regressions:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
