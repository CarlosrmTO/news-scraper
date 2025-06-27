"""
Test script for El País scraper.
"""
import sys
import os
import logging
from datetime import datetime, timezone, timedelta

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_el_pais_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

def test_el_pais_scraper():
    """Test the El País scraper."""
    try:
        from competitors.config.el_pais import get_config
        from competitors.scrapers.el_pais_scraper import ElPaisScraper, get_el_pais_articles
        
        # Get the El País configuration
        config = get_config()
        logger.info(f"Testing El País scraper with config: {config['name']}")
        
        # Create a test instance of the scraper
        scraper = ElPaisScraper(config)
        
        # Test fetching RSS entries
        logger.info("Testing RSS feed fetching...")
        entries = scraper.fetch_rss_entries(days_back=1)
        
        if not entries:
            logger.warning("No entries found in the RSS feeds.")
            return False
        
        logger.info(f"Found {len(entries)} recent articles.")
        
        # Display sample article data
        if entries:
            sample = entries[0]
            logger.info("\nSample article data:")
            logger.info(f"Title: {sample.get('title')}")
            logger.info(f"URL: {sample.get('url')}")
            logger.info(f"Published: {sample.get('publish_date')}")
            logger.info(f"Authors: {sample.get('authors')}")
            logger.info(f"Section: {sample.get('section')}")
            logger.info(f"Subsection: {sample.get('subsection')}")
            logger.info(f"Summary: {sample.get('summary', '')[:200]}...")
        
        # Test the exporter
        from competitors.exporters.el_pais_exporter import ElPaisExporter
        
        exporter = ElPaisExporter()
        output_file = exporter.export_articles(entries, config['name'])
        
        if os.path.exists(output_file):
            logger.info(f"Successfully exported articles to: {output_file}")
            
            # Display first few lines of the CSV
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:6]  # Header + first 5 articles
                logger.info("\nCSV file preview:")
                for line in lines:
                    logger.info(line.strip())
            
            return True
        else:
            logger.error("Failed to export articles.")
            return False
            
    except Exception as e:
        logger.error(f"Error testing El País scraper: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting El País scraper test...")
    success = test_el_pais_scraper()
    if success:
        logger.info("El País scraper test completed successfully!")
    else:
        logger.error("El País scraper test failed!")
