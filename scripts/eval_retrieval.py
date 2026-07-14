import sys
# Force UTF-8 stdout to prevent Windows console UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import csv
import logging
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger("eval")

def main():
    eval_file = "tests/eval_set.csv"
    if not Path(eval_file).exists():
        logger.error(f"{eval_file} not found.")
        return
        
    try:
        index = FAISSIndex()
        index.load()
    except FileNotFoundError:
        logger.error("FAISS index not found. Run scripts/build_index.py first.")
        return
        
    embedder = Embedder()
    
    # Metrics
    total = 0
    top1_hits = 0
    top3_hits = 0
    
    lang_stats = defaultdict(lambda: {"total": 0, "hits": 0})
    cat_stats = defaultdict(lambda: {"total": 0, "hits": 0})
    failures = []
    
    logger.info("Running evaluation...")
    
    with open(eval_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['question']
            expected = row['expected_source_id']
            lang = row['language']
            cat = row['category']
            
            # Embed and search
            q_emb = embedder.embed_query(query)
            results = index.search(q_emb, top_k=3)
            
            result_sources = [r['source_id'] for r in results]
            
            # Normalize URLs for matching (ignore www. and trailing slashes)
            def normalize_id(s: str) -> str:
                return s.lower().replace("www.", "").strip("/")
                
            expected_norm = normalize_id(expected)
            result_sources_norm = [normalize_id(s) for s in result_sources]
            
            # Check hits
            hit1 = len(result_sources_norm) > 0 and result_sources_norm[0] == expected_norm
            hit3 = expected_norm in result_sources_norm
            
            total += 1
            if hit1:
                top1_hits += 1
            if hit3:
                top3_hits += 1
                lang_stats[lang]["hits"] += 1
                cat_stats[cat]["hits"] += 1
            else:
                failures.append({
                    "query": query,
                    "expected": expected,
                    "got": result_sources
                })
                
            lang_stats[lang]["total"] += 1
            cat_stats[cat]["total"] += 1
            
    # Print report
    print("\n" + "="*50)
    print("RETRIEVAL EVALUATION REPORT")
    print("="*50)
    print(f"Overall Top-1 Accuracy: {top1_hits/total*100:.1f}%")
    print(f"Overall Top-3 Accuracy: {top3_hits/total*100:.1f}% (Target: >=85%)")
    print("-" * 50)
    
    print("Accuracy by Language (Top-3):")
    for lang, stat in lang_stats.items():
        if stat["total"] > 0:
            print(f"  - {lang}: {stat['hits']/stat['total']*100:.1f}% ({stat['hits']}/{stat['total']})")
            
    print("-" * 50)
    print("Accuracy by Category (Top-3):")
    for cat, stat in cat_stats.items():
        if stat["total"] > 0:
            print(f"  - {cat}: {stat['hits']/stat['total']*100:.1f}% ({stat['hits']}/{stat['total']})")
            
    if failures:
        print("-" * 50)
        print("Failed Queries (Missing from Top-3):")
        for fail in failures:
            print(f"  Q: {fail['query']}")
            print(f"     Expected: {fail['expected']}")
            print(f"     Got:      {fail['got']}\n")

if __name__ == "__main__":
    main()
