import logging
from typing import Dict, List
import os
from datetime import datetime
from src.scrapers.gpt_analyzer import GPTAnalyzer
from src.scrapers.pdf_handler import PDFHandler



class DocumentAnalyzer:
    """Analyzes municipal documents for development opportunities"""
    
    def __init__(self, openai_api_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.gpt_analyzer = GPTAnalyzer(openai_api_key)
        self.pdf_handler = PDFHandler(openai_api_key)
        
        # Document type patterns
        self.document_types = {
            'omgevingsvisie': [
                'omgevingsvisie', 
                'toekomstvisie', 
                'structuurvisie'
            ],
            'bestemmingsplan': [
                'bestemmingsplan', 
                'omgevingsplan', 
                'ruimtelijk plan'
            ],
            'gebiedsvisie': [
                'gebiedsvisie', 
                'gebiedsontwikkeling', 
                'ontwikkelvisie'
            ],
            'woningbouw': [
                'woonvisie', 
                'woningbouwprogramma', 
                'huisvestingsplan'
            ]
        }
        
        # Development indicators
        self.development_indicators = {
            'location_patterns': [
                r'locatie:?\s*([A-Z][a-zA-Z\s\-]+)',
                r'gebied:?\s*([A-Z][a-zA-Z\s\-]+)',
                r'in de ([A-Z][a-zA-Z\s\-]+(?:buurt|wijk|gebied))'
            ],
            'size_patterns': [
                r'(\d+[\d\.,]*)\s*(?:m2|m²|ha)\b',
                r'(\d+[\d\.,]*)\s*woningen\b',
                r'oppervlakte van (\d+[\d\.,]*)'
            ],
            'timeline_patterns': [
                r'(?:start|begin|aanvang)[\s:]+(Q\d\s+\d{4}|\d{4})',
                r'planning[\s:]+(Q\d\s+\d{4}|\d{4})',
                r'oplevering[\s:]+(Q\d\s+\d{4}|\d{4})'
            ]
        }

    def detect_document_type(self, title: str, content: str) -> str:
        """Detect the type of municipal document"""
        title_lower = title.lower()
        content_lower = content.lower()[:1000]  # Check first 1000 chars
        
        for doc_type, patterns in self.document_types.items():
            if any(pattern in title_lower for pattern in patterns):
                return doc_type
            if any(pattern in content_lower for pattern in patterns):
                return doc_type
        
        return 'other'

    def analyze_document(self, content: str, url: str = None, title: str = None, 
                        document_type: str = None) -> Dict:
        """Analyze a document for development opportunities"""
        self.logger.info(f"Analyzing document: {title or url}")
        
        # Detect document type if not provided
        if not document_type:
            document_type = self.detect_document_type(title or url, content)
        
        # Get GPT analysis
        gpt_analysis = self.gpt_analyzer.analyze_document(
            content=content,
            title=title,
            url=url,
            doc_type=document_type
        )
        
        # Extract structured information
        structured_info = self.extract_structured_info(content)
        
        # Combine analyses
        result = {
            'document_info': {
                'title': title,
                'url': url,
                'type': document_type,
                'analyzed_at': datetime.now().isoformat()
            },
            'gpt_analysis': gpt_analysis,
            'structured_info': structured_info,
            'opportunities': self.combine_opportunities(gpt_analysis, structured_info)
        }
        
        return result

    def extract_structured_info(self, content: str) -> Dict:
        """Extract structured information using patterns"""
        import re
        
        result = {
            'locations': [],
            'sizes': [],
            'timelines': [],
            'developments': []
        }
        
        # Extract using patterns
        for pattern in self.development_indicators['location_patterns']:
            matches = re.finditer(pattern, content)
            result['locations'].extend([m.group(1) for m in matches])
        
        for pattern in self.development_indicators['size_patterns']:
            matches = re.finditer(pattern, content)
            result['sizes'].extend([m.group(1) for m in matches])
        
        for pattern in self.development_indicators['timeline_patterns']:
            matches = re.finditer(pattern, content)
            result['timelines'].extend([m.group(1) for m in matches])
        
        return result

    def combine_opportunities(self, gpt_analysis: Dict, structured_info: Dict) -> List[Dict]:
        """Combine GPT and structured analysis into opportunities"""
        opportunities = []
        
        # Start with GPT-identified opportunities
        for opp in gpt_analysis.get('opportunities', []):
            opportunity = {
                'location': opp.get('location'),
                'type': opp.get('type'),
                'status': opp.get('status'),
                'source': 'gpt_analysis',
                'confidence': 'high'
            }
            
            # Add structured info if location matches
            if opportunity['location'] in structured_info['locations']:
                # Find related size and timeline info
                idx = structured_info['locations'].index(opportunity['location'])
                if idx < len(structured_info['sizes']):
                    opportunity['size'] = structured_info['sizes'][idx]
                if idx < len(structured_info['timelines']):
                    opportunity['timeline'] = structured_info['timelines'][idx]
            
            opportunities.append(opportunity)
        
        # Add opportunities from structured info not found by GPT
        for idx, location in enumerate(structured_info['locations']):
            if location not in [opp['location'] for opp in opportunities]:
                opportunity = {
                    'location': location,
                    'source': 'structured_analysis',
                    'confidence': 'medium'
                }
                
                if idx < len(structured_info['sizes']):
                    opportunity['size'] = structured_info['sizes'][idx]
                if idx < len(structured_info['timelines']):
                    opportunity['timeline'] = structured_info['timelines'][idx]
                
                opportunities.append(opportunity)
        
        return opportunities

    def save_analysis(self, analysis: Dict, gemeente: str, document_id: str):
        """Save analysis results"""
        # Create output directory
        output_dir = os.path.join('data', 'processed', gemeente, 'analyses')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON analysis
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(output_dir, f"analysis_{document_id}_{timestamp}.json")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Save human-readable summary
        summary_path = os.path.join(output_dir, f"analysis_{document_id}_{timestamp}.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            self._write_summary(f, analysis)
        
        return {
            'json_path': json_path,
            'summary_path': summary_path
        }

    def _write_summary(self, file, analysis: Dict):
        """Write human-readable summary"""
        file.write("Document Analysis Summary\n")
        file.write("=" * 50 + "\n\n")
        
        # Document info
        doc_info = analysis['document_info']
        file.write(f"Title: {doc_info['title']}\n")
        file.write(f"Type: {doc_info['type']}\n")
        file.write(f"URL: {doc_info['url']}\n\n")
        
        # Development Opportunities
        file.write("Development Opportunities\n")
        file.write("-" * 30 + "\n")
        for opp in analysis['opportunities']:
            file.write(f"\nLocation: {opp.get('location', 'Unknown')}\n")
            if 'type' in opp:
                file.write(f"Type: {opp['type']}\n")
            if 'status' in opp:
                file.write(f"Status: {opp['status']}\n")
            if 'size' in opp:
                file.write(f"Size: {opp['size']}\n")
            if 'timeline' in opp:
                file.write(f"Timeline: {opp['timeline']}\n")
            file.write(f"Confidence: {opp.get('confidence', 'unknown')}\n")
        
        # Structured Information
        file.write("\nStructured Information\n")
        file.write("-" * 30 + "\n")
        structured = analysis['structured_info']
        if structured['locations']:
            file.write("\nLocations found:\n")
            for loc in structured['locations']:
                file.write(f"- {loc}\n")
        if structured['sizes']:
            file.write("\nSizes mentioned:\n")
            for size in structured['sizes']:
                file.write(f"- {size}\n")
        if structured['timelines']:
            file.write("\nTimelines mentioned:\n")
            for timeline in structured['timelines']:
                file.write(f"- {timeline}\n")

def main():
    """Test the document analyzer"""
    analyzer = DocumentAnalyzer(os.getenv("OPENAI_API_KEY"))
    
    # Test with a sample document
    pdf_handler = PDFHandler()
    pdf_info = pdf_handler.download_pdf("https://example.com/test.pdf")
    
    if pdf_info['success']:
        analysis = analyzer.analyze_document(
            content=pdf_info['text_content'],
            url=pdf_info['url'],
            title="Test Document"
        )
        
        # Save analysis
        saved_paths = analyzer.save_analysis(analysis, "Amsterdam", "test_doc")
        print(f"Analysis saved to {saved_paths['summary_path']}")
        print(f"Found {len(analysis['opportunities'])} opportunities")

if __name__ == "__main__":
    main()