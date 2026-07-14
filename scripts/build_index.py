import sys
from pathlib import Path
import json
import logging
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.embeddings.embed import Embedder
from src.embeddings.faiss_index import FAISSIndex

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("build_index")

def main():
    chunks_file = "data/chunks.jsonl"
    
    if not Path(chunks_file).exists():
        logger.error(f"{chunks_file} not found. Run crawle₹r first.")
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
    
    duration = time.time() - start_time
    
    index_size_mb = Path(index.index_file).stat().st_size / (1024 * 1024)
    
    logger.info("-" * 40)
    logger.info("INDEX BUILD SUMMARY")
    logger.info(f"Total chunks embedded: {len(chunks)}")
    logger.info(f"Index dimension: {index.dimension}")
    logger.info(f"Index size on disk: {index_size_mb:.2f} MB")
    logger.info(f"Total time: {duration:.2f} seconds")
    logger.info(f"Average speed: {len(chunks)/duration:.2f} chunks/sec")
    logger.info("-" * 40)

if __name__ == "__main__":
    main()
