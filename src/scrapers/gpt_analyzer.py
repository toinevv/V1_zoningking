from typing import List, Dict
import logging
import json
from openai import OpenAI
from datetime import datetime
import os

class GPTAnalyzer:
    """Handles all GPT-based analysis of content"""

    def __init__(self, openai_api_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
        # Initialize OpenAI client
        try:
            if not self.openai_api_key:  # Use self.openai_api_key instead of api_key
                self.openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if not self.openai_api_key:
                raise ValueError("No OpenAI API key provided")
                
            self.client = OpenAI(api_key=self.openai_api_key)  # Use self.openai_api_key
            self.logger.info("GPT Analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize GPT Analyzer: {str(e)}")
            raise Exception("Failed to initialize GPT Analyzer. Check your API key.")
    
    def analyze_text(self, text: str, url: str = None, context: str = None) -> Dict:
        """Analyze any text content for development opportunities"""
        prompt = f"""
        Analyseer deze tekst{f' van {url}' if url else ''} voor vastgoed ontwikkelkansen.
        {f'Context: {context}' if context else ''}

        Focus op het vinden van:
        1. Specifieke locaties/gebieden voor ontwikkeling
        2. Type ontwikkelingen die mogelijk zijn
        3. Status en timeline van ontwikkelingen
        4. Omvang/schaal van ontwikkelingen
        5. Voorwaarden en bestemmingsplan informatie

        Geef terug als JSON met deze keys:
        - is_relevant: boolean (of er ontwikkelkansen in de tekst staan)
        - locations: lijst van specifieke locaties
        - development_types: lijst van type ontwikkelingen
        - status: huidige status van ontwikkelingen
        - key_details: lijst van belangrijke details
        - opportunities: lijst van concrete ontwikkelkansen
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "Je bent een Nederlandse vastgoed ontwikkelingsexpert die teksten analyseert voor concrete ontwikkelkansen."},
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": text[:4000]}  # First 4000 chars
                ],
                response_format={ "type": "json_object" }
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Error in text analysis: {str(e)}")
            return {
                "is_relevant": False,
                "locations": [],
                "development_types": [],
                "status": "unknown",
                "key_details": [],
                "opportunities": []
            }

    def analyze_document(self, content: str, title: str, url: str = None, doc_type: str = None) -> Dict:
        """Analyze official documents (like omgevingsvisie)"""
        prompt = f"""
        Analyseer dit {doc_type or 'gemeentelijk'} document: '{title}'
        {f'Bron: {url}' if url else ''}

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
        - opportunities: lijst van concrete ontwikkelkansen
        - key_areas: lijst van prioritaire ontwikkelgebieden
        - zoning_changes: lijst van geplande bestemmingswijzigingen
        - relevant_policies: lijst van relevante ontwikkelingsregels
        """

        try:
            # Split content into chunks if it's too long
            chunks = [content[i:i + 4000] for i in range(0, len(content), 4000)]
            self.logger.info(f"Analyzing {title} in {len(chunks)} chunks")
            
            all_analyses = []
            for i, chunk in enumerate(chunks[:5]):  # Analyze first 5 chunks
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
                
                chunk_analysis = json.loads(response.choices[0].message.content)
                all_analyses.append(chunk_analysis)
            
            combined = self.combine_analyses(all_analyses)
            self.logger.info(f"Analysis complete for {title}")
            self.logger.info(f"Found {len(combined.get('opportunities', []))} opportunities")
            
            return combined

        except Exception as e:
            self.logger.error(f"Error in document analysis: {str(e)}")
            return {
                "document_type": doc_type or "unknown",
                "opportunities": [],
                "key_areas": [],
                "zoning_changes": [],
                "relevant_policies": []
            }

    def combine_analyses(self, analyses: List[Dict]) -> Dict:
        """Combine analyses from different chunks"""
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

    def save_analysis(self, analysis: Dict, output_path: str, title: str):
        """Save analysis results"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_path = os.path.join(output_path, f"{title.replace(' ', '_')}_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Save readable summary
        summary_path = os.path.join(output_path, f"{title.replace(' ', '_')}_{timestamp}_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            self._write_summary(f, title, analysis)
        
        return json_path, summary_path

    def _write_summary(self, file, title: str, analysis: Dict):
        """Write human-readable summary"""
        file.write(f"Analysis of {title}\n")
        file.write("=" * 50 + "\n\n")
        
        file.write(f"Document Type: {analysis['document_type']}\n\n")
        
        if analysis.get('opportunities'):
            file.write("Development Opportunities:\n")
            file.write("-" * 30 + "\n")
            for opp in analysis['opportunities']:
                file.write(f"Location: {opp.get('location', 'Unknown')}\n")
                file.write(f"Type: {opp.get('type', 'Unknown')}\n")
                file.write(f"Status: {opp.get('status', 'Unknown')}\n")
                if 'timeline' in opp:
                    file.write(f"Timeline: {opp['timeline']}\n")
                if 'size' in opp:
                    file.write(f"Size: {opp['size']}\n")
                if 'conditions' in opp:
                    file.write("Conditions:\n")
                    for condition in opp['conditions']:
                        file.write(f"- {condition}\n")
                file.write("\n")

        self._write_section(file, "Key Development Areas", analysis.get('key_areas', []))
        self._write_section(file, "Planned Zoning Changes", analysis.get('zoning_changes', []))
        self._write_section(file, "Relevant Development Policies", analysis.get('relevant_policies', []))

    def _write_section(self, file, title: str, items: List[str]):
        """Helper to write a section of the summary"""
        if items:
            file.write(f"\n{title}:\n")
            file.write("-" * 30 + "\n")
            for item in items:
                file.write(f"- {item}\n")