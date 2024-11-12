import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse
import json
from googlesearch import search

class URLDiscoverer:
    """Discovers relevant URLs for municipality development opportunities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Search queries templates
        self.search_queries = [
            "{gemeente} ontwikkellocatie",
            "{gemeente} omgevingsvisie 2024",
            "{gemeente} bestemmingsplan wijziging",
            "{gemeente} woningbouw locatie",
            "site:{gemeente}.nl ontwikkeling",
            "{gemeente} gebiedsontwikkeling",
            "{gemeente} transformatie vastgoed"
        ]

    def discover_urls(self, gemeente: str, max_results: int = 10) -> Dict[str, List[Dict]]:
        """Main method to discover URLs"""
        results = {
            'google_results': [],
            'municipality_urls': [],
            'pdf_documents': []
        }
        
        # 1. Google Search
        results['google_results'] = self.google_search(gemeente, max_results)
        
        # 2. Check municipality website
        muni_urls = self.check_municipality_site(gemeente)
        results['municipality_urls'] = muni_urls
        
        # Combine and deduplicate results
        all_urls = set()
        for result in results['google_results']:
            all_urls.add(result['url'])
        for result in results['municipality_urls']:
            all_urls.add(result['url'])
        
        self.logger.info(f"Found {len(all_urls)} unique URLs for {gemeente}")
        return results

    def google_search(self, gemeente: str, max_results: int = 10) -> List[Dict]:
        """Perform Google searches for gemeente"""
        search_results = []
        
        for query_template in self.search_queries:
            query = query_template.format(gemeente=gemeente)
            self.logger.info(f"Searching Google for: {query}")
            
            try:
                # Use googlesearch-python library
                results = search(query, num_results=max_results)
                
                for url in results:
                    result = {
                        'url': url,
                        'query': query,
                        'source': 'google_search'
                    }
                    
                    # Categorize URL
                    if url.lower().endswith('.pdf'):
                        result['type'] = 'pdf'
                    elif 'ruimtelijkeplannen.nl' in url:
                        result['type'] = 'zoning'
                    elif f"{gemeente.lower()}.nl" in url:
                        result['type'] = 'municipality'
                    else:
                        result['type'] = 'other'
                    
                    search_results.append(result)
                
                # Be nice to Google
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error searching for {query}: {str(e)}")
        
        return search_results

    def check_municipality_site(self, gemeente: str) -> List[Dict]:
        """Check municipality website for relevant pages"""
        results = []
        base_urls = [
            f"https://www.{gemeente.lower()}.nl",
            f"https://{gemeente.lower()}.nl"
        ]
        
        relevant_paths = [
            '/ontwikkeling',
            '/projecten',
            '/bestemmingsplannen',
            '/omgevingsvisie',
            '/wonen-en-leven',
            '/bouwen',
            '/vastgoed'
        ]
        
        for base_url in base_urls:
            try:
                # Check if site exists
                response = self.session.get(base_url)
                if response.status_code == 200:
                    # Check each relevant path
                    for path in relevant_paths:
                        url = urljoin(base_url, path)
                        try:
                            path_response = self.session.get(url)
                            if path_response.status_code == 200:
                                results.append({
                                    'url': url,
                                    'type': 'municipality',
                                    'source': 'direct_check'
                                })
                        except:
                            continue
                        
                        time.sleep(1)  # Be nice to servers
                        
            except Exception as e:
                self.logger.error(f"Error checking {base_url}: {str(e)}")
        
        return results

    def save_results(self, results: Dict, gemeente: str):
        """Save discovered URLs"""
        try:
            # Create output directory
            import os
            output_dir = os.path.join('data', 'raw', gemeente, 'urls')
            os.makedirs(output_dir, exist_ok=True)
            
            # Save JSON
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"discovered_urls_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            # Save human-readable summary
            summary_path = os.path.join(output_dir, f"url_summary_{timestamp}.txt")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"URL Discovery Results for {gemeente}\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("Google Search Results:\n")
                f.write("-" * 30 + "\n")
                for result in results['google_results']:
                    f.write(f"Type: {result['type']}\n")
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Query: {result['query']}\n\n")
                
                f.write("\nMunicipality URLs:\n")
                f.write("-" * 30 + "\n")
                for result in results['municipality_urls']:
                    f.write(f"{result['url']}\n")
                
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            return None

def main():
    """Test the URL discoverer"""
    discoverer = URLDiscoverer()
    
    # Test with a gemeente
    gemeente = "Amsterdam"
    results = discoverer.discover_urls(gemeente)
    
    # Save results
    saved_path = discoverer.save_results(results, gemeente)
    
    if saved_path:
        print(f"Results saved to {saved_path}")
        print(f"Found {len(results['google_results'])} Google results")
        print(f"Found {len(results['municipality_urls'])} municipality URLs")

if __name__ == "__main__":
    main()