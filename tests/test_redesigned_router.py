import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from src.routing.router import Router
from src.routing.persona.persona_classifier import PersonaClassifier
from src.routing.intent.intent_classifier import IntentClassifier
from src.routing.template_matching.template_matcher import TemplateMatcher
from src.routing.extractive.extractive_generator import ExtractiveGenerator
from src.routing.sanitizer.sanitizer import ResponseSanitizer
from src.routing.greetings.greeting_detector import GreetingDetector

@pytest.fixture
def router():
    # Use patch to mock Redis connection to avoid dependency on a running Redis instance
    with patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        yield Router()

def test_greeting_detector():
    detector = GreetingDetector()
    assert detector.is_greeting("hello") is True
    assert detector.is_greeting("Namaste") is True
    assert detector.is_greeting("नमस्ते") is True
    assert detector.is_greeting("what is course eligibility") is False
    
    # Language match response
    assert "Namaste" in detector.get_greeting_response("Namaste", "hi") or "नमस्ते" in detector.get_greeting_response("Namaste", "hi")
    assert "Hello" in detector.get_greeting_response("Hello", "en") or "Hi" in detector.get_greeting_response("Hello", "en")

def test_persona_classifier(router):
    classifier = PersonaClassifier(router.embedder)
    
    # Student persona query containing keywords
    q_student = "how to enroll in a course as a student and get course list"
    q_emb = router.embedder.embed_query(q_student)
    persona, score = classifier.classify(q_student, q_emb)
    assert persona == "Student"
    
    # Training Partner query containing keywords
    q_tp = "what are the empanelment and infrastructure requirements for a training centre"
    q_emb_tp = router.embedder.embed_query(q_tp)
    persona_tp, score_tp = classifier.classify(q_tp, q_emb_tp)
    assert persona_tp == "Training Partner"

def test_intent_classifier(router):
    classifier = IntentClassifier(router.embedder)
    
    # Student query
    q = "how to enroll in courses"
    q_emb = router.embedder.embed_query(q)
    intent, score = classifier.classify(q, q_emb, "Student")
    assert intent == "Enroll"
    
    # Training Partner query
    q_tp = "training center infrastructure requirements"
    q_emb_tp = router.embedder.embed_query(q_tp)
    intent_tp, score_tp = classifier.classify(q_tp, q_emb_tp, "Training Partner")
    assert intent_tp == "Infrastructure"

def test_template_matcher(router):
    matcher = TemplateMatcher(router.embedder)
    
    # Match success
    q = "what is the helpline number"
    q_emb = router.embedder.embed_query(q)
    status, answer, meta = matcher.match(q, q_emb, "General Public", "Helpline", "en")
    assert status == "success"
    assert "0522-4944200" in answer
    
    # Ambiguous match simulation
    # Mocking templates with extremely close scores
    with patch.object(matcher, "entries", [
        {"intent": "Registration", "persona": "Training Partner", "answer": "TP registration details.", "aliases": ["register"]},
        {"intent": "Enroll", "persona": "Student", "answer": "Student registration details.", "aliases": ["register"]}
    ]):
        matcher.template_embeddings = []
        for entry in matcher.entries:
            for alias in entry.get("aliases", []):
                norm_alias = matcher._normalize(alias)
                emb = matcher.embedder.embed_query(alias)
                matcher.template_embeddings.append({
                    "entry": entry,
                    "alias": alias,
                    "norm_alias": norm_alias,
                    "embedding": emb.flatten()
                })
        # Match using same alias to force equal score
        q_amb = "register"
        q_emb_amb = matcher.embedder.embed_query(q_amb)
        status_amb, _, _ = matcher.match(q_amb, q_emb_amb, "Unknown", "General", "en")
        assert status_amb == "ambiguous"

def test_extractive_generator(router):
    generator = ExtractiveGenerator(router.embedder)
    
    # High confidence evaluation
    results = [
        {
            "chunk_id": "chunk_001",
            "source_url": "https://upsdm.gov.in/Home/FAQ",
            "text": "The helpline number is 0522-4944200. Nodal offices are located in Lucknow. Candidates can register online.",
            "score": 0.95
        },
        {
            "chunk_id": "chunk_002",
            "source_url": "https://upsdm.gov.in/Home/Downloads",
            "text": "For training centers search, click Search Centers on home page. Map displays list of locations.",
            "score": 0.88
        }
    ]
    
    level, score, signals = generator.compute_retrieval_confidence(results)
    assert level == "HIGH"
    
    # Extractive generation
    query = "what is the helpline number of upsdm?"
    q_emb = router.embedder.embed_query(query)
    answer = generator.generate_extractive_answer(query, q_emb, results)
    
    assert "0522-4944200" in answer
    assert "Source: upsdm.gov.in" in answer

def test_sanitizer():
    sanitizer = ResponseSanitizer()
    dirty_text = "[Draft RAG Response] [Debug: some metadata] The answer is here. <!-- comment -->"
    clean_text = sanitizer.sanitize(dirty_text)
    assert clean_text == "The answer is here."
