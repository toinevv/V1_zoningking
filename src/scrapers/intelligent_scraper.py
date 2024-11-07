from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import os
from urllib.parse import urljoin, urlparse
import time
import openai
import json
from datetime import datetime
import PyPDF2
import io

class IntelligentScraper:
    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        
        # Properly initialize OpenAI client
        try:
            self.client = openai.OpenAI(
                api_key=openai_api_key,
                timeout=60.0  # Increase timeout for large documents
            )
            self.logger.info("OpenAI client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise Exception("Failed to initialize OpenAI client. Check your API key.")
        
        # Initialize session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_fallback_strategy(self, gemeente: str) -> Dict:
        """Active fallback strategy that scrapes municipality website and ruimtelijkeplannen.nl"""
        
        base_urls = {
            'gemeente': f'https://www.{gemeente.lower()}.nl',
            'ruimtelijke_plannen': 'https://www.ruimtelijkeplannen.nl',
            'overheid': 'https://zoek.officielebekendmakingen.nl'
        }
        
        discovered_links = []
        keywords = []
        patterns = []

        try:
            # 1. Try to find the sitemap or robots.txt for better crawling
            for name, base_url in base_urls.items():
                try:
                    # Check robots.txt for sitemap
                    robots_response = self.session.get(f"{base_url}/robots.txt")
                    if robots_response.status_code == 200:
                        for line in robots_response.text.split('\n'):
                            if 'sitemap' in line.lower():
                                sitemap_url = line.split(': ')[1].strip()
                                discovered_links.append(sitemap_url)
                    
                    # Try common development-related paths
                    common_paths = [
                        '/ontwikkeling',
                        '/projecten',
                        '/bestemmingsplannen',
                        '/omgevingsvisie',
                        '/wonen',
                        '/bouwen',
                        '/ruimtelijke-plannen'
                    ]
                    
                    for path in common_paths:
                        url = f"{base_url}{path}"
                        response = self.session.get(url)
                        if response.status_code == 200:
                            discovered_links.append(url)
                            # Extract more links from the page
                            soup = BeautifulSoup(response.text, 'html.parser')
                            for link in soup.find_all('a', href=True):
                                href = link['href']
                                text = link.get_text().lower().strip()
                                
                                # Build keyword list from actual page content
                                if any(term in text for term in ['ontwikkel', 'bouw', 'plan', 'visie', 'gebied']):
                                    keywords.append(text)
                                    
                                # Build pattern list from discovered URLs
                                if href.startswith('/') or href.startswith(base_url):
                                    url_parts = href.split('/')
                                    for part in url_parts:
                                        if any(term in part for term in ['ontwikkel', 'bouw', 'plan', 'visie', 'gebied']):
                                            patterns.append(part)
                
                except Exception as e:
                    self.logger.error(f"Error exploring {name}: {str(e)}")
                
                # Be nice to servers
                time.sleep(1)

            # Create dynamic search strategy based on what we found
            return {
                "google_queries": [
                    f"site:{base_urls['gemeente']} ontwikkeling",
                    f"site:{base_urls['gemeente']} omgevingsvisie",
                    f"site:{base_urls['ruimtelijke_plannen']} {gemeente}",
                    *[f"site:{base_urls['gemeente']} {keyword}" for keyword in set(keywords[:5])]
                ],
                "keywords": list(set(keywords)),
                "document_types": ["pdf", "nota", "visie", "plan"],
                "page_patterns": list(set(patterns)) or ["ontwikkeling", "projecten", "plannen"],
                "discovered_urls": discovered_links
            }
            
        except Exception as e:
            self.logger.error(f"Error in fallback strategy: {str(e)}")
            # Absolute minimum fallback if everything fails
            return {
                "google_queries": [f"site:{base_urls['gemeente']} ontwikkeling"],
                "keywords": ["ontwikkeling"],
                "document_types": ["pdf"],
                "page_patterns": ["ontwikkeling"],
                "discovered_urls": []
            }
    def get_search_strategy(self, gemeente: str) -> Dict:
        """Use LLM to generate search strategies for this gemeente"""
        prompt = f"""
        I need to find development opportunities in the municipality of {gemeente}, Netherlands.
        Create a search strategy to find:
        1. The municipality's official website
        2. Development plans (ontwikkelingsplannen)
        3. Zoning changes (bestemmingsplannen)
        4. Vision documents (omgevingsvisie)
        5. Transformation areas (transformatiegebieden)

        Format the response as JSON with these keys:
        - google_queries: list of search queries to find relevant pages
        - keywords: Dutch keywords to look for in pages
        - document_types: types of documents to look for
        - page_patterns: common page titles or URL patterns that might indicate relevant content
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",  # Using the latest model that supports JSON output
                messages=[
                    {"role": "system", "content": "You are a Dutch urban development researcher who knows how to find municipality development information."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }  # This is now supported in the latest model
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Error getting search strategy: {str(e)}")
            return self.get_fallback_strategy(gemeente)
    def test_openai_connection(self):
        """Test if OpenAI connection is working"""
        try:
            # Load API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("Error: No OpenAI API key found in environment variables")
                return False
            
            # Try to initialize scraper
            scraper = IntelligentScraper(api_key)
            
            # Test a simple completion
            response = scraper.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "You are a test assistant."},
                    {"role": "user", "content": "Say 'test successful' if you can read this."}
                ]
            )
            
            if response:
                print("OpenAI connection test successful!")
                return True
                
        except Exception as e:
            self.logger.error(f"Error testing OpenAI connection: {str(e)}")
            return False

    def scrape_gemeente(self, gemeente: str) -> Dict:
        """Main method to scrape gemeente information using LLM guidance"""
        results = {
            'search_strategy': None,
            'relevant_pages': [],
            'development_opportunities': [],
            'key_documents': []
        }
        
        try:
            # 1. Get search strategy from LLM
            self.logger.info(f"Getting search strategy for {gemeente}")
            search_strategy = self.get_search_strategy(gemeente)
            results['search_strategy'] = search_strategy
            
            # 2. First check any discovered URLs from the strategy
            if 'discovered_urls' in search_strategy:
                for url in search_strategy['discovered_urls']:
                    try:
                        page_response = self.session.get(url, timeout=10)
                        if page_response.status_code == 200:
                            content = self.extract_text(page_response.text)
                            analysis = self.analyze_content(content, url)
                            
                            if analysis.get('is_relevant'):
                                results['relevant_pages'].append({
                                    'url': url,
                                    'title': self.extract_title(page_response.text),
                                    'analysis': analysis,
                                    'source': 'direct_discovery'
                                })
                    except Exception as e:
                        self.logger.error(f"Error processing discovered URL {url}: {str(e)}")
                    time.sleep(1)
            
            # 3. Then do Google searches based on strategy
            for query in search_strategy['google_queries']:
                google_url = f"https://www.google.com/search?q={query}"
                response = self.session.get(google_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for result in soup.find_all('div', class_='g'):
                        link = result.find('a')
                        if link and link.get('href'):
                            url = link['href']
                            
                            if not any(pattern in url.lower() for pattern in search_strategy['page_patterns']):
                                continue
                            
                            try:
                                page_response = self.session.get(url, timeout=10)
                                if page_response.status_code == 200:
                                    content = self.extract_text(page_response.text)
                                    analysis = self.analyze_content(content, url)
                                    
                                    if analysis.get('is_relevant'):
                                        results['relevant_pages'].append({
                                            'url': url,
                                            'title': self.extract_title(page_response.text),
                                            'analysis': analysis,
                                            'source': 'google_search'
                                        })
                            except Exception as e:
                                self.logger.error(f"Error fetching {url}: {str(e)}")
                
                time.sleep(2)
            # Process any PDF links found
            pdf_docs = []
            for page in results['relevant_pages']:
                if page['url'].lower().endswith('.pdf'):
                    self.logger.info(f"Found PDF: {page['url']}")
                    pdf_content = self.download_pdf(page['url'])
                    if pdf_content:
                        pdf_docs.append({
                            'url': page['url'],
                            'title': page['title'],
                            'content': pdf_content
                        })

            results['pdf_documents'] = pdf_docs
            
            # Process PDF documents
            if pdf_docs:
                self.logger.info(f"Processing {len(pdf_docs)} PDF documents")
                for pdf_doc in pdf_docs:
                    self.logger.info(f"Analyzing PDF: {pdf_doc['title']}")
                    pdf_analysis = self.analyze_pdf_content(
                        pdf_doc['content'],
                        pdf_doc['url'],
                        pdf_doc['title']
                    )
                    
                    # Save PDF analysis
                    self.save_pdf_analysis(pdf_analysis, gemeente, pdf_doc['title'])
                    
                    # Add opportunities to overall results
                    results['development_opportunities'].extend(
                        pdf_analysis.get('opportunities', [])
                    )
                    
                    # Add document reference
                    results['key_documents'].append({
                        'title': pdf_doc['title'],
                        'url': pdf_doc['url'],
                        'type': pdf_analysis.get('document_type', 'unknown'),
                        'key_areas': pdf_analysis.get('key_areas', []),
                        'zoning_changes': pdf_analysis.get('zoning_changes', [])
                    })
            # Process PDF documents
            if 'pdf_documents' in results:
                self.logger.info(f"Processing {len(results['pdf_documents'])} PDF documents")
                for pdf_doc in results['pdf_documents']:
                    if pdf_doc.get('content'):
                        pdf_analysis = self.analyze_pdf_content(
                            pdf_doc['content'],
                            pdf_doc['url'],
                            pdf_doc['title']
                        )
                        
                        # Save PDF analysis
                        self.save_pdf_analysis(pdf_analysis, gemeente, pdf_doc['title'])
                        
                        # Add opportunities to overall results
                        results['development_opportunities'].extend(pdf_analysis.get('opportunities', []))
                        
                        # Add document reference
                        results['key_documents'].append({
                            'title': pdf_doc['title'],
                            'url': pdf_doc['url'],
                            'type': pdf_analysis.get('document_type', 'unknown'),
                            'key_areas': pdf_analysis.get('key_areas', []),
                            'zoning_changes': pdf_analysis.get('zoning_changes', [])
                        })
            # Save results
            self.save_results(results, gemeente)

            if len(results['development_opportunities']) > 0:
                self.logger.info(f"\nFound {len(results['development_opportunities'])} development opportunities:")
                for i, opp in enumerate(results['development_opportunities'], 1):
                    self.logger.info(f"{i}. {opp.get('location', 'Unknown location')} - {opp.get('type', 'Unknown type')}")
            
            if len(results['key_documents']) > 0:
                self.logger.info(f"\nAnalyzed {len(results['key_documents'])} key documents:")
                for doc in results['key_documents']:
                    self.logger.info(f"- {doc['title']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in main scrape process: {str(e)}")
            return results
        
    def analyze_content(self, text: str, url: str) -> Dict:
        """Use LLM to analyze if content is relevant and extract key information"""
        prompt = f"""
        Analyze this text from {url} and determine if it contains information about real estate development opportunities.
        Look for:
        1. Specific areas or locations mentioned for development
        2. Types of development (housing, commercial, mixed-use)
        3. Timeline or status of developments
        4. Size or scale of developments
        5. Any zoning or permit information

        Format the response as JSON with these keys:
        - is_relevant: boolean
        - locations: list of specific locations mentioned
        - development_types: list of development types mentioned
        - status: current status of developments
        - key_details: list of important details
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",  # Using the latest model that supports JSON output
                messages=[
                    {"role": "system", "content": "You are a Dutch urban development expert. Analyze text for development opportunities."},
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": text[:4000]}  # First 4000 chars for context
                ],
                response_format={ "type": "json_object" }  # This is now supported in the latest model
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Error analyzing content: {str(e)}")
            return {"is_relevant": False}
            
        except Exception as e:
            self.logger.error(f"Error analyzing content: {str(e)}")
            return {"is_relevant": False}
        
    def analyze_pdf_content(self, pdf_content: str, pdf_url: str, pdf_title: str) -> Dict:
        """Analyze PDF content using GPT-4 for development opportunities"""
        self.logger.info(f"\n{'='*50}\nAnalyzing PDF: {pdf_title}\n{'='*50}")
        
        prompt = f"""
        Je bent een expert in Nederlandse gebiedsontwikkeling. 
        Analyseer dit document '{pdf_title}' ({pdf_url}) en identificeer concrete ontwikkelkansen.

        Focus op het vinden van:
        1. Specifieke ontwikkellocaties of gebieden
        2. Toekomstige ontwikkelplannen
        3. Bestemmingswijzigingen of transformaties
        4. Timeline van ontwikkelingen (2024-2030)
        5. Eisen en voorwaarden voor ontwikkeling

        Voor elke ontwikkelkans, geef:
        - Exacte locatie/gebied
        - Type ontwikkeling dat is toegestaan
        - Huidige status
        - Planning indien genoemd
        - Omvang/schaal indien genoemd
        - Speciale voorwaarden of eisen

        Format als JSON met deze keys:
        - document_type: type document (omgevingsvisie, bestemmingsplan, etc.)
        - opportunities: lijst van ontwikkelkansen
        - key_areas: lijst van prioritaire ontwikkelgebieden
        - zoning_changes: lijst van geplande bestemmingswijzigingen
        - relevant_policies: lijst van relevante ontwikkelingsregels
        """

        try:
            # Split content into chunks if it's too long
            chunks = [pdf_content[i:i + 4000] for i in range(0, len(pdf_content), 4000)]
            self.logger.info(f"Document split into {len(chunks)} chunks for analysis")
            all_analyses = []

            for i, chunk in enumerate(chunks[:5]):  # Analyze first 5 chunks (20K chars)
                self.logger.info(f"Analyzing chunk {i+1}/{len(chunks)}")
                response = self.client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": "Je bent een Nederlandse stedenbouwkundige expert die gemeentelijke planningsdocumenten analyseert."},
                        {"role": "user", "content": prompt},
                        {"role": "user", "content": f"Document deel {i+1}/{len(chunks)}: {chunk}"}
                    ],
                    response_format={ "type": "json_object" }
                )
                
                analysis = json.loads(response.choices[0].message.content)
                self.logger.info(f"Chunk {i+1} analysis complete. Found {len(analysis.get('opportunities', []))} opportunities")
                all_analyses.append(analysis)

            # Combine analyses from different chunks
            combined_analysis = self.combine_pdf_analyses(all_analyses)
            self.logger.info(f"""
            Analysis complete for {pdf_title}:
            - Total opportunities found: {len(combined_analysis.get('opportunities', []))}
            - Key areas identified: {len(combined_analysis.get('key_areas', []))}
            - Zoning changes found: {len(combined_analysis.get('zoning_changes', []))}
            - Relevant policies: {len(combined_analysis.get('relevant_policies', []))}
            """)
            return combined_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing PDF content: {str(e)}")
            return {"opportunities": [], "key_areas": [], "zoning_changes": []}

    def extract_text(self, html: str) -> str:
        """Extract readable text from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        return " ".join(soup.stripped_strings)

    def download_pdf(self, url: str) -> str:
        """Download and extract text from PDF"""
        self.logger.info(f"Downloading PDF from: {url}")
        try:
            response = requests.get(url, timeout=30)  # Longer timeout for large PDFs
            if response.status_code == 200:
                # Create a PDF reader object
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Extract text from all pages
                text = ""
                total_pages = len(pdf_reader.pages)
                self.logger.info(f"PDF has {total_pages} pages")
                
                for page_num in range(total_pages):
                    text += pdf_reader.pages[page_num].extract_text() or ""
                    
                self.logger.info(f"Successfully extracted {len(text)} characters of text")
                return text
            else:
                self.logger.error(f"Failed to download PDF: HTTP {response.status_code}")
                return ""
        except Exception as e:
            self.logger.error(f"Error downloading/processing PDF: {str(e)}")
            return ""

    def extract_title(self, html: str) -> str:
        """Extract page title from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.title.string if soup.title else "No title"
    
    def combine_pdf_analyses(self, analyses: List[Dict]) -> Dict:
        """Combine analyses from different chunks of the same PDF"""
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
            
            # Add unique areas
            combined["key_areas"].extend([
                area for area in analysis.get("key_areas", [])
                if area not in combined["key_areas"]
            ])
            
            # Add unique zoning changes
            combined["zoning_changes"].extend([
                change for change in analysis.get("zoning_changes", [])
                if change not in combined["zoning_changes"]
            ])
            
            # Add unique policies
            combined["relevant_policies"].extend([
                policy for policy in analysis.get("relevant_policies", [])
                if policy not in combined["relevant_policies"]
            ])

        return combined

    def save_pdf_analysis(self, analysis: Dict, gemeente: str, pdf_title: str):
        """Save PDF analysis results"""
        output_dir = os.path.join('data', 'processed', gemeente, 'pdf_analyses')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON analysis
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{pdf_title.replace(' ', '_')}_{timestamp}.json"
        
        with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Save human-readable summary
        with open(os.path.join(output_dir, f"{pdf_title.replace(' ', '_')}_{timestamp}_summary.txt"), 'w', encoding='utf-8') as f:
            f.write(f"Analysis of {pdf_title}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("Document Type: " + analysis['document_type'] + "\n\n")
            
            f.write("Development Opportunities:\n")
            f.write("-" * 30 + "\n")
            for opp in analysis['opportunities']:
                f.write(f"Location: {opp.get('location', 'Unknown')}\n")
                f.write(f"Type: {opp.get('type', 'Unknown')}\n")
                f.write(f"Status: {opp.get('status', 'Unknown')}\n")
                if 'timeline' in opp:
                    f.write(f"Timeline: {opp['timeline']}\n")
                if 'size' in opp:
                    f.write(f"Size: {opp['size']}\n")
                if 'conditions' in opp:
                    f.write("Conditions:\n")
                    for condition in opp['conditions']:
                        f.write(f"- {condition}\n")
                f.write("\n")

            if analysis['key_areas']:
                f.write("\nKey Development Areas:\n")
                f.write("-" * 30 + "\n")
                for area in analysis['key_areas']:
                    f.write(f"- {area}\n")

            if analysis['zoning_changes']:
                f.write("\nPlanned Zoning Changes:\n")
                f.write("-" * 30 + "\n")
                for change in analysis['zoning_changes']:
                    f.write(f"- {change}\n")

            if analysis['relevant_policies']:
                f.write("\nRelevant Development Policies:\n")
                f.write("-" * 30 + "\n")
                for policy in analysis['relevant_policies']:
                    f.write(f"- {policy}\n")

    def save_results(self, results: Dict, gemeente: str):
        """Save scraped results"""
        output_dir = os.path.join('data', 'raw', gemeente)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save as JSON for easier processing
        with open(os.path.join(output_dir, 'scraping_results.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save human-readable summary
        with open(os.path.join(output_dir, 'development_summary.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Development Opportunities in {gemeente}\n")
            f.write("=" * 50 + "\n\n")
            
            for page in results['relevant_pages']:
                f.write(f"Source: {page['url']}\n")
                f.write(f"Title: {page['title']}\n")
                
                analysis = page['analysis']
                if 'locations' in analysis:
                    f.write("\nLocations mentioned:\n")
                    for loc in analysis['locations']:
                        f.write(f"- {loc}\n")
                
                if 'key_details' in analysis:
                    f.write("\nKey Details:\n")
                    for detail in analysis['key_details']:
                        f.write(f"- {detail}\n")
                
                f.write("\n" + "-" * 50 + "\n\n")

def main():
    # Test the scraper
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return
        
    scraper = IntelligentScraper(os.getenv("OPENAI_API_KEY"))
    gemeente = "Amsterdam"
    
    print(f"Starting intelligent scrape for {gemeente}")
    results = scraper.scrape_gemeente(gemeente)
    
    print("\nResults found:")
    print(f"Relevant pages: {len(results['relevant_pages'])}")
    print(f"Development opportunities: {len(results['development_opportunities'])}")
    print(f"Key documents: {len(results['key_documents'])}")

if __name__ == "__main__":
    # Add test before running main scraper
    if test_openai_connection():
        main()
    else:
        print("Failed to initialize OpenAI connection. Please check your API key and try again.")