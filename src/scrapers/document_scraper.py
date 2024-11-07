import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import os
import PyPDF2
import io
from urllib.parse import urljoin
from datetime import datetime
import time
from openai import OpenAI
import json

class GemeenteDocumentScraper:
    def __init__(self, openai_api_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=openai_api_key)
            self.logger.info("OpenAI client initialized for document analysis")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise Exception("OpenAI client initialization failed")

    def analyze_with_gpt(self, text: str, document_title: str) -> Dict:
        """Analyze document content with GPT-4"""
        prompt = f"""
        Analyseer dit gemeentelijk document: '{document_title}'

        Focus op het vinden van concrete ontwikkelkansen:
        1. Specifieke locaties of gebieden voor ontwikkeling
        2. Type ontwikkelingen die mogelijk zijn
        3. Huidige status en timeline
        4. Voorwaarden en eisen voor ontwikkeling
        5. Bestemmingsplan wijzigingen

        Geef voor elke ontwikkelkans:
        - Exacte locatie/gebied
        - Toegestaan type ontwikkeling
        - Status/fase
        - Planning wanneer genoemd
        - Omvang/schaal wanneer genoemd
        - Specifieke voorwaarden

        Format als JSON met deze keys:
        - document_type: type document (omgevingsvisie, bestemmingsplan, etc.)
        - opportunities: lijst van ontwikkelkansen
        - key_areas: lijst van prioritaire ontwikkelgebieden
        - zoning_changes: lijst van geplande bestemmingswijzigingen
        - relevant_policies: lijst van relevante ontwikkelingsregels
        """

        try:
            # Split text into manageable chunks
            chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            all_analyses = []

            for i, chunk in enumerate(chunks[:5]):  # Analyze first 5 chunks
                self.logger.info(f"Analyzing chunk {i+1}/{len(chunks)} of {document_title}")
                
                response = self.client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": "Je bent een expert in Nederlandse gebiedsontwikkeling en bestemmingsplannen."},
                        {"role": "user", "content": prompt},
                        {"role": "user", "content": f"Document deel {i+1}/{len(chunks)}: {chunk}"}
                    ],
                    response_format={ "type": "json_object" }
                )
                
                analysis = json.loads(response.choices[0].message.content)
                all_analyses.append(analysis)

            # Combine analyses
            combined = self.combine_analyses(all_analyses)
            self.logger.info(f"Analysis complete for {document_title}. Found {len(combined.get('opportunities', []))} opportunities")
            return combined

        except Exception as e:
            self.logger.error(f"Error analyzing document with GPT: {str(e)}")
            return {"opportunities": [], "key_areas": [], "zoning_changes": []}

    def combine_analyses(self, analyses: List[Dict]) -> Dict:
        """Combine analyses from different chunks of the same document"""
        combined = {
            "document_type": next((a.get("document_type") for a in analyses if a.get("document_type")), "unknown"),
            "opportunities": [],
            "key_areas": [],
            "zoning_changes": [],
            "relevant_policies": []
        }

        seen_locations = set()
        
        for analysis in analyses:
            # Add unique opportunities
            for opp in analysis.get("opportunities", []):
                location = opp.get("location", "")
                if location and location not in seen_locations:
                    seen_locations.add(location)
                    combined["opportunities"].append(opp)
            
            # Add unique areas and changes
            combined["key_areas"].extend([
                area for area in analysis.get("key_areas", [])
                if area not in combined["key_areas"]
            ])
            combined["zoning_changes"].extend([
                change for change in analysis.get("zoning_changes", [])
                if change not in combined["zoning_changes"]
            ])
            combined["relevant_policies"].extend([
                policy for policy in analysis.get("relevant_policies", [])
                if policy not in combined["relevant_policies"]
            ])

        return combined

    def process_pdf_link(self, link, base_url: str) -> Dict:
        """Process and analyze a PDF link"""
        href = link.get('href', '')
        title = link.get_text().strip() or href.split('/')[-1]
        
        if not href.startswith('http'):
            href = urljoin(base_url, href)
        
        if href.lower().endswith('.pdf'):
            self.logger.info(f"Found PDF: {title}")
            content = self.download_pdf(href)
            
            if content:
                # Analyze the PDF content with GPT
                analysis = self.analyze_with_gpt(content, title)
                
                return {
                    'url': href,
                    'title': title,
                    'content': content,
                    'type': 'pdf',
                    'analysis': analysis,
                    'opportunities': analysis.get('opportunities', [])
                }
        return None

    # [Rest of your existing methods...]

    def scrape_municipality(self, gemeente: str) -> Dict:
        """Main scraping method"""
        results = {
            'development_pages': [],
            'pdf_documents': [],
            'development_areas': [],
            'opportunities': []  # New field for all opportunities
        }

        base_url = f"https://www.{gemeente.lower()}.nl"
        paths = [
            '/bestuur-organisatie/organisatie/ruimte-economie/grond-en-ontwikkeling/gebiedsontwikkeling',
            '/wonen-leefomgeving/vastgoedprofessionals/woningbouw-transformatie',
            '/bestuur-organisatie/volg-beleid/stedelijke-ontwikkeling',
            '/bestuur-organisatie/volg-beleid/omgevingsvisie'
        ]
        
        for path in paths:
            url = base_url + path
            self.logger.info(f"Scraping {url}")
            
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Store the page content
                    results['development_pages'].append({
                        'url': url,
                        'title': soup.title.string if soup.title else path,
                        'content': soup.get_text()
                    })
                    
                    # Process PDFs and analyze them
                    for link in soup.find_all('a'):
                        if 'omgevingsvisie' in str(link).lower() and link.get('href', '').lower().endswith('.pdf'):
                            self.logger.info(f"Processing relevant PDF: {link.get_text().strip()}")
                            pdf_doc = self.process_pdf_link(link, base_url)
                            if pdf_doc:
                                results['pdf_documents'].append(pdf_doc)
                                # Add opportunities from this document
                                results['opportunities'].extend(pdf_doc.get('opportunities', []))
                
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)}")
            
            time.sleep(1)  # Be nice to servers

        self.logger.info(f"Scraping complete for {gemeente}")
        self.logger.info(f"Found {len(results['opportunities'])} total opportunities")
        return results