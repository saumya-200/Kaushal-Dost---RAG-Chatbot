import sys
from pathlib import Path
import json
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import base64
import time

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.ingestion.spider import UPSDMSpider
from src.ingestion.text_extractor import TextExtractor
from src.ingestion.chunker import Chunker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_crawler")

def run_spider(raw_file: str):
    logger.info("Starting Scrapy crawler...")
    process = CrawlerProcess(get_project_settings())
    process.crawl(UPSDMSpider, output_file=raw_file)
    process.start() # This blocks until crawling is finished
    logger.info("Crawler finished.")

def process_raw_files(raw_file: str, output_file: str, report_file: str):
    logger.info("Processing raw files into chunks...")
    extractor = TextExtractor()
    chunker = Chunker()
    
    total_pages = 0
    total_pdfs = 0
    total_pdfs_ocr = 0
    total_chunks = 0
    lang_stats = {'en': 0, 'hi': 0, 'mixed': 0}
    
    start_time = time.time()
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(report_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(raw_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
         
        for line in f_in:
            if not line.strip():
                continue
                
            data = json.loads(line)
            url = data['url']
            content_type = data['content_type']
            
            text = ""
            actual_content_type = content_type
            
            if 'text/html' in content_type:
                total_pages += 1
                text = extractor.extract_html(data['html'], url)
            elif 'application/pdf' in content_type:
                total_pdfs += 1
                pdf_bytes = base64.b64decode(data['pdf_base64'])
                text, method = extractor.extract_pdf(pdf_bytes, url)
                if method == 'pdf_ocr':
                    total_pdfs_ocr += 1
                    actual_content_type = 'pdf_ocr'
                else:
                    actual_content_type = 'pdf'
                    
            if not text:
                logger.warning(f"No text extracted from {url}")
                continue
                
            lang = extractor.detect_language(text)
            chunks = chunker.chunk_text(text, url, actual_content_type, lang)
            
            for chunk in chunks:
                f_out.write(json.dumps(chunk) + '\n')
                total_chunks += 1
                lang_stats[chunk['language']] = lang_stats.get(chunk['language'], 0) + 1

    duration = time.time() - start_time
    
    # Write report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# UPSDM Crawl Report\n\n")
        f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Duration**: {duration:.2f} seconds\n")
        f.write(f"- **Total HTML pages processed**: {total_pages}\n")
        f.write(f"- **Total PDFs processed**: {total_pdfs} (OCR used on {total_pdfs_ocr})\n")
        f.write(f"- **Total chunks generated**: {total_chunks}\n")
        f.write(f"- **Language distribution**: English: {lang_stats['en']}, Hindi: {lang_stats['hi']}, Mixed: {lang_stats['mixed']}\n")
        
    logger.info(f"Processing complete. Generated {total_chunks} chunks. Report saved to {report_file}")

if __name__ == "__main__":
    raw_file = "data/raw_pages.jsonl"
    output_file = "data/chunks.jsonl"
    report_file = "reports/crawl_report.md"
    
    run_spider(raw_file)
    process_raw_files(raw_file, output_file, report_file)
