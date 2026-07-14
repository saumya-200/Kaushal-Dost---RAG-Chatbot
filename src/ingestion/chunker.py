import hashlib
import re
from datetime import datetime, timezone
import logging
from src.config import load_config

logger = logging.getLogger(__name__)

class Chunker:
    def __init__(self):
        config = load_config()
        self.chunk_size = config.chunking_config.get('chunk_size_tokens', 500)
        self.overlap = config.chunking_config.get('chunk_overlap_tokens', 50)
        
    def chunk_text(self, text: str, url: str, content_type: str, language: str) -> list[dict]:
        """
        Splits text into chunks and adds metadata.
        Uses a simple word-based splitting strategy that respects sentence boundaries where possible.
        """
        if not text or len(text.strip()) == 0:
            return []
            
        # Basic normalization
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Split into approximate "sentences" 
        # Hindi uses | (purna viram) or . for sentence endings
        sentences = re.split(r'(?<=[.।!?])\s+', text)
        
        chunks = []
        current_chunk_words = []
        current_word_count = 0
        
        # Helper to process current chunk
        def save_chunk(words):
            chunk_text = " ".join(words)
            chunks.append(chunk_text)
            
        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_len = len(sentence_words)
            
            if sentence_len == 0:
                continue
                
            # If a single sentence is huge, we have to split it forcefully
            if sentence_len > self.chunk_size:
                if current_chunk_words:
                    save_chunk(current_chunk_words)
                    current_chunk_words = []
                    current_word_count = 0
                
                # Split huge sentence into chunks of exact chunk_size
                for i in range(0, sentence_len, self.chunk_size - self.overlap):
                    segment = sentence_words[i:i + self.chunk_size]
                    save_chunk(segment)
                continue
                
            # If adding this sentence would exceed the chunk size, save the current chunk
            if current_word_count + sentence_len > self.chunk_size and current_word_count > 0:
                save_chunk(current_chunk_words)
                
                # Start new chunk with overlap
                overlap_words = current_chunk_words[-self.overlap:] if self.overlap > 0 else []
                current_chunk_words = overlap_words + sentence_words
                current_word_count = len(current_chunk_words)
            else:
                # Add sentence to current chunk
                current_chunk_words.extend(sentence_words)
                current_word_count += sentence_len
                
        # Save the last chunk if not empty
        if current_chunk_words:
            save_chunk(current_chunk_words)
            
        # Format chunks as dicts with metadata
        source_id = url.replace('https://', '').replace('http://', '').strip('/')
        now = datetime.now(timezone.utc).isoformat()
        
        formatted_chunks = []
        for i, chunk_text in enumerate(chunks):
            # Extract a rough title from the URL path or first line
            title = url.split('/')[-1] if '/' in url else source_id
            if not title or title.lower() in ['index', 'home']:
                title = "UPSDM " + (url.split('/')[-2] if len(url.split('/')) > 2 else "Page")
                
            formatted_chunks.append({
                "chunk_id": f"{source_id}__chunk_{i:03d}",
                "source_url": url,
                "source_id": source_id,
                "text": chunk_text,
                "hash_sha256": self.compute_hash(chunk_text),
                "language": language,
                "content_type": content_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "last_crawled": now,
                "title": title,
                "word_count": len(chunk_text.split())
            })
            
        return formatted_chunks
        
    def compute_hash(self, text: str) -> str:
        """SHA-256 hash of normalized text."""
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
