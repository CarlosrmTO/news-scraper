"""
Base exporter class for all competitor exporters.
"""
import csv
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BaseExporter(ABC):
    """Base class for all competitor exporters."""
    
    def __init__(self, output_dir: str = None):
        """Initialize the exporter with output directory.
        
        Args:
            output_dir: Base output directory. If None, will use default location.
        """
        self.output_dir = output_dir or f'output/competitors/{self.get_competitor_name()}'
        os.makedirs(self.output_dir, exist_ok=True)
    
    @classmethod
    @abstractmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        pass
    
    def _export_articles_to_file(self, articles: List[Dict], competitor_name: str = None) -> str:
        """Internal method to export articles to a CSV file.
        
        Args:
            articles: List of article dictionaries to export
            competitor_name: Optional name override for the competitor
            
        Returns:
            str: Path to the exported file
        """
        if not articles:
            logger.warning("No articles to export")
            return ""
            
        # Generate filename with current date
        today = datetime.now().strftime('%Y%m%d')
        competitor = competitor_name or self.get_competitor_name()
        safe_name = "".join(c if c.isalnum() else "_" for c in competitor.lower())
        filename = f"{safe_name}_articles_{today}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # Debug: Print article data directly to console
        if articles:
            print("\n=== DEBUG: Article Data ===")
            print(f"Exporting {len(articles)} articles to {filepath}")
            print("First article data:")
            import pprint
            pprint.pprint(articles[0], indent=2, width=120)
            
            # Check for any missing fields in any article
            all_fields = set()
            for article in articles:
                all_fields.update(article.keys())
            print(f"\nAll fields found in articles: {sorted(all_fields)}")
            print("==========================\n")
        
        # Define field order
        fieldnames = [
            'title',
            'url',
            'publish_date',
            'authors',
            'source',
            'domain',
            'summary',
            'section',
            'subsection'
        ]
        
        try:
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.isfile(filepath) and os.path.getsize(filepath) > 0
            
            # Debug: Log first article data
            if articles:
                logger.debug(f"First article data before export: {articles[0]}")
            
            import unicodedata
            import re
            
            def normalize_text(text):
                """Normalize text to handle special characters and encoding issues."""
                if text is None:
                    return ""
                    
                if not isinstance(text, str):
                    try:
                        text = str(text)
                    except Exception:
                        return ""
                
                try:
                    # First, ensure the text is properly encoded as UTF-8
                    if isinstance(text, bytes):
                        try:
                            # Try UTF-8 first, then fall back to latin-1 if that fails
                            text = text.decode('utf-8', errors='strict')
                        except UnicodeDecodeError:
                            text = text.decode('latin-1', errors='ignore')
                    
                    # Normalize unicode characters to composed form (NFC)
                    text = unicodedata.normalize('NFC', text)
                    
                    # Replace problematic control characters but preserve valid UTF-8
                    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
                    
                    # Normalize line endings and spaces
                    text = text.replace('\r\n', '\n').replace('\r', '\n')
                    
                    # Replace multiple spaces and newlines with a single space
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    # Ensure the text is properly encoded as UTF-8
                    text = text.encode('utf-8', errors='strict').decode('utf-8')
                    
                    return text
                    
                except UnicodeError as e:
                    logger.error(f"Error normalizing text: {e}")
                    # Fallback: remove non-printable characters but preserve Spanish characters
                    return ''.join(
                        c for c in text 
                        if c.isprintable() or c in 'áéíóúüñÁÉÍÓÚÜÑ¿¡ªº'
                    )
                except Exception as e:
                    logger.error(f"Unexpected error normalizing text: {e}")
                    return text  # Return as-is if we can't normalize it
            
            def clean_article(article):
                cleaned = {}
                for key, value in article.items():
                    if isinstance(value, str):
                        cleaned[key] = normalize_text(value)
                    elif isinstance(value, (list, tuple)):
                        cleaned[key] = [
                            normalize_text(v) if isinstance(v, str) else v 
                            for v in value
                        ]
                    else:
                        cleaned[key] = value
                return cleaned
            
            # Clean all articles before export
            cleaned_articles = [clean_article(article) for article in articles]
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write to file with explicit UTF-8 BOM and proper encoding handling
            with open(filepath, 'a', newline='', encoding='utf-8-sig', errors='strict') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=fieldnames, 
                    delimiter='^',
                    quoting=csv.QUOTE_MINIMAL,
                    escapechar='\\',
                    doublequote=False,
                    strict=True
                )
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write articles
                for article in articles:
                    # Ensure all fields are present and properly formatted
                    row = {}
                    for field in fieldnames:
                        value = article.get(field, '')
                        # Convert to string and ensure proper encoding
                        if value is None:
                            value = ''
                        elif not isinstance(value, str):
                            value = str(value)
                        row[field] = value
                    
                    # Debug: Log the row being written
                    logger.debug(f"Writing row: {row}")
                    writer.writerow(row)
            
            logger.info(f"Exported {len(articles)} articles to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting articles: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def export_articles(cls, articles: List[Dict], config) -> str:
        """Class method to export articles using this exporter.
        
        Args:
            articles: List of article dictionaries to export
            config: Competitor configuration (dict) or competitor name (str)
            
        Returns:
            str: Path to the exported file
        """
        exporter = cls()
        competitor_name = config.get('name') if isinstance(config, dict) else config
        return exporter._export_articles_to_file(articles, competitor_name)
