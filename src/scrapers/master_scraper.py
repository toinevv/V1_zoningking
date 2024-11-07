from src.scrapers.comprehensive_scraper import ComprehensiveGemeenteScraper
from src.scrapers.document_scraper import GemeenteDocumentScraper
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime
import os

class MasterScraper:
    def __init__(self):
        # Initialize all our scrapers
        self.google_scraper = ComprehensiveGemeenteScraper()
        self.doc_scraper = GemeenteDocumentScraper()
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Create necessary directories
        self.create_directories()

    def create_directories(self):
        """Create necessary directories for data storage"""
        directories = [
            'data',
            'data/scraped',
            'data/processed',
            'data/raw'
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def scrape_gemeente(self, gemeente: str) -> Dict:
        """Main method to scrape all sources for a gemeente"""
        self.logger.info(f"Starting comprehensive scraping for {gemeente}")
        
        # Create gemeente-specific directory
        gemeente_dir = f"data/scraped/{gemeente}"
        os.makedirs(gemeente_dir, exist_ok=True)
        
        results = {
            'search_results': [],
            'document_results': [],
            'ruimtelijke_plannen': [],
            'official_publications': [],
            'real_estate_listings': []
        }
        
        # 1. Comprehensive Search
        try:
            self.logger.info("Starting comprehensive search...")
            search_results = self.google_scraper.search_gemeente(gemeente)
            results['search_results'] = search_results
            self.save_results(search_results, gemeente, 'search_results')
        except Exception as e:
            self.logger.error(f"Error in comprehensive search: {str(e)}")

        # 2. Document Scraping
        try:
            self.logger.info("Starting document scraping...")
            doc_results = self.doc_scraper.scrape_gemeente_documents(gemeente)
            results['document_results'] = doc_results
            self.save_results(doc_results, gemeente, 'document_results')
        except Exception as e:
            self.logger.error(f"Error in document scraping: {str(e)}")

        # 3. Ruimtelijke Plannen
        try:
            self.logger.info("Scraping Ruimtelijke Plannen...")
            rp_url = f"https://www.ruimtelijkeplannen.nl/viewer/view?gemeente={gemeente}"
            # Add specific implementation here
        except Exception as e:
            self.logger.error(f"Error in Ruimtelijke Plannen scraping: {str(e)}")

        # 4. Official Publications
        try:
            self.logger.info("Scraping official publications...")
            # Add specific implementation here
        except Exception as e:
            self.logger.error(f"Error in official publications scraping: {str(e)}")

        return results

    def save_results(self, results: List[Dict], gemeente: str, result_type: str):
        """Save results to CSV file"""
        if not results:
            return
            
        # Create gemeente directory if it doesn't exist
        gemeente_dir = f"data/scraped/{gemeente}"
        os.makedirs(gemeente_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{gemeente_dir}/{result_type}_{timestamp}.csv"
        
        # Convert to DataFrame and save
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False, encoding='utf-8')
        self.logger.info(f"Saved {len(results)} {result_type} to {filename}")

def main():
    # Test the scraper
    scraper = MasterScraper()
    gemeente = "Amsterdam"
    
    print(f"Starting scrape for {gemeente}")
    results = scraper.scrape_gemeente(gemeente)
    
    # Print summary
    for result_type, data in results.items():
        print(f"\nFound {len(data)} {result_type}")

if __name__ == "__main__":
    main()