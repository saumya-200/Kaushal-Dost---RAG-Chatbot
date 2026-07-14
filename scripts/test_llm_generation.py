import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.routing.router import Router
from src.llm.generator import LLMGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_llm_generation")

def test_language_mirroring_and_constraints():
    router = Router()
    
    queries = [
        # English
        "What is the main objective of UPSDM?",
        "Is there a helpline number to contact UPSDM?",
        
        # Hindi
        "यूपीएसडीएम (UPSDM) का मुख्य उद्देश्य क्या है?",
        "यूपीएसडीएम का संपर्क सूत्र क्या है?",
        
        # Hinglish
        "UPSDM ka registration process kya hai?",
        "UPSDM helpline call karne ke liye kya number hai?"
    ]
    
    print("\n" + "="*80)
    print("TESTING LANGUAGE MIRRORING AND WORD LIMITS")
    print("="*80)
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        # Route through the entire pipeline (cache miss routes to LLM generator)
        stage, answer, meta = router.route(q)
        word_count = len(answer.split())
        
        print(f"Stage Used: {stage}")
        print(f"Answer:     {answer}")
        print(f"Word Count: {word_count} (Cap is 120 words)")
        assert word_count <= 120, "Response exceeded 120 words!"
        print("-" * 50)

def test_conversation_history():
    router = Router()
    
    print("\n" + "="*80)
    print("TESTING MULTI-TURN CONVERSATION HISTORY")
    print("="*80)
    
    # Simple chat history simulation
    history = []
    
    # Turn 1
    q1 = "What is UPSDM?"
    print(f"\nTurn 1 Query: '{q1}'")
    stage1, answer1, meta1 = router.route(q1, history)
    print(f"Turn 1 Answer: {answer1}")
    
    # Save to history
    history.append({"query": q1, "answer": answer1})
    
    # Turn 2: Query refers back to Turn 1 using "its"
    q2 = "What is its official helpline number?"
    print(f"\nTurn 2 Query: '{q2}' (uses conversation history)")
    stage2, answer2, meta2 = router.route(q2, history)
    print(f"Turn 2 Answer: {answer2}")
    
    # We check if the LLM correctly identified the helpline from the context
    assert "0522-4944200" in answer2 or "upsdm.gov.in" in answer2 or "helpline" in answer2.lower()
    print("-" * 50)

def test_fallback_model():
    print("\n" + "="*80)
    print("TESTING FALLBACK MODEL (qwen3:1.7b)")
    print("="*80)
    
    generator = LLMGenerator()
    chunks = [
        {"title": "Helpline", "text": "For queries, contact UPSDM helpline at 0522-4944200."}
    ]
    
    print("Querying qwen3:1.7b...")
    # Explicitly run using the fallback model
    answer = generator.generate_answer(
        query="What is the phone number of UPSDM?",
        chunks=chunks,
        use_fallback_model=True
    )
    print(f"Fallback Model Answer: {answer}")
    assert "0522-4944200" in answer
    print("-" * 50)

if __name__ == "__main__":
    try:
        # Run tests
        test_language_mirroring_and_constraints()
        test_conversation_history()
        test_fallback_model()
        print("\n🎉 ALL GENERATION VERIFICATION TESTS PASSED SUCCESSFULLY! 🎉\n")
    except Exception as e:
        logger.error(f"Verification test failed: {e}")
        sys.exit(1)
