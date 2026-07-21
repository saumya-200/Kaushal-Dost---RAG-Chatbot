import pytest
import numpy as np
from src.ingestion.chunker import Chunker
from src.routing.extractive.extractive_generator import ExtractiveGenerator
from src.routing.router import Router
from unittest.mock import patch


def test_markdown_link_stripping():
    chunker = Chunker()
    raw_text = "Click here [Candidate Registration User Manual](https://upsdm.gov.in/manual.pdf) to download the form."
    chunks = chunker.chunk_text(raw_text, "https://upsdm.gov.in/test", "text/html", "en")
    
    assert len(chunks) > 0
    stored_text = chunks[0]["text"]
    assert "](" not in stored_text
    assert "Candidate Registration User Manual" in stored_text
    assert "https://upsdm.gov.in/manual.pdf" not in stored_text


def test_pdf_ligature_normalization():
    chunker = Chunker()
    # Raw PDF text with ligatures ﬁ (U+FB01) and ﬂ (U+FB02)
    raw_pdf_text = "Speciﬁc requirements for a training center include ﬂexible classrooms."
    chunks = chunker.chunk_text(raw_pdf_text, "https://upsdm.gov.in/guidelines.pdf", "pdf", "en")
    
    assert len(chunks) > 0
    stored_text = chunks[0]["text"]
    assert "ﬁ" not in stored_text
    assert "ﬂ" not in stored_text
    assert "Specific requirements" in stored_text
    assert "flexible classrooms" in stored_text


def test_administrative_list_tagging_and_stage5_exclusion():
    chunker = Chunker()
    blacklisted_url = "https://upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf"
    normal_url = "https://upsdm.gov.in/Home/AboutUPSDM"
    
    chunks_blacklisted = chunker.chunk_text("List of de-empanelled training partners", blacklisted_url, "pdf", "en")
    chunks_normal = chunker.chunk_text("UPSDM is a state mission for skill development", normal_url, "text/html", "en")
    
    assert len(chunks_blacklisted) > 0
    assert chunks_blacklisted[0]["content_type"] == "administrative_list"
    
    assert len(chunks_normal) > 0
    assert chunks_normal[0]["content_type"] == "content"
    
    # Test Stage 5 exclusion in ExtractiveGenerator
    with patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        router = Router()
        ext_gen = ExtractiveGenerator(router.embedder)
        
        faiss_results = [
            {
                "chunk_id": "blacklisted_001",
                "source_url": blacklisted_url,
                "text": "De-empanelled training partner list for 2024",
                "score": 0.95,
                "content_type": "administrative_list"
            },
            {
                "chunk_id": "normal_001",
                "source_url": normal_url,
                "text": "UPSDM provides skill development training across Uttar Pradesh",
                "score": 0.85,
                "content_type": "content"
            }
        ]
        
        # Test confidence calculation excludes administrative_list
        level, score, signals = ext_gen.compute_retrieval_confidence(faiss_results)
        # Top valid score should be 0.85 (from normal_001), not 0.95 (from blacklisted_001)
        assert signals["top_score"] == 0.85
        
        # Test answer generation excludes administrative_list
        query = "What is UPSDM?"
        q_emb = router.embedder.embed_query(query)
        answer = ext_gen.generate_extractive_answer(query, q_emb, faiss_results)
        
        assert "De-empanelled" not in answer
        assert "UPSDM provides skill development training" in answer
