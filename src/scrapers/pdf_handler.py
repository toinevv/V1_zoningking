import logging
import PyPDF2
import io
import requests
import os
from typing import Dict, Optional, List
from urllib.parse import urljoin, urlparse
from datetime import datetime
from .gpt_analyzer import GPTAnalyzer


class PDFHandler:
    """Handles all PDF operations: finding, downloading, and text extraction"""
    
    def __init__(self, openai_api_key: str = None):  # Make api_key optional
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Common PDF keywords to look for
        self.relevant_keywords = [
            'omgevingsvisie',
            'bestemmingsplan',
            'ontwikkelingsplan',
            'structuurvisie',
            'gebiedsvisie',
            'woningbouw'
        ]
        # Initialize GPT Analyzer
        try:
            self.gpt_analyzer = os.getenv('OPENAI_API_KEY') and GPTAnalyzer(os.getenv('OPENAI_API_KEY'))
            self.logger.info("GPT Analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize GPT Analyzer: {str(e)}")
            self.gpt_analyzer = None

    def find_pdfs_on_page(self, html_soup, base_url: str) -> List[Dict]:
        """Find PDF links in a webpage"""
        pdf_links = []
        
        for link in html_soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text().strip()
            
            if href.lower().endswith('.pdf'):
                # Make URL absolute if it's relative
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                # Check if PDF is relevant
                is_relevant = any(keyword in (href + text).lower() 
                                for keyword in self.relevant_keywords)
                
                pdf_links.append({
                    'url': href,
                    'title': text or href.split('/')[-1],
                    'is_relevant': is_relevant,
                    'source_page': base_url
                })
        
        return pdf_links

    def download_pdf(self, url: str, save_path: Optional[str] = None) -> Dict:
        """Download and process a PDF file"""
        self.logger.info(f"Downloading PDF from: {url}")
        
        try:
            # Download PDF
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Failed to download PDF: HTTP {response.status_code}")
            
            # Create PDF reader object
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text
            total_pages = len(pdf_reader.pages)
            self.logger.info(f"Processing PDF with {total_pages} pages")
            
            extracted_text = ""
            for page_num in range(total_pages):
                try:
                    text = pdf_reader.pages[page_num].extract_text() or ""
                    extracted_text += text
                    
                    if page_num % 10 == 0:  # Log progress every 10 pages
                        self.logger.info(f"Processed {page_num + 1}/{total_pages} pages")
                        
                except Exception as e:
                    self.logger.error(f"Error processing page {page_num}: {str(e)}")
            
            # Save PDF if path provided
            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(response.content)
            
            result = {
                'success': True,
                'url': url,
                'total_pages': total_pages,
                'text_content': extracted_text,
                'text_length': len(extracted_text),
                'saved_path': save_path if save_path else None
            }
            
            self.logger.info(f"Successfully processed PDF: {len(extracted_text)} characters extracted")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {url}: {str(e)}")
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'text_content': "",
                'text_length': 0,
                'saved_path': None
            }

    def is_relevant_pdf(self, pdf_info: Dict) -> bool:
        """Check if a PDF is relevant for development opportunities"""
        if not pdf_info['success']:
            return False
            
        # Check content for relevant keywords
        text_lower = pdf_info['text_content'].lower()
        keyword_count = sum(1 for keyword in self.relevant_keywords 
                          if keyword in text_lower)
                          
        return keyword_count >= 2  # PDF must contain at least 2 relevant keywords

    def save_pdf_info(self, pdf_info: Dict, gemeente: str):
        """Save PDF information and content"""
        if not pdf_info['success']:
            return
            
        # Create directory structure
        base_dir = os.path.join('data', 'raw', gemeente, 'pdfs')
        os.makedirs(base_dir, exist_ok=True)
        
        # Create filename from URL
        filename = urlparse(pdf_info['url']).path.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Save paths
        pdf_path = os.path.join(base_dir, filename)
        info_path = os.path.join(base_dir, f"{filename[:-4]}_info.json")
        text_path = os.path.join(base_dir, f"{filename[:-4]}_content.txt")
        
        # Save PDF file
        if not pdf_info.get('saved_path'):
            self.download_pdf(pdf_info['url'], pdf_path)
        
        # Save text content
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(pdf_info['text_content'])
        
        # Save metadata
        import json
        meta_info = {
            'url': pdf_info['url'],
            'total_pages': pdf_info['total_pages'],
            'text_length': pdf_info['text_length'],
            'pdf_path': pdf_path,
            'text_path': text_path,
            'processed_date': datetime.now().isoformat()
        }
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(meta_info, f, indent=2)
            
        return {
            'pdf_path': pdf_path,
            'text_path': text_path,
            'info_path': info_path
        }
    def process_pdf_with_analysis(self, url: str, gemeente: str) -> Dict:
        """Download, process and analyze a PDF"""
        # First download and process PDF
        pdf_info = self.download_pdf(url)
        
        if not pdf_info['success']:
            return pdf_info
            
        # If we have a GPT analyzer, analyze the content
        if self.gpt_analyzer and self.is_relevant_pdf(pdf_info):
            self.logger.info("Analyzing PDF content with GPT")
            analysis = self.gpt_analyzer.analyze_document(
                content=pdf_info['text_content'],
                title=url.split('/')[-1],
                url=url,
                doc_type=self.detect_document_type(url, pdf_info['text_content'])
            )
            pdf_info['analysis'] = analysis
            
        # Save everything
        saved_info = self.save_pdf_info(pdf_info, gemeente)
        pdf_info['saved_paths'] = saved_info
        
        return pdf_info

def main():
    """Test the PDF handler"""
    handler = PDFHandler()
    
    # Test with a sample PDF
    test_url = "https://www.amsterdam.nl/bestuur-organisatie/volg-beleid/omgevingsvisie/omgevingsvisie-amsterdam-2050/"
    
    # Download and process PDF
    pdf_info = handler.download_pdf(test_url)
    
    if pdf_info['success']:
        print(f"Successfully processed PDF:")
        print(f"- Pages: {pdf_info['total_pages']}")
        print(f"- Text length: {pdf_info['text_length']}")
        
        # Check relevance
        if handler.is_relevant_pdf(pdf_info):
            print("PDF is relevant for development opportunities")
            
            # Save information
            save_info = handler.save_pdf_info(pdf_info, "Amsterdam")
            print(f"Saved PDF information to: {save_info['info_path']}")
    else:
        print(f"Failed to process PDF: {pdf_info['error']}")

if __name__ == "__main__":
    main()