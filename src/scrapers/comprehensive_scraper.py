import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import pandas as pd
from datetime import datetime
import time
import logging
from typing import List, Dict
import re

class ComprehensiveGemeenteScraper:
    def __init__(self):
        self.search_terms = {
            'development': [
                '{gemeente} ontwikkellocatie',
                '{gemeente} herontwikkeling',
                '{gemeente} transformatie vastgoed',
                '{gemeente} woningbouw plannen',
                '{gemeente} omgevingsvisie',
                '{gemeente} bestemmingsplan wijziging'
            ],
            'news': [
                '{gemeente} nieuwbouw nieuws',
                '{gemeente} vastgoed ontwikkeling',
                '{gemeente} bouwprojecten'
            ],
            'municipality': [
                '{gemeente} gemeente visie',
                '{gemeente} ruimtelijke ontwikkeling',
                '{gemeente} woningbouw locatie'
            ]
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean up text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

    def scrape_url(self, url: str) -> Dict:
        """Scrape content from a URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Extract text content
            text_content = self.extract_text_from_html(response.text)
            
            # Extract title
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else url
            
            return {
                'url': url,
                'title': title.strip(),
                'content': text_content,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'title': url,
                'content': '',
                'status': 'error',
                'error': str(e)
            }

    def search_gemeente(self, gemeente: str, max_results: int = 30) -> List[Dict]:
        """Search for gemeente information"""
        all_results = []
        gemeente_lower = gemeente.lower().replace(' ', '-')
        
        # List of URLs to check
        base_urls = [
            f"https://www.{gemeente_lower}.nl",
            f"https://www.ruimtelijkeplannen.nl/viewer/view?gemeente={gemeente}",
            "https://www.vastgoedmarkt.nl",
            "https://www.gebiedsontwikkeling.nu"
        ]
        
        for base_url in base_urls:
            try:
                self.logger.info(f"Checking {base_url}")
                response = requests.get(base_url, headers=self.headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find relevant links
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        title = link.get_text().strip()
                        
                        # Make URL absolute
                        if not href.startswith('http'):
                            href = urljoin(base_url, href)
                        
                        # Check if link is relevant
                        if self.is_relevant_link(href, title):
                            result = {
                                'gemeente': gemeente,
                                'title': title,
                                'url': href,
                                'source': base_url,
                                'date_found': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            # Scrape content if it's a key page
                            if any(term in href.lower() for term in ['omgevingsvisie', 'bestemmingsplan']):
                                content = self.scrape_url(href)
                                result.update(content)
                            
                            all_results.append(result)
                            
                            if len(all_results) >= max_results:
                                break
                    
                time.sleep(2)  # Be nice to servers
                
            except Exception as e:
                self.logger.error(f"Error processing {base_url}: {str(e)}")
        
        return all_results

    def is_relevant_link(self, url: str, title: str) -> bool:
        """Check if a link is relevant for development opportunities"""
        relevant_terms = [
            'ontwikkel', 'bouw', 'woning', 'vastgoed', 'transformatie',
            'herontwikkeling', 'omgevingsvisie', 'bestemmingsplan'
        ]
        
        url_lower = url.lower()
        title_lower = title.lower()
        
        return any(term in url_lower or term in title_lower for term in relevant_terms)

    def save_results(self, results: List[Dict], gemeente: str):
        """Save results to CSV file"""
        if not results:
            return
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"data/scraped/{gemeente}/results_{timestamp}.csv"
        
        # Ensure directory exists
        import os
        os.makedirs(f"data/scraped/{gemeente}", exist_ok=True)
        
        # Save
        df.to_csv(filename, index=False, encoding='utf-8')
        self.logger.info(f"Saved {len(results)} results to {filename}")

def main():
    # Test the scraper
    scraper = ComprehensiveGemeenteScraper()
    gemeente = "Amsterdam"
    
    print(f"Starting scrape for {gemeente}")
    results = scraper.search_gemeente(gemeente, max_results=5)
    
    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"\nTitle: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Source: {result['source']}")
    
    # Save results
    scraper.save_results(results, gemeente)

if __name__ == "__main__":
    main()