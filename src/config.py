import json
import yaml
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Config paths
CONFIG_DIR = BASE_DIR / "chatbot_config"
APPROVED_DOMAINS_PATH = CONFIG_DIR / "approved_domains.json"
THRESHOLDS_PATH = CONFIG_DIR / "thresholds.yaml"
SYSTEM_PROMPT_PATH = CONFIG_DIR / "system_prompt.yaml"
STATIC_KNOWLEDGE_PATH = CONFIG_DIR / "static_knowledge.yaml"

class Config:
    def __init__(self):
        self.domains = self._load_json(APPROVED_DOMAINS_PATH)
        self.thresholds = self._load_yaml(THRESHOLDS_PATH)
        self.prompts = self._load_yaml(SYSTEM_PROMPT_PATH)
        self._static_knowledge = self._load_yaml(STATIC_KNOWLEDGE_PATH) if STATIC_KNOWLEDGE_PATH.exists() else {}
        
    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Missing config file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Missing config file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def approved_domains(self) -> list[str]:
        return self.domains.get("domains", [])

    @property
    def retrieval_thresholds(self) -> dict:
        return self.thresholds.get("retrieval", {})

    @property
    def cache_config(self) -> dict:
        return self.thresholds.get("cache", {})

    @property
    def llm_config(self) -> dict:
        return self.thresholds.get("llm", {})

    @property
    def response_config(self) -> dict:
        return self.thresholds.get("response", {})

    @property
    def chunking_config(self) -> dict:
        return self.thresholds.get("chunking", {})

    @property
    def static_lookup_config(self) -> dict:
        return self.thresholds.get("static_lookup", {})

    @property
    def scope_config(self) -> dict:
        return self.thresholds.get("scope", {})

    @property
    def routing_config(self) -> dict:
        return self.thresholds.get("routing", {})

    @property
    def static_knowledge(self) -> dict:
        return self._static_knowledge

    @property
    def system_prompt(self) -> str:
        return self.prompts.get("system_prompt", "")

    @property
    def banned_words(self) -> list[str]:
        return self.prompts.get("banned_words", [])

    @property
    def banned_word_substitutions(self) -> dict:
        return self.prompts.get("banned_word_substitutions", {})
    
    @property
    def greeting_responses(self) -> dict:
        return self.prompts.get("greeting_responses", {})
        
    @property
    def fallback_responses(self) -> dict:
        return self.prompts.get("fallback_responses", {})

_config_instance = None

def load_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

