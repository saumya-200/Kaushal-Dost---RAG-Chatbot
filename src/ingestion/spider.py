import scrapy
from scrapy.http import Response
import json
from pathlib import Path
from src.config import load_config

class UPSDMSpider(scrapy.Spider):
    name = "upsdm"
    
    # Load settings from config
    config = load_config()
    allowed_domains = config.approved_domains
    start_urls = [
        "https://www.upsdm.gov.in/Home/Index",
        "https://www.upsdm.gov.in/Home/FAQ",
        "https://www.upsdm.gov.in/Home/CourseDetails",
        "https://www.upsdm.gov.in/Home/ContactUsSPMU",
        "https://www.upsdm.gov.in/Home/AboutUPSDM",
        "https://www.upsdm.gov.in/Home/AboutTrainingPartner",
        "https://www.upsdm.gov.in/Home/AboutDPMU",
        "https://www.upsdm.gov.in/Home/AboutSPMU",
        "https://www.upsdm.gov.in/Home/SuccessStory",
        "https://www.upsdm.gov.in/Home/RunningSchemes",
        "https://www.upsdm.gov.in/Home/Downloads",
        "https://www.upsdm.gov.in/Home/PrivacyPolicy",
        "https://www.upsdm.gov.in/Home/CyberSecurity"
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,          # Polite crawling
        'ROBOTSTXT_OBEY': True,
        'DEPTH_LIMIT': 1,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'KaushalDostBot/1.0 (UPSDM Chatbot Research)',
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, output_file='data/raw_pages.jsonl', *args, **kwargs):
        super(UPSDMSpider, self).__init__(*args, **kwargs)
        self.output_file = output_file
        # Ensure data directory exists
        Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
        # Clear previous run
        if Path(self.output_file).exists():
            Path(self.output_file).unlink()

    def parse(self, response: Response):
        # We only want to process HTML and PDF
        content_type = response.headers.get(b'Content-Type', b'').decode('utf-8').lower()
        
        if 'application/pdf' in content_type or response.url.lower().endswith('.pdf'):
            yield self.process_pdf(response)
        elif 'text/html' in content_type:
            yield self.process_html(response)
            
            # Extract internal links and follow them
            for href in response.css('a::attr(href)').getall():
                if not href.startswith('javascript:') and not href.startswith('mailto:') and not href.startswith('#'):
                    yield response.follow(href, self.parse)
        else:
            self.logger.debug(f"Skipping unsupported content type {content_type} at {response.url}")

    def process_html(self, response: Response) -> dict:
        item = {
            'url': response.url,
            'content_type': 'text/html',
            'html': response.text
        }
        self._save_item(item)
        return item
        
    def process_pdf(self, response: Response) -> dict:
        import base64
        item = {
            'url': response.url,
            'content_type': 'application/pdf',
            # Store bytes as base64 in JSON
            'pdf_base64': base64.b64encode(response.body).decode('utf-8')
        }
        self._save_item(item)
        return item
        
    def _save_item(self, item: dict):
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item) + '\n')
