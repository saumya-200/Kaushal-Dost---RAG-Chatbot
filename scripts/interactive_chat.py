#!/usr/bin/env python3
"""
Interactive terminal client to test the UPSDM RAG pipeline.
Queries the running FastAPI container at http://localhost:8000/chat.
"""
import sys
import json
import time
import urllib.request
import urllib.error

# ANSI Color codes for beautiful UI
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

API_URL = "http://localhost:8000/chat"
HEALTH_URL = "http://localhost:8000/health"

def check_health():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return True, data.get("model", "unknown")
    except Exception:
        pass
    return False, None

def print_header():
    print(f"{CYAN}{BOLD}================================================================{RESET}")
    print(f"{CYAN}{BOLD}               🤖 UPSDM RAG Pipeline Interactive Chat 🤖          {RESET}")
    print(f"{CYAN}{BOLD}================================================================{RESET}")
    print(f"Type your questions below to test the RAG pipeline routing.")
    print(f"Special Commands:")
    print(f"  {YELLOW}/clear{RESET} - Clear chat history (starts a fresh conversation)")
    print(f"  {YELLOW}/exit{RESET} or {YELLOW}/quit{RESET} - Close this chat session\n")

def query_chat_api(message, history):
    payload = {
        "message": message,
        "history": history
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            latency_seconds = time.time() - t0
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data, latency_seconds
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode())
            detail = err_data.get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": f"HTTP {e.code}: {detail}"}, 0
    except Exception as e:
        return {"error": f"Connection failed: {e}"}, 0

def format_stage(stage):
    stages = {
        "greeting": f"{GREEN}Greeting Router (Instant Template Response){RESET}",
        "semantic_cache": f"{CYAN}Semantic Cache (Redis Hit){RESET}",
        "faiss_direct": f"{BLUE}FAISS Direct Route (Exact Chunk Match){RESET}",
        "llm_generation": f"{MAGENTA}LLM Generation Route (Synthesis via Qwen3){RESET}",
        "fallback": f"{YELLOW}Fallback Route (Low Confidence / Out of Scope){RESET}"
    }
    return stages.get(stage, f"{RED}{stage}{RESET}")

def main():
    # 1. Verify API is online
    online, model = check_health()
    if not online:
        print(f"{RED}{BOLD}Error: UPSDM Chatbot API is offline or model setup is incomplete!{RESET}")
        print(f"Please ensure your Docker containers are running and model setup finished:")
        print(f"  1. Run: {BOLD}docker compose up -d{RESET}")
        print(f"  2. Monitor model pull: {BOLD}docker logs -f upsdm-chatbot-model-setup{RESET}")
        sys.exit(1)
        
    print_header()
    print(f"{GREEN}Connected to API successfully! (Active Model: {BOLD}{model}{RESET})\n")
    
    history = []
    
    while True:
        try:
            # Get user input
            query = input(f"{BOLD}You:{RESET} ").strip()
            if not query:
                continue
                
            # Handle commands
            if query.lower() in ("/exit", "/quit"):
                print(f"\n{YELLOW}Goodbye!{RESET}")
                break
            elif query.lower() == "/clear":
                history = []
                print(f"\n{YELLOW}🧹 Chat history cleared.{RESET}\n")
                continue
                
            print(f"{GRAY}Thinking...{RESET}", end="\r")
            
            # Call API
            response, latency = query_chat_api(query, history)
            
            # Clear "Thinking..." line
            print(" " * 20, end="\r")
            
            if "error" in response:
                print(f"{RED}{BOLD}API Error:{RESET} {response['error']}\n")
                continue
                
            reply = response.get("reply", "")
            stage = response.get("stage", "unknown")
            source_ids = response.get("source_ids", [])
            latency_ms = response.get("latency_ms", latency * 1000)
            
            # Print response
            print(f"{BOLD}Bot:{RESET} {reply}")
            print(f"{GRAY}[Metadata]{RESET}")
            print(f"  - Route Stage: {format_stage(stage)}")
            print(f"  - Latency:     {latency_ms:.2f} ms")
            if source_ids:
                print(f"  - Sources:     {', '.join(source_ids)}")
            print()
            
            # Update history for next turns
            history.append({
                "query": query,
                "answer": reply
            })
            
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Goodbye!{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}An unexpected error occurred: {e}{RESET}\n")

if __name__ == "__main__":
    main()
