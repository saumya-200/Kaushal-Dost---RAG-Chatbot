import sys
import os
import time

import redis
import httpx
import asyncio
import subprocess
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
THRESHOLDS_PATH = BASE_DIR / "chatbot_config" / "thresholds.yaml"

async def send_request(client, query_idx):
# Updated to use existing Docker FastAPI server on port 8000
    url = "http://localhost:8000/chat"
    # No need to start a separate server; we assume Docker services are already running.

    
    t0 = time.time()
    try:
        # Use a high timeout for the requests that get queued and processed
        payload = {"message": f"Can we register candidate now query {query_idx}?", "history": []}
        r = await client.post(url, json=payload, timeout=240.0)
        latency = time.time() - t0
        return r.status_code, r.text, latency
    except Exception as e:
        latency = time.time() - t0
        return 999, str(e), latency

async def main():
    print("=" * 80)
    print("STARTING PIPELINE CONCURRENCY AND QUEUE LOAD TEST")
    print("=" * 80)

    # Load original thresholds
    with open(THRESHOLDS_PATH, "r") as f:
        original_yaml = f.read()
    # Apply test limits
    test_thresholds = yaml.safe_load(original_yaml)
    test_thresholds["llm"]["max_concurrent"] = 2
    test_thresholds["llm"]["queue_size"] = 1
    with open(THRESHOLDS_PATH, "w") as f:
        yaml.dump(test_thresholds, f)
    print("Temporarily set max_concurrent=2, queue_size=1 for load test.")

    # Ensure Redis cache is flushed for clean testing.
    try:
        redis_client = redis.Redis(host="localhost", port=6379)
        redis_client.flushdb()
        print("Flushed Redis semantic cache for clean concurrency testing.")
    except Exception as e:
        print(f"Warning: Could not flush Redis cache: {e}")

    # Fire 5 concurrent requests to the existing FastAPI server.
    print("Firing 5 concurrent LLM-stage requests simultaneously...")
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # 6. Process results
        success_count = 0
        busy_count = 0
        failed_count = 0
        
        for idx, (status, content, latency) in enumerate(results):
            print(f"Request {idx}: Status={status}, Latency={latency:.2f}s")
            if status == 200:
                success_count += 1
            elif status == 503:
                busy_count += 1
            else:
                failed_count += 1
                print(f"  Error Detail: {content[:150]}")

        print("\n" + "="*50)
        print("CONCURRENCY REPORT:")
        print(f"  HTTP 503 (Queue Busy):    {busy_count} (Expected: 2)")
        print(f"  Other Errors/Failures:     {failed_count} (Expected: 0)")
        print("="*50)
        
        # Asserts
        assert success_count == 3, f"Expected 3 successful processes, got {success_count}"
        assert busy_count == 2, f"Expected 2 queue rejections (HTTP 503), got {busy_count}"
        assert failed_count == 0, f"Expected 0 failed requests, got {failed_count}"
        print("\n🎉 CONCURRENCY CONTROLS AND QUEUE BOUNDS WORKED PERFECTLY! 🎉\n")
        
    # Restore original thresholds
    with open(THRESHOLDS_PATH, "w") as f:
        f.write(original_yaml)
    print("Restored original thresholds.yaml.")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as ae:
        print(f"\n❌ Load test assertion failed: {ae}\n")
        sys.exit(1)
    except Exception as ex:
        print(f"\n❌ Load test encountered an error: {ex}\n")
        sys.exit(1)
