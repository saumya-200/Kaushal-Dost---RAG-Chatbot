from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Embedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        """
        Loads the embedding model. First load downloads it (~118MB).
        Uses CPU by default on systems without GPU.
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info("Model loaded successfully.")

    def embed_chunks(self, chunks: list[dict], batch_size: int = 32) -> np.ndarray:
        """
        Embeds all chunk texts as passages.
        E5 convention requires prefixing passages with 'passage: '
        """
        texts = [f"passage: {chunk['text']}" for chunk in chunks]
        logger.info(f"Embedding {len(texts)} chunks in batches of {batch_size}...")
        
        # model.encode returns a numpy array directly by default
        embeddings = self.model.encode(
            texts, 
            batch_size=batch_size, 
            show_progress_bar=True,
            normalize_embeddings=True # E5 models usually perform best with normalized embeddings
        )
        
        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embeds a single query.
        E5 convention requires prefixing queries with 'query: '
        """
        text = f"query: {query}"
        # return shape (1, 384)
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding

    def embed_passages(self, passages: list[str], batch_size: int = 64) -> np.ndarray:
        """
        Embeds a list of passage/sentence strings with E5 'passage: ' prefix in batches.
        Returns normalized 2D numpy array (len(passages), dim).
        """
        if not passages:
            return np.empty((0, 384), dtype=np.float32)
        texts = [f"passage: {p}" for p in passages]
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )
