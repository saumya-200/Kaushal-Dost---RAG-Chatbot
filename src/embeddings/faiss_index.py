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
        """Loads index and metadata from disk."""
        if not self.index_file.exists() or not self.metadata_file.exists():
            raise FileNotFoundError("FAISS index files not found. Run build_index.py first.")
            
        logger.info("Loading FAISS index...")
        self.index = faiss.read_index(str(self.index_file))
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
            
        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")

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
