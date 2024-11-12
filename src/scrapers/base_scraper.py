from abc import ABC, abstractmethod
from typing import List, Dict
import logging
import requests
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @abstractmethod
    def scrape(self, gemeente: str) -> Dict:
        """Main scraping method to be implemented by each scraper"""
        pass

    def get_page(self, url: str) -> BeautifulSoup:
        """Get and parse a webpage"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            self.logger.error(f"Failed to get {url}: Status {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
        return None

    def save_results(self, results: Dict, gemeente: str):
        """Save scraping results"""
        pass