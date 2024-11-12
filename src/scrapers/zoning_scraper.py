import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
from typing import List, Dict
import re
from datetime import datetime

class MunicipalityDocumentScraper:
    def __init__(self):
        # Updated with actual Dutch municipality document URLs
        self.base_urls = {
            'amsterdam': 'https://www.amsterdam.nl/bestuur-organisatie/volg-beleid/omgevingsvisie/',
            'rotterdam': 'https://www.rotterdam.nl/wonen-leven/omgevingsvisie/',
            'utrecht': 'https://www.utrecht.nl/bestuur-en-organisatie/beleid/omgevingsvisie/',
            'den-haag': 'https://www.denhaag.nl/nl/bestuur-en-organisatie/beleid/omgevingsvisie.htm'
        }
        
        # Dutch development keywords with categories
        self.development_keywords = {
            # Wonen/Residential
            'woningbouw': 'Wonen',
            'woningen': 'Wonen',
            'appartementen': 'Wonen',
            'woonwijk': 'Wonen',
            'huisvesting': 'Wonen',
            
            # Kantoor/Office
            'kantoorruimte': 'Kantoor',
            'kantoorontwikkeling': 'Kantoor',
            'werklocatie': 'Kantoor',
            
            # Commercieel/Commercial
            'winkelruimte': 'Commercieel',
            'detailhandel': 'Commercieel',
            'horeca': 'Commercieel',
            'retail': 'Commercieel',
            
            # Gemengd/Mixed-Use
            'gemengd gebruik': 'Gemengd',
            'multifunctioneel': 'Gemengd',
            'gemengde ontwikkeling': 'Gemengd',
            
            # Transformatie/Transformation
            'herontwikkeling': 'Transformatie',
            'transformatie': 'Transformatie',
            'herbestemming': 'Transformatie',
            'renovatie': 'Transformatie'
        }
        
        # Dutch location indicators
        self.location_patterns = [
            r'(?:in|op|bij|nabij|aan)\s+(?:de|het)?\s+([A-Z][a-zA-Z\s-]+(?:straat|weg|plein|buurt|wijk|gebied|kwartier|park|laan|gracht|kade|steeg|hof|singel))',
            r'(?:de|het)\s+([A-Z][a-zA-Z\s-]+(?:straat|weg|plein|buurt|wijk|gebied|kwartier|park|laan|gracht|kade|steeg|hof|singel))'
        ]

    def extract_text_from_pdf(self, pdf_url: str) -> str:
        """Download and extract text from PDF."""
        try:
            response = requests.get(pdf_url)
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error bij PDF extractie: {e}")
            return ""

    def find_development_mentions(self, text: str) -> List[Dict]:
        """Find mentions of development opportunities in text."""
        developments = []
        
        # Search for development mentions in paragraphs
        paragraphs = text.split('\n\n')
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            
            # Check for development keywords
            for keyword, dev_type in self.development_keywords.items():
                if keyword.lower() in paragraph_lower:
                    # Try to find location
                    location = None
                    for pattern in self.location_patterns:
                        matches = re.findall(pattern, paragraph)
                        if matches:
                            location = matches[0]
                            break
                    
                    # Look for additional relevant information
                    extra_info = {
                        'heeft_bestemmingsplan': 'bestemmingsplan' in paragraph_lower,
                        'heeft_omgevingsvergunning': 'omgevingsvergunning' in paragraph_lower,
                        'is_prioriteitsgebied': any(term in paragraph_lower for term in 
                            ['prioriteitsgebied', 'focusgebied', 'ontwikkelgebied']),
                        'mentions_woningnood': any(term in paragraph_lower for term in 
                            ['woningnood', 'woningtekort', 'woningbehoefte']),
                    }
                    
                    if location:
                        developments.append({
                            'type': dev_type,
                            'locatie': location,
                            'beschrijving': paragraph[:200] + '...',
                            'bron_tekst': paragraph,
                            'datum_gevonden': datetime.now().strftime('%Y-%m-%d'),
                            'extra_info': extra_info
                        })
        
        return developments

    def scrape_municipality(self, municipality: str) -> List[Dict]:
        """Scrape documents for a specific municipality."""
        if municipality not in self.base_urls:
            return []

        url = self.base_urls[municipality]
        opportunities = []
        
        try:
            # Get main page
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find document links (PDF and web pages)
            doc_links = []
            
            # Look for PDFs
            pdf_links = [a['href'] for a in soup.find_all('a') if '.pdf' in a.get('href', '').lower()]
            doc_links.extend(pdf_links)
            
            # Look for relevant web pages
            relevant_links = [a['href'] for a in soup.find_all('a') 
                            if any(term in a.get('href', '').lower() for term in [
                                'omgevingsvisie', 'bestemmingsplan', 'gebiedsontwikkeling',
                                'ruimtelijke-ontwikkeling', 'woningbouw', 'ontwikkelgebied'
                            ])]
            doc_links.extend(relevant_links)
            
            for doc_link in doc_links:
                # Make URL absolute if necessary
                if not doc_link.startswith('http'):
                    doc_link = f"{self.base_urls[municipality]}{doc_link}"
                
                # Handle different document types
                if doc_link.lower().endswith('.pdf'):
                    text = self.extract_text_from_pdf(doc_link)
                else:
                    # For web pages, get the HTML content
                    try:
                        response = requests.get(doc_link)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Extract text from main content area (adjust selectors as needed)
                        text = ' '.join([p.text for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
                    except Exception as e:
                        print(f"Error bij web pagina extractie: {e}")
                        continue
                
                # Find development mentions
                developments = self.find_development_mentions(text)
                
                for dev in developments:
                    dev['gemeente'] = municipality
                    dev['bron_url'] = doc_link
                    opportunities.append(dev)
        
        except Exception as e:
            print(f"Error bij scrapen van {municipality}: {e}")
        
        return opportunities

    def get_document_types(self) -> List[str]:
        """Get list of document types to search for."""
        return [
            "Omgevingsvisie",
            "Bestemmingsplan",
            "Gebiedsvisie",
            "Structuurvisie",
            "Ontwikkelstrategie",
            "Woningbouwprogramma",
            "Omgevingsplan"
        ]
    