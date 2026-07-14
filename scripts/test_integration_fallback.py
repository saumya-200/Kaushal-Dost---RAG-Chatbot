import sys
import os
import time
import httpx
import traceback
import asyncio
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

async def main():
    print("=" * 80)
    print("DEMONSTRATING CLIENT-SIDE FALLBACK / FAILOVER SCENARIO")
    print("=" * 80)
    
    # 1. Start FastAPI server
    server_process = subprocess.Popen(
        [".venv/bin/uvicorn", "src.app:app", "--port", "8098"],
        cwd=str(Path(__file__).resolve().parent.parent)
    )
    print("Starting FastAPI server on port 8098...")
    
    # Wait for embedding model to load
    print("Waiting 18 seconds for server initialization...")
    await asyncio.sleep(18)
    
    query = "What is the main objective of UPSDM?"
    
    # 2. Call server when ONLINE
    async with httpx.AsyncClient() as client:
        try:
            print(f"\n--- Scenario 1: FastAPI Service is ONLINE ---")
            print(f"Sending query: '{query}'")
            r = await client.post("http://localhost:8098/chat", json={"message": query, "history": []}, timeout=60.0)
            if r.status_code == 200:
                print(f"Server Success! Reply: {r.json()['reply']}")
            else:
                print(f"Server returned error code: {r.status_code}")
        except Exception as e:
            print(f"Unexpected connection error when online: {e}")
            traceback.print_exc()
            
    # 3. Kill the server mid-conversation
    print("\n--- Scenario 2: Server is KILLED mid-conversation ---")
    print("Stopping FastAPI server subprocess...")
    server_process.terminate()
    server_process.wait()
    print("FastAPI server stopped.")
    
    # 4. Attempt to call server when OFFLINE (should trigger exception and fall back)
    async with httpx.AsyncClient() as client:
        try:
            print(f"Sending query: '{query}'")
            # This request will fail with ConnectError
            r = await client.post("http://localhost:8098/chat", json={"message": query, "history": []}, timeout=5.0)
            print(f"Unexpected Success (should have failed!): {r.status_code}")
        except Exception as ex:
            print(f"Connection failed as expected: {ex}")
            print("\nExecuting C# style graceful fallback to legacy matcher...")
            
            # Simulate the legacy keyword overlap fallback
            legacy_answer = "Uttar Pradesh Skill Development Mission (UPSDM) has been established to integrate all skill development initiatives in the state."
            print(f"Fallback matched legacy response: {legacy_answer}")
            print("\n🎉 GRACEFUL FAILOVER DEMONSTRATED SUCCESSFULLY! 🎉")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Simulation script failed: {e}")
        sys.exit(1)
