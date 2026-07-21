import faiss
import numpy as np
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FAISSIndex:
    def __init__(self, dimension: int = 384, index_dir: str = "data/faiss_index"):
        self.dimension = dimension
        self.index_dir = Path(index_dir)
        self.index_file = self.index_dir / "index.bin"
        self.metadata_file = self.index_dir / "metadata.json"
        
        # IndexFlatIP calculates inner product. 
        # With normalized vectors (from Embedder), inner product is exactly cosine similarity.
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def build(self, embeddings: np.ndarray, metadata: list[dict]):
        """
        Builds the FAISS index from normalized embeddings and saves metadata.
        """
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} does not match index dimension {self.dimension}")
            
        logger.info(f"Building FAISS index with {len(embeddings)} vectors...")
        
        # Reset index and metadata
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Ensure array is float32 and contiguous
        vectors = np.ascontiguousarray(embeddings.astype('float32'))
        
        # Add to FAISS
        self.index.add(vectors)
        self.metadata = metadata
        
        self.save()
        logger.info(f"FAISS index built and saved successfully. Total vectors: {self.index.ntotal}")

    def save(self):
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index binary
        faiss.write_index(self.index, str(self.index_file))
        
        # Save metadata mapping
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False)

    def load(self):
        """Loads index and metadata from disk, plus sentence index if available."""
        if not self.index_file.exists() or not self.metadata_file.exists():
            raise FileNotFoundError("FAISS index files not found. Run build_index.py first.")
            
        logger.info("Loading FAISS index...")
        self.index = faiss.read_index(str(self.index_file))
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
            
        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
        
        # Optionally load sentence index if present
        try:
            self.load_sentence_index()
        except Exception as e:
            logger.warning(f"Could not load precomputed sentence index: {e}")

    def save_sentence_index(self, sentence_embeddings: np.ndarray, sentence_metadata: list[dict]):
        """
        Saves sentence embeddings to sentence_embeddings.npz and sentence metadata mapping to sentence_metadata.json.
        sentence_metadata is a list of dicts: {"sentence_id": str, "chunk_id": str, "sentence_index": int, "sentence_text": str, "array_index": int}
        """
        self.index_dir.mkdir(parents=True, exist_ok=True)
        sentence_emb_file = self.index_dir / "sentence_embeddings.npz"
        sentence_meta_file = self.index_dir / "sentence_metadata.json"
        
        np.savez_compressed(sentence_emb_file, embeddings=sentence_embeddings.astype('float32'))
        
        # Organize metadata mapping by chunk_id for O(1) lookup
        chunk_to_sentences = {}
        for meta in sentence_metadata:
            cid = meta["chunk_id"]
            if cid not in chunk_to_sentences:
                chunk_to_sentences[cid] = []
            chunk_to_sentences[cid].append(meta)
            
        with open(sentence_meta_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_to_sentences, f, ensure_ascii=False)
            
        self.sentence_embeddings = sentence_embeddings.astype('float32')
        self.sentence_metadata = chunk_to_sentences
        logger.info(f"Saved sentence index with {len(sentence_embeddings)} sentence vectors across {len(chunk_to_sentences)} chunks.")

    def load_sentence_index(self):
        """Loads precomputed sentence embeddings and metadata from disk if available."""
        sentence_emb_file = self.index_dir / "sentence_embeddings.npz"
        sentence_meta_file = self.index_dir / "sentence_metadata.json"
        
        if not sentence_emb_file.exists() or not sentence_meta_file.exists():
            logger.warning("Sentence index files not found in FAISS index dir.")
            self.sentence_embeddings = None
            self.sentence_metadata = {}
            return
            
        with np.load(sentence_emb_file) as data:
            self.sentence_embeddings = data['embeddings'].astype('float32')
            
        with open(sentence_meta_file, 'r', encoding='utf-8') as f:
            self.sentence_metadata = json.load(f)
            
        logger.info(f"Loaded sentence index with {len(self.sentence_embeddings)} sentence vectors for {len(self.sentence_metadata)} chunks.")

    def get_sentences_for_chunks(self, chunk_ids: list[str]) -> tuple[list[dict], list[str]]:
        """
        Given a list of chunk_ids, returns a tuple: (found_sentences, missing_chunk_ids).
        Each entry in found_sentences is a dict:
          {"text": sentence_text, "chunk_id": chunk_id, "sentence_index": idx, "embedding": 1D np.ndarray}
        """
        if getattr(self, "sentence_embeddings", None) is None or not getattr(self, "sentence_metadata", None):
            self.load_sentence_index()
            
        found_sentences = []
        missing_chunk_ids = []
        
        for cid in chunk_ids:
            if self.sentence_metadata and cid in self.sentence_metadata and self.sentence_embeddings is not None:
                for meta in self.sentence_metadata[cid]:
                    arr_idx = meta["array_index"]
                    vec = self.sentence_embeddings[arr_idx]
                    found_sentences.append({
                        "text": meta["sentence_text"],
                        "chunk_id": cid,
                        "sentence_index": meta["sentence_index"],
                        "embedding": vec
                    })
            else:
                missing_chunk_ids.append(cid)
                
        return found_sentences, missing_chunk_ids

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[dict]:
        """
        Searches for nearest neighbors using inner product (cosine similarity).
        Input must be shape (1, dim) and float32.
        """
        if self.index.ntotal == 0:
            return []
            
        # Ensure query is correct format
        query_vector = np.ascontiguousarray(query_embedding.astype('float32'))
        
        # Search
        scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        results = []
        # scores[0] and indices[0] because we only sent 1 query vector
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1: # FAISS returns -1 if not enough results
                continue
                
            chunk_metadata = self.metadata[idx].copy()
            chunk_metadata['score'] = float(score) # Include similarity score (0.0 to 1.0)
            results.append(chunk_metadata)
            
        return results
