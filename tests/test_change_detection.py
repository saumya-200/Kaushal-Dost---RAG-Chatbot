import pytest
import os
import sqlite3
from src.ingestion.change_detector import ChangeDetector

def query_db(db_path, query, params=(), fetchone=False):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchone:
            return cursor.fetchone()
        return cursor.fetchall()
    finally:
        conn.close()

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_state.db"
    yield str(path)
    if path.exists():
        os.remove(path)

@pytest.fixture
def detector(db_path):
    return ChangeDetector(db_path)

@pytest.fixture
def sample_chunks():
    return [
        {"source_id": "page1", "chunk_index": 0, "hash_sha256": "hash1a"},
        {"source_id": "page1", "chunk_index": 1, "hash_sha256": "hash1b"},
        {"source_id": "page2", "chunk_index": 0, "hash_sha256": "hash2a"},
        {"source_id": "page3", "chunk_index": 0, "hash_sha256": "hash3a"},
        {"source_id": "page3", "chunk_index": 1, "hash_sha256": "hash3b"},
    ]

def test_first_run_all_new(detector, sample_chunks, db_path):
    result = detector.check_and_update(sample_chunks)
    
    assert result["summary"]["total_sources"] == 3
    assert result["summary"]["new_count"] == 3
    assert result["summary"]["changed_count"] == 0
    assert result["summary"]["unchanged_count"] == 0
    
    res = query_db(db_path, "SELECT count(*) FROM chunk_state", fetchone=True)
    assert res[0] == 3

def test_unchanged_run(detector, sample_chunks, db_path):
    # First run
    detector.check_and_update(sample_chunks)
    
    # Second run (identical)
    result = detector.check_and_update(sample_chunks)
    
    assert result["summary"]["new_count"] == 0
    assert result["summary"]["changed_count"] == 0
    assert result["summary"]["unchanged_count"] == 3
    
    res = query_db(db_path, "SELECT version FROM chunk_state")
    versions = [row[0] for row in res]
    assert all(v == 1 for v in versions)

def test_changed_content(detector, sample_chunks, db_path):
    # First run
    detector.check_and_update(sample_chunks)
    
    # Modify one chunk
    modified_chunks = list(sample_chunks)
    modified_chunks[0] = {"source_id": "page1", "chunk_index": 0, "hash_sha256": "hash1a_MODIFIED"}
    
    # Second run
    result = detector.check_and_update(modified_chunks)
    
    assert result["summary"]["new_count"] == 0
    assert result["summary"]["changed_count"] == 1
    assert result["summary"]["unchanged_count"] == 2
    assert "page1" in result["changed"]
    
    res = query_db(db_path, "SELECT version FROM chunk_state WHERE source_id = 'page1'", fetchone=True)
    assert res[0] == 2

def test_new_source_added(detector, sample_chunks, db_path):
    # First run
    detector.check_and_update(sample_chunks)
    
    # Add new source
    new_chunks = list(sample_chunks)
    new_chunks.append({"source_id": "page4", "chunk_index": 0, "hash_sha256": "hash4a"})
    
    # Second run
    result = detector.check_and_update(new_chunks)
    
    assert result["summary"]["new_count"] == 1
    assert result["summary"]["changed_count"] == 0
    assert result["summary"]["unchanged_count"] == 3
    assert "page4" in result["new"]
    
    res = query_db(db_path, "SELECT count(*) FROM chunk_state", fetchone=True)
    assert res[0] == 4

def test_deleted_source(detector, sample_chunks, db_path):
    # First run
    detector.check_and_update(sample_chunks)
    
    # Remove page2
    reduced_chunks = [c for c in sample_chunks if c["source_id"] != "page2"]
    
    # Second run
    result = detector.check_and_update(reduced_chunks)
    
    assert result["summary"]["new_count"] == 0
    assert result["summary"]["changed_count"] == 0
    assert result["summary"]["unchanged_count"] == 2
    assert "page2" not in result["unchanged"]
    
    # DB should still have 3 rows (we keep history)
    res = query_db(db_path, "SELECT count(*) FROM chunk_state", fetchone=True)
    assert res[0] == 3
