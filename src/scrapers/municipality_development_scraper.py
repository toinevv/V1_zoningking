import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import os
from urllib.parse import urljoin
import PyPDF2
import io

class MunicipalityDevelopmentScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Key development-related pages per municipality
        self.development_paths = {
            'amsterdam': [
                '/bestuur-organisatie/organisatie/ruimte-economie/grond-en-ontwikkeling/gebiedsontwikkeling',
                '/wonen-leefomgeving/vastgoedprofessionals/woningbouw-transformatie',
                '/bestuur-organisatie/volg-beleid/stedelijke-ontwikkeling',
                '/bestuur-organisatie/volg-beleid/omgevingsvisie'
            ]
        }
        
        # Key document types to look for
        self.document_types = [
            'omgevingsvisie',
            'structuurvisie',
            'gebiedsvisie',
            'ontwikkelstrategie',
            'woningbouwplannen',
            'transformatiegebieden'
        ]

    def scrape_municipality(self, gemeente: str) -> Dict:
        """Scrape development information for a specific municipality"""
        gemeente_lower = gemeente.lower()
        base_url = f"https://www.{gemeente_lower}.nl"
        
        results = {
            'development_pages': [],
            'pdf_documents': [],
            'development_areas': []
        }
        
        try:
            # 1. Scrape main development pages
            development_paths = self.development_paths.get(gemeente_lower, [])
            for path in development_paths:
                url = urljoin(base_url, path)
                self.logger.info(f"Scraping {url}")
                
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Store page content
                    results['development_pages'].append({
                        'url': url,
                        'title': soup.title.string if soup.title else path,
                        'content': soup.get_text()
                    })
                    
                    # Find PDF links
                    pdf_links = self.find_pdf_links(soup, base_url)
                    for pdf in pdf_links:
                        if any(doc_type in pdf['url'].lower() for doc_type in self.document_types):
                            self.logger.info(f"Found relevant PDF: {pdf['title']}")
                            # Download and store PDF content
                            pdf_content = self.download_and_process_pdf(pdf['url'])
                            if pdf_content:
                                pdf['content'] = pdf_content
                                results['pdf_documents'].append(pdf)
                    
                    # Find development areas
                    areas = self.find_development_areas(soup)
                    results['development_areas'].extend(areas)
            
            # Save results
            self.save_results(results, gemeente)
            return results
            
        except Exception as e:
            self.logger.error(f"Error scraping {gemeente}: {str(e)}")
            return results

    def find_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Find PDF links in page"""
        pdf_links = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.lower().endswith('.pdf'):
                url = href if href.startswith('http') else urljoin(base_url, href)
                pdf_links.append({
                    'url': url,
                    'title': link.get_text().strip() or href.split('/')[-1]
                })
        return pdf_links

    def download_and_process_pdf(self, url: str) -> str:
        """Download and extract text from PDF"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            self.logger.error(f"Error processing PDF {url}: {str(e)}")
        return None

    def find_development_areas(self, soup: BeautifulSoup) -> List[Dict]:
        """Find mentions of development areas in page"""
        areas = []
        development_keywords = [
            'ontwikkelgebied',
            'transformatiegebied',
            'woningbouwlocatie',
            'herontwikkeling'
        ]
        
        # Look for structured content (lists, tables, etc.)
        for element in soup.find_all(['ul', 'ol', 'table']):
            text = element.get_text().lower()
            if any(keyword in text for keyword in development_keywords):
                # Parse out individual areas
                items = element.find_all(['li', 'tr'])
                for item in items:
                    item_text = item.get_text().strip()
                    if item_text:
                        areas.append({
                            'name': item_text,
                            'source_type': element.name,
                            'keywords_found': [k for k in development_keywords if k in item_text.lower()]
                        })
        
        return areas

    def save_results(self, results: Dict, gemeente: str):
        """Save scraped results"""
        # Create directory for gemeente
        gemeente_dir = os.path.join('data', 'raw', gemeente)
        os.makedirs(gemeente_dir, exist_ok=True)
        
        # Save development pages
        if results['development_pages']:
            with open(os.path.join(gemeente_dir, 'development_pages.txt'), 'w', encoding='utf-8') as f:
                for page in results['development_pages']:
                    f.write(f"URL: {page['url']}\n")
                    f.write(f"Title: {page['title']}\n")
                    f.write(f"Content:\n{page['content']}\n")
                    f.write("-" * 80 + "\n")
        
        # Save PDF contents
        if results['pdf_documents']:
            with open(os.path.join(gemeente_dir, 'pdf_contents.txt'), 'w', encoding='utf-8') as f:
                for pdf in results['pdf_documents']:
                    f.write(f"Title: {pdf['title']}\n")
                    f.write(f"URL: {pdf['url']}\n")
                    if pdf.get('content'):
                        f.write(f"Content:\n{pdf['content']}\n")
                    f.write("-" * 80 + "\n")
        
        # Save development areas
        if results['development_areas']:
            with open(os.path.join(gemeente_dir, 'development_areas.txt'), 'w', encoding='utf-8') as f:
                for area in results['development_areas']:
                    f.write(f"Name: {area['name']}\n")
                    f.write(f"Keywords: {', '.join(area['keywords_found'])}\n")
                    f.write("-" * 80 + "\n")

def main():
    # Test the scraper
    scraper = MunicipalityDevelopmentScraper()
    gemeente = "Amsterdam"
    
    print(f"Scraping development information for {gemeente}")
    results = scraper.scrape_municipality(gemeente)
    
    print("\nResults found:")
    print(f"Development pages: {len(results['development_pages'])}")
    print(f"PDF documents: {len(results['pdf_documents'])}")
    print(f"Development areas: {len(results['development_areas'])}")

if __name__ == "__main__":
    main()