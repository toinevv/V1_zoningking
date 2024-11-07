from .base_scraper import BaseScraper
from typing import Dict, List
import time

class MunicipalityScraper(BaseScraper):
    """Scrapes municipality websites for development information"""
    
    def __init__(self):
        super().__init__()
        self.development_patterns = [
            'ontwikkeling',
            'woningbouw',
            'bestemmingsplan',
            'omgevingsvisie',
            'gebiedsontwikkeling'
        ]

    def get_municipality_urls(self, gemeente: str) -> List[str]:
        """Get common municipality URLs to check"""
        base_urls = [
            f"https://www.{gemeente.lower()}.nl",
            f"https://{gemeente.lower()}.nl",
            f"https://gemeente.{gemeente.lower()}.nl"
        ]
        
        paths = [
            '/ontwikkeling',
            '/projecten',
            '/wonen',
            '/bouwen',
            '/bestemmingsplannen',
            '/omgevingsvisie',
            '/gebiedsontwikkeling'
        ]
        
        urls = []
        for base in base_urls:
            urls.extend([f"{base}{path}" for path in paths])
            
        return urls

    def scrape(self, gemeente: str) -> Dict:
        """Scrape municipality website"""
        results = {
            'urls_checked': [],
            'active_urls': [],
            'development_pages': [],
            'development_links': []
        }
        
        urls = self.get_municipality_urls(gemeente)
        
        for url in urls:
            self.logger.info(f"Checking {url}")
            results['urls_checked'].append(url)
            
            soup = self.get_page(url)
            if soup:
                results['active_urls'].append(url)
                
                # Store page if it contains development information
                if any(pattern in soup.text.lower() for pattern in self.development_patterns):
                    results['development_pages'].append({
                        'url': url,
                        'title': soup.title.string if soup.title else url,
                        'content': soup.get_text()
                    })
                
                # Find related links
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text()
                    if any(pattern in (href + text).lower() for pattern in self.development_patterns):
                        results['development_links'].append({
                            'url': href,
                            'text': text,
                            'source_page': url
                        })
            
            time.sleep(1)  # Be nice to servers
        
        self.logger.info(f"Found {len(results['development_pages'])} development pages")
        return results