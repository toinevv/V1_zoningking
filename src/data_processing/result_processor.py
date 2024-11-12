import pandas as pd
import os
from typing import List, Dict
import re
from datetime import datetime
import logging

class DevelopmentOpportunityProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.development_indicators = {
            'high_priority': [
                'ontwikkellocatie',
                'transformatiegebied',
                'herontwikkeling',
                'bestemmingswijziging',
                'woningbouw',
                'gebiedsontwikkeling'
            ],
            'location_indicators': [
                r'(?:aan de|nabij|op)\s+([A-Z][a-zA-Z\s-]+(?:straat|weg|plein|laan))',
                r'(?:in|op)\s+(?:de|het)\s+([A-Z][a-zA-Z\s-]+(?:gebied|wijk|buurt|kwartier))',
                r'(?:gebied|terrein|locatie)\s+([A-Z][a-zA-Z\s-]+)',
                r'([A-Z][a-zA-Z\s-]+(?:buurt|wijk|gebied|kwartier))'
            ],
            'size_patterns': [
                r'(\d+(?:,\d+)?)\s*(?:m2|vierkante meter|hectare|ha)\b',
                r'(\d+(?:,\d+)?)\s*woningen\b'
            ],
            'status_indicators': [
                'vergunning mogelijk',
                'bestemmingsplan wijziging',
                'in ontwikkeling',
                'transformatie mogelijk',
                'herontwikkeling mogelijk'
            ]
        }

    def process_gemeente_results(self, gemeente: str, base_dir: str = 'data') -> List[Dict]:
        """Process all results for a gemeente to identify opportunities"""
        self.logger.info(f"Processing results for {gemeente}")
        opportunities = []
        
        # Construct path to scraped data
        gemeente_dir = os.path.join(base_dir, 'scraped', gemeente)
        
        if not os.path.exists(gemeente_dir):
            self.logger.warning(f"No data directory found for {gemeente}")
            return opportunities

        # Find most recent results file
        search_results_files = [f for f in os.listdir(gemeente_dir) if f.startswith('search_results_')]
        if not search_results_files:
            self.logger.warning("No search results files found")
            return opportunities

        latest_file = max(search_results_files)
        file_path = os.path.join(gemeente_dir, latest_file)
        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            self.logger.info(f"Processing {len(df)} results from {latest_file}")
            
            # Process each row
            for _, row in df.iterrows():
                opportunity = self.identify_opportunity(row)
                if opportunity:
                    opportunities.append(opportunity)
            
            # Save opportunities
            if opportunities:
                self.save_opportunities(opportunities, gemeente, base_dir)
            
            self.logger.info(f"Found {len(opportunities)} opportunities")
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            return opportunities

    def identify_opportunity(self, row: pd.Series) -> Dict:
        """Identify if a result contains a development opportunity"""
        try:
            content = str(row.get('content', '')).lower()
            title = str(row.get('title', '')).lower()
            url = str(row.get('url', ''))
            
            # Check for high priority indicators
            priority_matches = [word for word in self.development_indicators['high_priority'] 
                              if word in content or word in title]
            
            if priority_matches:
                # Look for location information
                location = None
                for pattern in self.development_indicators['location_indicators']:
                    matches = re.findall(pattern, str(row.get('content', '')))
                    if matches:
                        location = matches[0]
                        break
                
                # Look for size information
                size = None
                for pattern in self.development_indicators['size_patterns']:
                    matches = re.findall(pattern, str(row.get('content', '')))
                    if matches:
                        size = matches[0]
                        break
                
                # Look for status indicators
                status_matches = [status for status in self.development_indicators['status_indicators']
                                if status in content]
                
                if location or len(priority_matches) >= 2:  # If we have a location or multiple indicators
                    opportunity = {
                        'title': row.get('title', 'Untitled'),
                        'location': location or 'Location not specified',
                        'size': size,
                        'type': self.determine_type(content),
                        'priority_indicators': priority_matches,
                        'status': status_matches[0] if status_matches else 'Status unknown',
                        'source_url': url,
                        'confidence_score': self.calculate_confidence(content, priority_matches, bool(location), bool(size)),
                        'date_found': datetime.now().strftime('%Y-%m-%d')
                    }
                    return opportunity
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing row: {str(e)}")
            return None

    def determine_type(self, text: str) -> str:
        """Determine the type of development opportunity"""
        if 'woningbouw' in text or 'appartementen' in text or 'wonen' in text:
            return 'Residential'
        elif 'kantoor' in text or 'bedrijfs' in text:
            return 'Commercial'
        elif 'gemengd' in text or 'multi' in text:
            return 'Mixed-Use'
        elif 'transformatie' in text:
            return 'Transformation'
        else:
            return 'Development'

    def calculate_confidence(self, text: str, indicators: List[str], has_location: bool, has_size: bool) -> float:
        """Calculate a confidence score for the opportunity"""
        score = len(indicators) * 15  # Base score from priority indicators
        
        # Additional factors
        if has_location:
            score += 25
        if has_size:
            score += 15
        if 'bestemmingsplan' in text:
            score += 15
        if 'omgevingsvisie' in text:
            score += 10
        if any(status in text for status in self.development_indicators['status_indicators']):
            score += 20
        
        return min(100, score)  # Cap at 100

    def save_opportunities(self, opportunities: List[Dict], gemeente: str, base_dir: str):
        """Save identified opportunities to CSV"""
        if not opportunities:
            return
            
        # Create output directory
        output_dir = os.path.join(base_dir, 'processed', gemeente)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'opportunities_{timestamp}.csv')
        
        df = pd.DataFrame(opportunities)
        df.to_csv(filename, index=False, encoding='utf-8')
        self.logger.info(f"Saved {len(opportunities)} opportunities to {filename}")

def main():
    # Test the processor
    processor = DevelopmentOpportunityProcessor()
    gemeente = "Amsterdam"
    
    opportunities = processor.process_gemeente_results(gemeente)
    
    print(f"\nFound {len(opportunities)} opportunities:")
    for opp in opportunities:
        print(f"\nLocation: {opp['location']}")
        print(f"Type: {opp['type']}")
        print(f"Confidence: {opp['confidence_score']}")
        print(f"Indicators: {', '.join(opp['priority_indicators'])}")

if __name__ == "__main__":
    main()