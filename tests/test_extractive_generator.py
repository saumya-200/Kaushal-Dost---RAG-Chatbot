import pytest
import numpy as np
from unittest.mock import MagicMock
from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex
from src.routing.extractive.extractive_generator import ExtractiveGenerator


def test_extractive_generator_uses_precomputed_sentence_embeddings():
    # Mock Embedder
    mock_embedder = MagicMock(spec=Embedder)
    # Mock FAISSIndex with precomputed sentence index
    mock_faiss_index = MagicMock(spec=FAISSIndex)
    
    chunk_id = "test_chunk_001"
    sent_text = "UPSDM offers skill training across Uttar Pradesh."
    fake_sentence_vec = np.ones((384,), dtype=np.float32)
    fake_sentence_vec = fake_sentence_vec / np.linalg.norm(fake_sentence_vec)
    
    mock_faiss_index.get_sentences_for_chunks.return_value = (
        [
            {
                "text": sent_text,
                "chunk_id": chunk_id,
                "sentence_index": 0,
                "embedding": fake_sentence_vec
            }
        ],
        []  # no missing chunk_ids
    )
    
    generator = ExtractiveGenerator(embedder=mock_embedder, faiss_index=mock_faiss_index)
    
    query = "What is UPSDM?"
    query_emb = np.ones((1, 384), dtype=np.float32)
    query_emb = query_emb / np.linalg.norm(query_emb)
    
    results = [
        {
            "chunk_id": chunk_id,
            "source_url": "https://upsdm.gov.in/About",
            "text": sent_text,
            "score": 0.88,
            "content_type": "content"
        }
    ]
    
    answer = generator.generate_extractive_answer(query, query_emb, results)
    
    # Assert answer contains the sentence text
    assert sent_text in answer
    # Assert zero calls to embedder methods during request handling!
    mock_embedder.embed_query.assert_not_called()
    mock_embedder.embed_passages.assert_not_called()


def test_extractive_generator_fallback_on_missing_chunk_id():
    mock_embedder = MagicMock(spec=Embedder)
    fake_emb = np.ones((1, 384), dtype=np.float32)
    fake_emb = fake_emb / np.linalg.norm(fake_emb)
    mock_embedder.embed_query.return_value = fake_emb
    
    mock_faiss_index = MagicMock(spec=FAISSIndex)
    chunk_id = "unindexed_chunk_999"
    
    # Return missing chunk_id
    mock_faiss_index.get_sentences_for_chunks.return_value = ([], [chunk_id])
    
    generator = ExtractiveGenerator(embedder=mock_embedder, faiss_index=mock_faiss_index)
    
    query = "What is UPSDM?"
    query_emb = fake_emb
    results = [
        {
            "chunk_id": chunk_id,
            "source_url": "https://upsdm.gov.in/About",
            "text": "UPSDM is Uttar Pradesh Skill Development Mission.",
            "score": 0.88,
            "content_type": "content"
        }
    ]
    
    answer = generator.generate_extractive_answer(query, query_emb, results)
    
    assert "UPSDM is Uttar Pradesh Skill Development Mission." in answer
    # Assert fallback live encoding was called for the missing chunk
    assert mock_embedder.embed_query.call_count > 0


def test_extractive_generator_truncation():
    # Test boundary-aware truncation on long chunks
    mock_embedder = MagicMock(spec=Embedder)
    mock_faiss_index = MagicMock(spec=FAISSIndex)
    
    chunk_id = "long_chunk_001"
    # Construct sentences that exceed 500 characters
    long_sentences = [
        "First sentence is here and it is short.",
        "Second sentence is also here and contains a good amount of words.",
        "Third sentence is very long and has a lot of words to exceed the character limit of five hundred characters in total. " * 3,
        "Fourth sentence is the final one."
    ]
    
    # Mock precomputed sentences
    mock_faiss_index.get_sentences_for_chunks.return_value = (
        [
            {
                "text": s,
                "chunk_id": chunk_id,
                "sentence_index": idx,
                "embedding": np.ones((384,), dtype=np.float32) / np.sqrt(384)
            }
            for idx, s in enumerate(long_sentences)
        ],
        []
    )
    
    generator = ExtractiveGenerator(embedder=mock_embedder, faiss_index=mock_faiss_index)
    
    query = "test query"
    query_emb = np.ones((1, 384), dtype=np.float32) / np.sqrt(384)
    
    results = [
        {
            "chunk_id": chunk_id,
            "source_url": "https://upsdm.gov.in/About",
            "text": " ".join(long_sentences),
            "score": 0.95,
            "content_type": "content"
        }
    ]
    
    answer = generator.generate_extractive_answer(query, query_emb, results)
    
    # Assert answer is under 500 characters
    assert len(answer) <= 500
    # Assert it ends cleanly (should end with the source suffix)
    assert answer.endswith("(Source: upsdm.gov.in/About)")
    
    # Strip suffix and prefix to check truncation boundary
    extracted_part = answer.replace("According to official UPSDM guidelines from upsdm.gov.in/About:\n", "").replace("\n\n(Source: upsdm.gov.in/About)", "")
    assert extracted_part[-1] in ['.', '!', '?', '।'] or not extracted_part[-1].isalnum()

