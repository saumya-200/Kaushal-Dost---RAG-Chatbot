"""
Builds the FAISS vector index and precomputed sentence embeddings from processed chunks.

Note:
  This script MUST be re-run after any change to chunk content or data files.
  Sentence-level embeddings used by ExtractiveGenerator (Stage 5) are now
  precomputed and stored in data/faiss_index/sentence_embeddings.npz and
  data/faiss_index/sentence_metadata.json to eliminate runtime re-embedding latency.
"""

import sys
from pathlib import Path
import json
import logging
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex
from src.ingestion.sentence_splitter import split_into_sentences

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("build_index")

def main():
    chunks_file = "data/chunks.jsonl"
    
    if not Path(chunks_file).exists():
        logger.error(f"{chunks_file} not found. Run crawler first.")
        return

    logger.info("Loading chunks...")
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    if not chunks:
        logger.error("No chunks found in file.")
        return
        
    logger.info(f"Loaded {len(chunks)} chunks.")
    
    start_time = time.time()
    
    embedder = Embedder()
    embeddings = embedder.embed_chunks(chunks)
    
    index = FAISSIndex()
    index.build(embeddings, chunks)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 2: Precompute sentence embeddings offline
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("Extracting and precomputing sentence embeddings across all chunks...")
    all_sentences = []
    sentence_metadata = []
    
    for chunk in chunks:
        cid = chunk["chunk_id"]
        text = chunk.get("text", "")
        sents = split_into_sentences(text)
        for s_idx, sent_text in enumerate(sents):
            arr_idx = len(all_sentences)
            all_sentences.append(sent_text)
            sentence_metadata.append({
                "sentence_id": f"{cid}__sent_{s_idx:03d}",
                "chunk_id": cid,
                "sentence_index": s_idx,
                "sentence_text": sent_text,
                "array_index": arr_idx
            })
            
    logger.info(f"Extracted {len(all_sentences)} sentences from {len(chunks)} chunks. Pre-embedding in batches...")
    sentence_embeddings = embedder.embed_passages(all_sentences, batch_size=64)
    index.save_sentence_index(sentence_embeddings, sentence_metadata)
    
    duration = time.time() - start_time
    
    index_size_mb = Path(index.index_file).stat().st_size / (1024 * 1024)
    sentence_size_mb = Path(index.index_dir / "sentence_embeddings.npz").stat().st_size / (1024 * 1024)
    
    logger.info("-" * 40)
    logger.info("INDEX BUILD SUMMARY")
    logger.info(f"Total chunks embedded: {len(chunks)}")
    logger.info(f"Total sentences precomputed: {len(all_sentences)}")
    logger.info(f"Index dimension: {index.dimension}")
    logger.info(f"Chunk index size on disk: {index_size_mb:.2f} MB")
    logger.info(f"Sentence index size on disk: {sentence_size_mb:.2f} MB")
    logger.info(f"Total time: {duration:.2f} seconds")
    logger.info(f"Average speed: {len(chunks)/duration:.2f} chunks/sec")
    logger.info("-" * 40)

if __name__ == "__main__":
    main()
