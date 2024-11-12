import logging
from typing import Dict, List
import os
from datetime import datetime

# Fix imports to use absolute paths from project root
from src.scrapers.url_discoverer import URLDiscoverer
from src.scrapers.pdf_handler import PDFHandler
from src.scrapers.document_analyzer import DocumentAnalyzer
from src.scrapers.gpt_analyzer import GPTAnalyzer
from src.scrapers.image_map_analyzer import ImageMapAnalyzer

class MasterController:
    """Controls and orchestrates all components of the system"""
    
    def __init__(self, openai_api_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
        # Initialize components
        self.url_discoverer = URLDiscoverer()  # This one doesn't need the API key
        self.pdf_handler = PDFHandler(openai_api_key=openai_api_key)
        self.document_analyzer = DocumentAnalyzer(openai_api_key=openai_api_key)
        self.gpt_analyzer = GPTAnalyzer(openai_api_key=openai_api_key)
        self.image_analyzer = ImageMapAnalyzer(openai_api_key=openai_api_key)

    def analyze_gemeente(self, gemeente: str) -> Dict:
        """Complete analysis process for a gemeente"""
        results = {
            'gemeente': gemeente,
            'timestamp': datetime.now().isoformat(),
            'discovered_urls': [],
            'analyzed_documents': [],
            'development_opportunities': [],
            'visual_analyses': []
        }
        
        try:
            # 1. Discover URLs
            self.logger.info(f"Starting URL discovery for {gemeente}")
            urls = self.url_discoverer.discover_urls(gemeente)
            results['discovered_urls'] = urls
            
            # 2. Process each discovered URL
            for url_info in urls['google_results'] + urls['municipality_urls']:
                try:
                    # Handle different types of URLs
                    if url_info['type'] == 'pdf':
                        self._process_pdf(url_info, gemeente, results)
                    else:
                        self._process_webpage(url_info, gemeente, results)
                except Exception as e:
                    self.logger.error(f"Error processing URL {url_info['url']}: {str(e)}")
            
            # 3. Consolidate opportunities
            results['development_opportunities'] = self._consolidate_opportunities(results)
            
            # 4. Save final results
            self._save_results(results, gemeente)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing {gemeente}: {str(e)}")
            return results

    def _process_pdf(self, url_info: Dict, gemeente: str, results: Dict):
        """Process a PDF document"""
        self.logger.info(f"Processing PDF: {url_info['url']}")
        
        # Download and process PDF
        pdf_info = self.pdf_handler.process_pdf_with_analysis(url_info['url'], gemeente)
        
        if pdf_info['success']:
            # Analyze document content
            doc_analysis = self.document_analyzer.analyze_document(
                content=pdf_info['text_content'],
                url=url_info['url'],
                title=pdf_info.get('title', 'Unknown PDF'),
                document_type=None  # Let analyzer detect type
            )
            
            # Analyze visuals if available
            if pdf_info.get('saved_paths', {}).get('pdf_path'):
                visual_analysis = self.image_analyzer.analyze_pdf_visuals(
                    pdf_info['saved_paths']['pdf_path'],
                    gemeente
                )
                results['visual_analyses'].append(visual_analysis)
            
            # Store analysis
            results['analyzed_documents'].append({
                'url': url_info['url'],
                'type': 'pdf',
                'analysis': doc_analysis
            })

    def _process_webpage(self, url_info: Dict, gemeente: str, results: Dict):
        """Process a webpage"""
        self.logger.info(f"Processing webpage: {url_info['url']}")
        
        try:
            # Get webpage content
            response = self.pdf_handler.session.get(url_info['url'])
            if response.status_code == 200:
                # Extract text
                text_content = self.pdf_handler.extract_text(response.text)
                
                # Analyze content
                text_analysis = self.gpt_analyzer.analyze_text(
                    text=text_content,
                    url=url_info['url'],
                    context=f"Webpage from {gemeente}"
                )
                
                if text_analysis.get('is_relevant'):
                    # Full document analysis if relevant
                    doc_analysis = self.document_analyzer.analyze_document(
                        content=text_content,
                        url=url_info['url'],
                        title=self.pdf_handler.extract_title(response.text)
                    )
                    
                    results['analyzed_documents'].append({
                        'url': url_info['url'],
                        'type': 'webpage',
                        'analysis': doc_analysis
                    })
        
        except Exception as e:
            self.logger.error(f"Error processing webpage {url_info['url']}: {str(e)}")

    def _consolidate_opportunities(self, results: Dict) -> List[Dict]:
        """Consolidate all found opportunities"""
        opportunities = []
        seen_locations = set()
        
        # Collect opportunities from all analyses
        for doc in results['analyzed_documents']:
            for opp in doc['analysis'].get('opportunities', []):
                location = opp.get('location')
                if location and location not in seen_locations:
                    seen_locations.add(location)
                    
                    # Enrich with visual analysis if available
                    visual_info = self._find_visual_info(location, results['visual_analyses'])
                    if visual_info:
                        opp['visual_analysis'] = visual_info
                    
                    opportunities.append(opp)
        
        return opportunities

    def _find_visual_info(self, location: str, visual_analyses: List[Dict]) -> Dict:
        """Find visual information for a location"""
        for analysis in visual_analyses:
            for map_info in analysis.get('maps', []):
                if location.lower() in map_info['analysis'].lower():
                    return map_info
        return None

    def _save_results(self, results: Dict, gemeente: str):
        """Save final analysis results"""
        output_dir = os.path.join('data', 'processed', gemeente, 'final_analysis')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON results
        import json
        json_path = os.path.join(output_dir, f"analysis_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save human-readable summary
        summary_path = os.path.join(output_dir, f"analysis_{timestamp}.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            self._write_summary(f, results)

    def _write_summary(self, file, results: Dict):
        """Write human-readable summary"""
        file.write(f"Development Analysis for {results['gemeente']}\n")
        file.write("=" * 50 + "\n\n")
        
        # URLs found
        file.write(f"URLs Analyzed: {len(results['discovered_urls'])}\n")
        file.write(f"Documents Processed: {len(results['analyzed_documents'])}\n")
        file.write(f"Development Opportunities Found: {len(results['development_opportunities'])}\n\n")
        
        # Development Opportunities
        file.write("Development Opportunities:\n")
        file.write("-" * 30 + "\n")
        for opp in results['development_opportunities']:
            file.write(f"\nLocation: {opp.get('location', 'Unknown')}\n")
            if 'type' in opp:
                file.write(f"Type: {opp['type']}\n")
            if 'status' in opp:
                file.write(f"Status: {opp['status']}\n")
            if 'size' in opp:
                file.write(f"Size: {opp['size']}\n")
            if 'visual_analysis' in opp:
                file.write("Visual Analysis Available\n")
            file.write("\n")

def main():
    """Test the master controller"""
    controller = MasterController(os.getenv("OPENAI_API_KEY"))
    
    # Test with a gemeente
    gemeente = "Amsterdam"
    results = controller.analyze_gemeente(gemeente)
    
    print(f"Analysis complete for {gemeente}")
    print(f"Found {len(results['development_opportunities'])} opportunities")

if __name__ == "__main__":
    main()
