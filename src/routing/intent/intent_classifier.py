import re
import yaml
import logging
from pathlib import Path
import numpy as np
from src.config import load_config
from src.embeddings.embed import Embedder

logger = logging.getLogger(__name__)

class IntentClassifier:
    """
    Classifies the specific intent of a query within the context of the detected persona.
    Includes UP location gazetteer matching for Locator intent queries.
    """
    def __init__(self, embedder: Embedder = None):
        self.config = load_config()
        self.embedder = embedder if embedder is not None else Embedder()
        
        # Load thresholds
        routing_config = self.config.routing_config
        self.intent_threshold = routing_config.get("intent_threshold", 0.50)
        
        # Load UP Locations gazetteer
        locations_file = Path("chatbot_config/up_locations.yaml")
        self.up_locations = set()
        if locations_file.exists():
            try:
                with open(locations_file, 'r', encoding='utf-8') as f:
                    loc_data = yaml.safe_load(f)
                    if loc_data and "locations" in loc_data:
                        self.up_locations = set(l.strip().lower() for l in loc_data["locations"])
            except Exception as e:
                logger.warning(f"Failed to load UP locations gazetteer: {e}")
        
        # Intent keywords per persona
        self.intent_keywords = {
            "Student": {
                "Enroll": {"enroll", "register", "admission", "apply", "sign up", "join", "course list", "registration", "प्रवेश", "दाखिला", "कोर्स"},
                "Certificate": {"certificate", "marksheet", "result", "passing", "degree", "प्रमाण पत्र", "सर्टिफिकेट"},
                "Placement": {"placement", "job", "recruitment", "hiring", "salary", "placement assistance", "रोजगार", "नौकरी"},
                "Eligibility": {"eligibility", "age limit", "criteria", "qualifications", "documents required", "fees", "fee", "पात्रता", "उम्र सीमा"},
                "Training Center": {"training center", "training centre", "search center", "find center", "center near me", "केंद्र", "सेंटर"},
                "Locator": {"locator", "location", "center", "centre", "training center", "training centre", "search center", "search centre", "list of", "near me", "nearby", "find center", "locate", "where is", "district", "केंद्र", "सेंटर"},
                "Process": {"process", "claim reimbursement", "empanelment process", "reimbursement claim", "registration process", "procedure", "how to claim", "reimbursement", "empanelment", "claim", "claims", "प्रक्रिया", "दावा"}
            },
            "Training Partner": {
                "Registration": {"register", "register institute", "register center", "tp registration", "rfp", "apply tp", "apply as tp", "पंजीकरण"},
                "Infrastructure": {"infrastructure", "classroom size", "lab equipment", "space", "building", "requirements", "लैब"},
                "Attendance": {"attendance", "biometric", "ae bas", "mobile app", "live capture", "live capture app", "उपस्थिति"},
                "Reimbursement": {"reimbursement", "payment", "payout", "fund release", "cost structure", "claims", "भुगतान"},
                "Affiliation": {"affiliation", "grading", "empanelment", "de-empanelled", "blacklisted", "deempanelled", "black list"},
                "Locator": {"locator", "location", "center", "centre", "training center", "training centre", "search center", "find center", "locate", "district"},
                "Process": {"process", "claim reimbursement", "empanelment process", "reimbursement claim", "registration process", "procedure", "how to claim", "application process", "reimbursement", "empanelment", "claim", "claims", "प्रक्रिया", "दावा"}
            },
            "Industrial Partner": {
                "Placement Partnership": {"placement partner", "placement partnership", "mou", "tie up", "companies collaborate"},
                "CSR": {"csr", "corporate social responsibility", "funding", "csr project"},
                "Hiring": {"hiring", "recruitment", "employer registration", "recruit candidates", "jobs", "need candidates"},
                "Skill Development": {"skill development", "skilling initiative", "corporate training", "upskill", "customize curriculum", "training curriculum", "curriculum customization", "customize the training curriculum"},
                "Locator": {"locator", "location", "center", "centre", "training center", "training centre", "locate", "district"},
                "Process": {"process", "empanelment process", "partnership process", "procedure", "how to partner", "registration process", "mou process", "reimbursement", "empanelment", "claim", "claims", "प्रक्रिया"}
            },
            "Assessment Agency": {
                "Empanelment": {"register agency", "apply assessment agency", "empanelment", "apply as assessment"},
                "Assessment": {"assessment", "exam", "assessor", "evaluator", "testing guidelines", "evaluation"},
                "Locator": {"locator", "location", "center", "centre", "training center", "locate", "district"},
                "Process": {"process", "empanelment process", "procedure", "reimbursement", "empanelment", "claim", "claims", "प्रक्रिया"}
            },
            "General Public": {
                "Helpline": {"helpline", "phone number", "contact", "email", "support", "हेल्पलाइन"},
                "Website": {"website", "portal", "url", "link", "downloads", "circular", "वेबसाइट"},
                "SPMU": {"spmu", "state", "nodal", "head office"},
                "DPMU": {"dpmu", "district", "district office"},
                "Locator": {"locator", "location", "center", "centre", "training center", "training centre", "search center", "find center", "list of", "near me", "nearby", "locate", "where is", "district", "केंद्र", "सेंटर"},
                "Process": {"process", "claim reimbursement", "empanelment process", "reimbursement claim", "registration process", "procedure", "reimbursement", "empanelment", "claim", "claims", "प्रक्रिया"}
            }
        }
        
        # Exemplar queries per intent
        self.intent_exemplars = {
            "Student": {
                "Enroll": ["how do I enroll in course registration", "apply for training classes", "start admission process list"],
                "Certificate": ["download course certificate marksheet passing degree", "when will I get certificate", "certificate result copy"],
                "Placement": ["does upsdm provide placement assistance jobs placement", "job opportunities salary package placement support", "placement helper post training"],
                "Eligibility": ["eligibility criteria age limit qualifications documents fee", "what is minimum age limit course fees", "is course training free candidates eligibility"],
                "Training Center": ["search training centers list near me find center map location", "where is nearest training center institute center"],
                "Locator": ["where can I find the list of training centers in Lucknow", "training center near me in Kanpur", "search training centers list in Varanasi Agra Lucknow", "find skill development training center near Prayagraj"],
                "Process": ["how do I claim reimbursement for candidate training process", "what is the empanelment process for new training programs procedure"]
            },
            "Training Partner": {
                "Registration": ["how do I register my institute as training partner rfp", "register training center rfp registration application"],
                "Infrastructure": ["infrastructure requirements classroom size lab equipment center space", "lab details classroom capacity spacing"],
                "Attendance": ["biometric attendance tracking system mobile app live capture app", "how to upload attendance batch live capture"],
                "Reimbursement": ["payout reimbursement process claims cost structure", "when will training partner get reimbursement payments"],
                "Affiliation": ["tp grading guidelines grading report empanelment status", "list of de-empanelled blacklisted training partners grading"],
                "Locator": ["where can I find list of training centers in Lucknow Kanpur Agra", "find training center location in district"],
                "Process": ["how do I claim reimbursement for candidate training process", "what is the empanelment process for new training programs procedure", "reimbursement claim process for training partners", "empanelment registration procedure for new training partners"]
            },
            "Industrial Partner": {
                "Placement Partnership": ["companies collaborate as placement partners placement partnership mou", "how can industry partner join placement partner"],
                "CSR": ["corporate social responsibility csr funding skill project", "csr collaboration sponsorship skill development"],
                "Hiring": ["employer registration recruit training candidates hiring", "recruitment options to hire certified student candidates"],
                "Locator": ["where can I find list of training centers in Lucknow Kanpur Agra", "find training center location in district"],
                "Process": ["what is the empanelment process for industrial partner mou", "how to apply for industry partnership process procedure"]
            },
            "Assessment Agency": {
                "Empanelment": ["register as assessment agency empanelment application process", "awarding body empanelment assessment agency registration"],
                "Assessment": ["assessor evaluator certification exam testing guidelines", "assessment evaluation criteria guidelines for assessor"],
                "Locator": ["where can I find list of training centers in Lucknow Kanpur Agra", "find training center location in district"],
                "Process": ["what is the empanelment process for assessment agency", "reimbursement claim process for assessment agency"]
            },
            "General Public": {
                "Helpline": ["contact helpline phone number email id customer care", "helpline number for enquiries"],
                "Website": ["website link portal url downloads forms guidelines", "downloads circulars guidelines website portal"],
                "SPMU": ["spmu nodal officer head office contact address", "state project management unit spmu phone email"],
                "DPMU": ["dpmu district contact address list details", "district project management unit office number"],
                "Locator": ["where can I find the list of training centers in Lucknow", "training center near me in Kanpur", "search training centers list in Varanasi Agra Lucknow", "find skill development training center near Prayagraj"],
                "Process": ["how do I claim reimbursement for candidate training process", "what is the empanelment process for new training programs procedure"]
            }
        }
        
        # Pre-embed intent exemplars
        self.exemplar_embeddings = {}
        for persona, intent_map in self.intent_exemplars.items():
            self.exemplar_embeddings[persona] = {}
            for intent, sentences in intent_map.items():
                embeddings = [self.embedder.embed_query(s) for s in sentences]
                self.exemplar_embeddings[persona][intent] = np.array(embeddings, dtype="float32")

    def _normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r'[?!.,;:\'"()\[\]{}]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def detect_location(self, query: str) -> str | None:
        """
        Checks query tokens/phrases against the UP locations gazetteer.
        Returns capitalized location name if matched (e.g. 'Lucknow'), else None.
        """
        if not self.up_locations:
            return None
        norm_query = self._normalize(query)
        words = set(norm_query.split())
        
        # Check multi-word location phrases first (e.g., 'greater noida', 'gautam buddha nagar')
        for loc in sorted(self.up_locations, key=len, reverse=True):
            if " " in loc and loc in norm_query:
                return loc.title()
                
        # Check single-word location tokens
        for w in words:
            if w in self.up_locations:
                return w.capitalize()
                
        return None

    def classify(self, query: str, query_embedding: np.ndarray, persona: str) -> tuple[str, float, str | None]:
        """
        Classifies intent within the detected persona namespace.
        Detects UP locations and boosts Locator intent if location + search action keywords match.
        Returns: (best_intent, best_score, detected_location)
        """
        detected_loc = self.detect_location(query)
        
        # Map target persona to keywords/exemplars dictionary
        target_persona = persona if persona in self.intent_keywords else "General Public"
        
        normalized = self._normalize(query)
        words = set(normalized.split())
        
        scores = {}
        
        intent_map = self.exemplar_embeddings.get(target_persona, {})
        keywords_map = self.intent_keywords.get(target_persona, {})
        
        for intent in intent_map.keys():
            # Signal A: Keyword matching
            keywords = keywords_map.get(intent, set())
            kw_matches = sum(1 for kw in keywords if kw in normalized)
            word_matches = len(words & keywords)
            kw_score = min(max(kw_matches, word_matches) / 2.0, 1.0) # max of 2 matches = 1.0
            
            # Signal B: Semantic similarity
            similarities = np.dot(intent_map[intent], query_embedding.flatten())
            semantic_score = float(np.max(similarities))
            
            # Combine signals
            if max(kw_matches, word_matches) == 0:
                score = 0.3 * semantic_score
            else:
                score = 0.4 * kw_score + 0.6 * semantic_score
                
            scores[intent] = score
            
        # Location + Action boost for Locator intent
        search_action_words = {"center", "centre", "centers", "centres", "training", "list", "find", "where", "locate", "search", "near", "address", "केन्द्र", "सेंटर"}
        if detected_loc and (words & search_action_words or any(w in normalized for w in search_action_words)):
            scores["Locator"] = max(scores.get("Locator", 0.0), 0.95)
            
        if not scores:
            return "General", 1.0, detected_loc
            
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        if best_score >= self.intent_threshold:
            return best_intent, round(best_score, 4)
            
        return "General", round(best_score, 4)
