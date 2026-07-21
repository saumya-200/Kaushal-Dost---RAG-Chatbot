import re
import numpy as np
from src.config import load_config
from src.embeddings.embed import Embedder

class PersonaClassifier:
    """
    Classifies queries into one of the supported personas:
    Student, Training Partner, Industrial Partner, Assessment Agency, General Public, Unknown.
    
    Combines rule-based keyword matching and embedding similarity for high precision.
    """
    def __init__(self, embedder: Embedder = None):
        self.config = load_config()
        self.embedder = embedder if embedder is not None else Embedder()
        
        # Load thresholds from config
        routing_config = self.config.routing_config
        self.persona_threshold = routing_config.get("persona_threshold", 0.50)
        
        # Keywords definition
        self.persona_keywords = {
            "Student": {
                "course", "courses", "admission", "enroll", "enrollment", "placement", 
                "placements", "certificate", "candidate", "candidates", "student", 
                "fee", "fees", "eligibility", "job", "jobs", "apply", "scholarship", 
                "training", "placement assistance", "कोर्स", "दाखिला", "प्रमाण पत्र"
            },
            "Training Partner": {
                "tp", "training partner", "training partners", "training centre", 
                "training center", "training centers", "empanelment", "empanelled", 
                "attendance", "batch", "batches", "reimbursement", "affiliation", 
                "institute", "institutes", "franchise", "target allocation", "smart portal",
                "center registration", "register center", "infrastructure requirements",
                "ट्रेनिंग पार्टनर", "केंद्र पंजीकरण"
            },
            "Industrial Partner": {
                "industry", "industrial", "company", "companies", "placement partner", 
                "placement partners", "csr", "recruitment", "hiring", "employer", 
                "employers", "mou", "collaboration", "industry partner", "placement partnership",
                "corporate", "recruit", "प्लेसमेंट पार्टनर", "कंपनी"
            },
            "Assessment Agency": {
                "assessment", "assessments", "exam", "exams", "evaluator", "evaluators", 
                "assessor", "assessors", "testing agency", "assessment agency", "ab",
                "मूल्यांकन", "परीक्षा"
            },
            "General Public": {
                "helpline", "contact", "email", "website", "address", "location", 
                "office", "spmu", "dpmu", "downloads", "circular", "circulars",
                "हेल्पलाइन", "वेबसाइट"
            }
        }
        
        # Strong overrides (if query contains these words, strongly bias persona)
        self.strong_rules = {
            "Training Partner": {"empanelment", "empanelled", "tp grading", "de-empanelled", "smart portal"},
            "Industrial Partner": {"csr funding", "placement partner", "placement partnership"},
            "Assessment Agency": {"assessment agency", "evaluator guidelines"}
        }

        # Exemplars for semantic matching
        self.exemplars = {
            "Student": [
                "how do I enroll for skill training",
                "do you provide placement assistance for candidates",
                "course list and eligibility details",
                "where can I find my certificate",
                "what is student registration process"
            ],
            "Training Partner": [
                "how to register my institute or training center",
                "what are the infrastructure requirements for empanelment",
                "training partner grading and targets allocation",
                "how to upload batch attendance on portal",
                "process for training partner reimbursement"
            ],
            "Industrial Partner": [
                "how can companies collaborate as placement partners",
                "industry recruitment and hiring partnership",
                "corporate social responsibility CSR skill development collaboration"
            ],
            "Assessment Agency": [
                "register as an assessment agency or awarding body",
                "evaluator and assessor empanelment guidelines",
                "examination schedule and testing center criteria"
            ],
            "General Public": [
                "what is the official helpline phone number and email ID",
                "contact details for State Project Management Unit SPMU",
                "official upsdm website link and downloads portal"
            ]
        }
        
        # Pre-embed exemplars for fast CPU comparison
        self.exemplar_embeddings = {}
        for persona, sentences in self.exemplars.items():
            embeddings = [self.embedder.embed_query(s) for s in sentences]
            self.exemplar_embeddings[persona] = np.array(embeddings, dtype="float32")

    def _normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r'[?!.,;:\'"()\[\]{}]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def classify(self, query: str, query_embedding: np.ndarray) -> tuple[str, float]:
        """
        Classifies the persona based on multiple signals.
        Returns: (detected_persona, confidence_score)
        """
        normalized = self._normalize(query)
        words = set(normalized.split())
        
        scores = {}
        
        # 1. Check strong rule overrides (high weight / absolute trigger)
        for persona, triggers in self.strong_rules.items():
            if any(trigger in normalized for trigger in triggers):
                return persona, 1.0
        
        for persona in self.exemplar_embeddings.keys():
            # Signal A: Keyword match count (normalized by log of keyword list length)
            kw_matches = sum(1 for kw in self.persona_keywords[persona] if kw in normalized)
            # Add partial match for words in query
            word_matches = len(words & self.persona_keywords[persona])
            kw_score = min(max(kw_matches, word_matches) / 3.0, 1.0) # max of 3 matches = 1.0
            
            # Signal B: Semantic similarity (cosine similarity of query against pre-embedded exemplars)
            similarities = np.dot(self.exemplar_embeddings[persona], query_embedding.flatten())
            semantic_score = float(np.max(similarities))
            
            # Weighted combine
            # If no keywords match, reduce semantic weight to avoid false positive embeddings
            if max(kw_matches, word_matches) == 0:
                score = 0.3 * semantic_score
            else:
                score = 0.4 * kw_score + 0.6 * semantic_score
                
            scores[persona] = score
            
        best_persona = max(scores, key=scores.get)
        best_score = scores[best_persona]
        
        if best_score >= self.persona_threshold:
            return best_persona, round(best_score, 4)
            
        return "Unknown", round(best_score, 4)
