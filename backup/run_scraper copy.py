from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
import sys
import logging
import argparse
import time
from pathlib import Path

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.scrapers.municipality_development_scraper import MunicipalityDevelopmentScraper
from src.scrapers.intelligent_scraper import IntelligentScraper

def setup_logging():
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraping.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def scrape_gemeente(gemeente: str, logger):
    """Run complete scraping process using both methods"""
    try:
        results = {
            'structured': {},
            'intelligent': {},
            'combined_opportunities': []
        }
        
        # 1. Run structured scraping
        logger.info(f"Starting structured scraping for {gemeente}")
        structured_scraper = MunicipalityDevelopmentScraper()
        results['structured'] = structured_scraper.scrape_municipality(gemeente)
        
        # 2. Run intelligent scraping if OpenAI key is available
        if os.getenv("OPENAI_API_KEY"):
            logger.info(f"Starting intelligent scraping for {gemeente}")
            intelligent_scraper = IntelligentScraper(os.getenv("OPENAI_API_KEY"))
            results['intelligent'] = intelligent_scraper.scrape_gemeente(gemeente)
        else:
            logger.warning("Skipping intelligent scraping - no OpenAI API key found")
        
        # 3. Combine and deduplicate results
        combine_results(results, gemeente)
        
        # Log summary
        log_results_summary(results, gemeente, logger)
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing {gemeente}: {str(e)}")
        return None

def combine_results(results: dict, gemeente: str):
    """Combine and deduplicate results from both scrapers"""
    all_opportunities = []
    seen_urls = set()
    
    # Add structured results
    if results['structured'].get('development_areas'):
        for area in results['structured']['development_areas']:
            if area.get('url') not in seen_urls:
                seen_urls.add(area.get('url'))
                all_opportunities.append({
                    'source': 'structured',
                    'data': area
                })
    
    # Add intelligent results
    if results['intelligent'].get('relevant_pages'):
        for page in results['intelligent']['relevant_pages']:
            if page['url'] not in seen_urls:
                seen_urls.add(page['url'])
                all_opportunities.append({
                    'source': 'intelligent',
                    'data': page
                })
    
    results['combined_opportunities'] = all_opportunities
    
    # Save combined results
    save_combined_results(results, gemeente)

def save_combined_results(results: dict, gemeente: str):
    """Save combined results in a clear format"""
    output_dir = os.path.join('data', 'processed', gemeente)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'combined_opportunities.txt'), 'w', encoding='utf-8') as f:
        f.write(f"Development Opportunities in {gemeente}\n")
        f.write("=" * 50 + "\n\n")
        
        for opp in results['combined_opportunities']:
            f.write(f"Source: {opp['source']}\n")
            
            if opp['source'] == 'structured':
                f.write(f"Area: {opp['data'].get('name', 'Unknown')}\n")
                if 'keywords_found' in opp['data']:
                    f.write(f"Keywords: {', '.join(opp['data']['keywords_found'])}\n")
            else:
                f.write(f"Title: {opp['data'].get('title', 'Unknown')}\n")
                if 'analysis' in opp['data']:
                    analysis = opp['data']['analysis']
                    if 'locations' in analysis:
                        f.write("\nLocations:\n")
                        for loc in analysis['locations']:
                            f.write(f"- {loc}\n")
            
            f.write("\n" + "-" * 50 + "\n\n")

def log_results_summary(results: dict, gemeente: str, logger):
    """Log summary of results"""
    logger.info(f"\nResults summary for {gemeente}:")
    
    if results['structured']:
        logger.info("Structured scraping results:")
        logger.info(f"- Development pages: {len(results['structured'].get('development_pages', []))}")
        logger.info(f"- PDF documents: {len(results['structured'].get('pdf_documents', []))}")
        logger.info(f"- Development areas: {len(results['structured'].get('development_areas', []))}")
    
    if results['intelligent']:
        logger.info("Intelligent scraping results:")
        logger.info(f"- Relevant pages: {len(results['intelligent'].get('relevant_pages', []))}")
        logger.info(f"- Development opportunities: {len(results['intelligent'].get('development_opportunities', []))}")
    
    logger.info(f"Total combined opportunities: {len(results['combined_opportunities'])}")

def main():
    parser = argparse.ArgumentParser(description='Run comprehensive development scraping')
    parser.add_argument('--gemeente', help='Specific gemeente to scrape')
    parser.add_argument('--all', action='store_true', help='Scrape all gemeentes')
    parser.add_argument('--intelligent-only', action='store_true', help='Use only intelligent scraping')
    parser.add_argument('--structured-only', action='store_true', help='Use only structured scraping')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    # List of gemeentes (you can expand this)
    all_gemeentes = ["Amsterdam", "Rotterdam", "Utrecht"]
    
    if args.gemeente:
        scrape_gemeente(args.gemeente, logger)
    
    elif args.all:
        for gemeente in all_gemeentes:
            logger.info(f"Starting process for {gemeente}")
            scrape_gemeente(gemeente, logger)
            logger.info("Waiting 60 seconds before next gemeente...")
            time.sleep(60)
    
    else:
        print("Please specify either --gemeente or --all")

if __name__ == "__main__":
    main()