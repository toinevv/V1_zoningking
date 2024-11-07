from transformers import pipeline
from typing import Dict, List
import numpy as np

class DevelopmentAnalyzer:
    def __init__(self):
        # Use Dutch BERT model for better Dutch text analysis
        self.sentiment_analyzer = pipeline("sentiment-analysis", 
                                        model="wietsedv/bert-base-dutch-cased")
        
        # Dutch development scoring factors
        self.scoring_factors = {
            'type_bonus': {
                'Wonen': 10,          # High priority due to housing shortage
                'Gemengd': 8,         # Mixed use is favored in Dutch urban planning
                'Commercieel': 6,
                'Kantoor': 4,
                'Transformatie': 12   # Transformation projects often get priority
            },
            'location_bonus': {
                'centrum': 5,
                'station': 5,
                'ov': 3,
                'binnenstad': 4
            },
            'priority_areas': {
                'ontwikkelgebied': 8,
                'focusgebied': 6,
                'prioriteitsgebied': 7
            }
        }
        
        # Dutch positive development indicators
        self.positive_indicators = [
            'verduurzaming',
            'verdichting',
            'bereikbaarheid',
            'leefbaarheid',
            'duurzaam',
            'energieneutraal',
            'klimaatadaptief',
            'innovatief'
        ]

    def analyze_opportunity(self, development_data: Dict) -> Dict:
        """Analyze a single development opportunity."""
        # Analyze sentiment of the Dutch text
        sentiment_results = self.sentiment_analyzer(development_data['bron_tekst'])
        sentiment_score = sentiment_results[0]['score'] if sentiment_results[0]['label'] == 'positive' else -sentiment_results[0]['score']
        
        # Calculate base score
        base_score = 50
        
        # Calculate adjustments
        score_adjustments = {
            'sentiment': sentiment_score * 20,
            'type_bonus': self.scoring_factors['type_bonus'].get(development_data['type'], 0),
            'location_bonus': sum(bonus for keyword, bonus in self.scoring_factors['location_bonus'].items()
                                if keyword in development_data['locatie'].lower()),
            'priority_bonus': sum(bonus for keyword, bonus in self.scoring_factors['priority_areas'].items()
                                if development_data['extra_info'].get(f'is_{keyword}', False)),
            'positive_indicators': sum(2 for indicator in self.positive_indicators
                                    if indicator in development_data['bron_tekst'].lower())
        }
        
        # Add extra bonuses based on Dutch planning specifics
        if development_data['extra_info'].get('heeft_bestemmingsplan'):
            score_adjustments['bestemmingsplan_bonus'] = 5
        if development_data['extra_info'].get('heeft_omgevingsvergunning'):
            score_adjustments['vergunning_bonus'] = 3
        if development_data['extra_info'].get('mentions_woningnood'):
            score_adjustments['woningnood_bonus'] = 4
        
        # Calculate final score
        final_score = base_score + sum(score_adjustments.values())
        final_score = max(0, min(100, final_score))
        
        return {
            **development_data,
            'sentiment_score': sentiment_score,
            'kans_score': round(final_score, 1),
            'score_factoren': score_adjustments
        }

    def analyze_opportunities(self, developments: List[Dict]) -> List[Dict]:
        """Analyze multiple development opportunities."""
        return [self.analyze_opportunity(dev) for dev in developments]