import sys
from pathlib import Path
import time
import asyncio

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.routing.router import Router

def format_result(query: str, stage: str, response: str, latency: float, meta: dict):
    print(f"Query:   '{query}'")
    print(f"Stage:   {stage}")
    print(f"Latency: {latency * 1000:.2f} ms")
    if "top_score" in meta:
        print(f"Score:   {meta['top_score']:.4f}")
    if "cached_query_match" in meta:
        print(f"Match:   '{meta['cached_query_match']}'")
    print(f"Answer:  {response[:180]}...")
    print("-" * 50)

async def main():
    print("Initializing Router...")
    router = Router()
    print("=" * 50)
    
    # Clear Redis db for a clean demo run
    if router.use_cache:
        router.redis_client.flushdb()
        router.cached_queries = []
        router.cached_embeddings = []
        print("Redis semantic cache flushed for clean demo.")
    else:
        print("Warning: Redis cache is not active!")
        
    print("=" * 50)
    print("DEMONSTRATING PIPELINE STAGES")
    print("=" * 50)
    
    # 1. Greeting Router
    q1 = "Hello there!"
    t0 = time.time()
    stage, answer, meta = await router.route(q1)
    format_result(q1, stage, answer, time.time() - t0, meta)
    
    # 2. Main Search & LLM (Cache Miss)
    q2 = "What is UPSDM?"
    t0 = time.time()
    stage, answer, meta = await router.route(q2)
    format_result(q2, stage, answer, time.time() - t0, meta)
    
    # 3. Exact query repeated (Cache Hit)
    t0 = time.time()
    stage, answer, meta = await router.route(q2)
    format_result(q2, stage, answer, time.time() - t0, meta)
    
    # 4. Paraphrase query (Semantic Cache Hit)
    q3 = "What is the meaning of UPSDM?"
    t0 = time.time()
    stage, answer, meta = await router.route(q3)
    format_result(q3, stage, answer, time.time() - t0, meta)
    
    # 5. Low confidence query (Fallback)
    q4 = "Who is the Prime Minister of Australia?"
    t0 = time.time()
    stage, answer, meta = await router.route(q4)
    format_result(q4, stage, answer, time.time() - t0, meta)

if __name__ == "__main__":
    asyncio.run(main())

