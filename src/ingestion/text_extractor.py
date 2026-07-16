import trafilatura
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io
import re
from langdetect import detect, detect_langs, LangDetectException
import logging

logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self):
        # Check if Hindi language pack is installed for tesseract
        try:
            self.tesseract_langs = pytesseract.get_languages(config='')
            self.has_hindi_ocr = 'hin' in self.tesseract_langs
            if not self.has_hindi_ocr:
                logger.warning("Tesseract 'hin' (Hindi) language pack not found. OCR for Hindi PDFs may fail.")
        except Exception as e:
            logger.warning(f"Failed to check Tesseract languages: {e}")
            self.has_hindi_ocr = False

    def extract_html(self, html: str, url: str) -> str:
        """Extract main text from HTML using trafilatura and append links/buttons."""
        try:
            # Trafilatura does an excellent job of removing boilerplates (nav, footer, etc)
            text = trafilatura.extract(html, url=url, include_links=True, include_images=False, include_tables=True)
            if not text:
                text = ""
                
            # Extract actionable links and buttons using BeautifulSoup
            # to make sure we don't lose key buttons (like "RFP Registration")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            action_elements = []
            
            # 1. Links (a tags)
            for a in soup.find_all('a'):
                href = a.get('href', '').strip()
                link_text = a.get_text(separator=' ', strip=True)
                # Ignore empty, javascript, mailto, tel links
                if href and link_text and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    action_elements.append(f"- Link: \"{link_text}\" leads to {href}")
            
            # 2. Buttons
            for btn in soup.find_all('button'):
                btn_text = btn.get_text(separator=' ', strip=True)
                if btn_text:
                    action_elements.append(f"- Button: \"{btn_text}\"")
                    
            # 3. Form input buttons (e.g. submit)
            for inp in soup.find_all('input', type=['submit', 'button']):
                val = inp.get('value', '').strip()
                if val:
                    action_elements.append(f"- Action Button: \"{val}\"")
            
            if action_elements:
                unique_actions = []
                seen = set()
                for act in action_elements:
                    if act not in seen:
                        seen.add(act)
                        unique_actions.append(act)
                
                actions_text = "\nAvailable links and buttons on this page:\n" + "\n".join(unique_actions)
                if text:
                    text = actions_text + "\n\n" + text
                else:
                    text = actions_text
                    
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting HTML from {url}: {e}")
            return ""

    def extract_pdf(self, pdf_bytes: bytes, url: str) -> tuple[str, str]:
        """
        Extract text from PDF.
        Returns tuple: (extracted_text, method_used)
        method_used is one of: 'pdf_text', 'pdf_ocr'
        """
        text = ""
        method = "pdf_text"
        
        try:
            # 1. Try PyMuPDF for text extraction
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Cap at 50 pages to prevent OOM/timeouts on massive docs
            num_pages = min(len(doc), 50)
            
            for i in range(num_pages):
                page = doc.load_page(i)
                text += page.get_text() + "\n\n"
            
            doc.close()
            
            text = text.strip()
            
            # If we got very little text relative to the number of pages, it's likely a scanned PDF
            if len(text) < num_pages * 50:
                logger.info(f"PDF {url} seems to be scanned (low text volume). Attempting OCR...")
                text = self._extract_pdf_ocr(pdf_bytes, num_pages)
                method = "pdf_ocr"
                
        except Exception as e:
            logger.error(f"Error processing PDF {url}: {e}")
            
        return text, method
        
    def _extract_pdf_ocr(self, pdf_bytes: bytes, num_pages: int) -> str:
        """Extract text from scanned PDF using Tesseract OCR."""
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for i, page in enumerate(pdf.pages[:num_pages]):
                    # Extract any tables first if they exist
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            text += " | ".join([str(c) if c else "" for c in row]) + "\n"
                        text += "\n"
                    
                    # Convert page to image for OCR
                    im = page.to_image(resolution=300)
                    pil_image = im.original
                    
                    # Run OCR
                    lang_config = 'eng+hin' if self.has_hindi_ocr else 'eng'
                    page_text = pytesseract.image_to_string(pil_image, lang=lang_config)
                    text += page_text + "\n\n"
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            
        return text.strip()

    def detect_language(self, text: str) -> str:
        """
        Detects language. Returns 'en', 'hi', or 'mixed'.
        """
        if not text or len(text.strip()) == 0:
            return "en"
            
        # Fast check for Devanagari script range
        # \u0900 to \u097F is the Devanagari Unicode block
        has_hindi = bool(re.search(r'[\u0900-\u097F]', text))
        
        try:
            if has_hindi:
                # Let's see if it's purely Hindi or mixed
                # If there are a significant number of English letters too
                has_english = bool(re.search(r'[a-zA-Z]{3,}', text))
                if has_english:
                    return "mixed"
                return "hi"
                
            # If no Devanagari, it might be English or Romanized Hindi
            # We'll classify both as 'en' for now, since they use Latin script
            return "en"
        except Exception:
            return "en"
