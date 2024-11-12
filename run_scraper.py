from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
import argparse
import time
from src.controllers.master_controller import MasterController

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraping.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def process_gemeente(gemeente: str, logger, openai_api_key: str):
    """Process a single gemeente"""
    try:
        logger.info(f"\n{'='*50}\nStarting analysis for {gemeente}\n{'='*50}")
        
        # Initialize master controller
        controller = MasterController(openai_api_key)
        
        # Run full analysis
        results = controller.analyze_gemeente(gemeente)
        
        # Print summary
        logger.info(f"\nAnalysis complete for {gemeente}:")
        logger.info(f"- URLs discovered: {len(results['discovered_urls'])}")
        logger.info(f"- Documents analyzed: {len(results['analyzed_documents'])}")
        logger.info(f"- Development opportunities found: {len(results['development_opportunities'])}")
        
        # Print opportunities
        if results['development_opportunities']:
            logger.info("\nDevelopment Opportunities Found:")
            for i, opp in enumerate(results['development_opportunities'], 1):
                logger.info(f"\n{i}. Location: {opp.get('location', 'Unknown')}")
                logger.info(f"   Type: {opp.get('type', 'Unknown')}")
                logger.info(f"   Status: {opp.get('status', 'Unknown')}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing {gemeente}: {str(e)}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Analyze Dutch municipalities for development opportunities')
    parser.add_argument('--gemeente', help='Specific gemeente to analyze')
    parser.add_argument('--all', action='store_true', help='Analyze all gemeentes')
    parser.add_argument('--limit', type=int, help='Limit number of gemeentes to process')
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("No OpenAI API key found. Please set OPENAI_API_KEY environment variable.")
        return
    
    # List of gemeentes (you can expand this or load from a file)
    all_gemeentes = [
        "Amsterdam", "Rotterdam", "Utrecht", "Den Haag", 
        "Eindhoven", "Groningen", "Tilburg", "Almere"
    ]
    
    if args.gemeente:
        # Process single gemeente
        process_gemeente(args.gemeente, logger, openai_api_key)
        
    elif args.all:
        # Process all gemeentes
        gemeentes = all_gemeentes[:args.limit] if args.limit else all_gemeentes
        
        for i, gemeente in enumerate(gemeentes, 1):
            logger.info(f"\nProcessing gemeente {i}/{len(gemeentes)}: {gemeente}")
            process_gemeente(gemeente, logger, openai_api_key)
            
            # Wait between gemeentes to avoid rate limits
            if i < len(gemeentes):
                logger.info("Waiting 60 seconds before next gemeente...")
                time.sleep(60)
    
    else:
        print("Please specify either --gemeente or --all")
        print("\nExample usage:")
        print("  python run_scraper.py --gemeente Amsterdam")
        print("  python run_scraper.py --all --limit 5")

if __name__ == "__main__":
    main()