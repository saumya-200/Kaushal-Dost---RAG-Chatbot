"""
Merge supplemental seed data into the main chunks.jsonl file.

This script handles JS-rendered pages whose content cannot be extracted
by Scrapy. The seed data is curated from publicly available information
about UPSDM (FAQ page content, official documents, etc.).
"""
import sys
import json
import hashlib
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))


def merge_supplements(chunks_file: str, supplements_file: str):
    """Append seed supplement entries to chunks.jsonl, avoiding duplicates."""
    
    # Load existing chunk source_ids for dedup
    existing_sources = set()
    existing_chunk_ids = set()
    if Path(chunks_file).exists():
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line)
                    existing_chunk_ids.add(chunk.get('chunk_id', ''))
    
    # Read supplements
    supplements = []
    with open(supplements_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                supplements.append(json.loads(line))
    
    # Append new entries
    added = 0
    with open(chunks_file, 'a', encoding='utf-8') as f:
        for supp in supplements:
            chunk_id = supp.get('chunk_id', '')
            if chunk_id and chunk_id not in existing_chunk_ids:
                # Format as a proper chunk entry
                chunk = {
                    "chunk_id": chunk_id,
                    "source_url": supp["source_url"],
                    "source_id": supp["source_url"].replace("https://", ""),
                    "text": supp["text"],
                    "language": supp.get("language", "en"),
                    "chunk_index": 0,
                    "hash": hashlib.sha256(supp["text"].encode()).hexdigest(),
                    "is_seed": True
                }
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                existing_chunk_ids.add(chunk_id)
                added += 1
                print(f"  Added: {chunk_id} ({supp['source_url']})")
    
    print(f"\nMerge complete. Added {added} seed chunks. "
          f"Total chunks now: {len(existing_chunk_ids)}")


if __name__ == "__main__":
    chunks_file = "data/chunks.jsonl"
    supplements_file = "data/seed_supplements.jsonl"
    
    if not Path(supplements_file).exists():
        print(f"Error: {supplements_file} not found.")
        sys.exit(1)
    
    merge_supplements(chunks_file, supplements_file)
