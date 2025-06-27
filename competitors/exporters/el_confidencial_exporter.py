"""
Dedicated exporter for El Confidencial articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class ElConfidencialExporter(BaseExporter):
    """Dedicated exporter for El Confidencial articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "el_confidencial"

def export_el_confidencial_articles(articles: List[Dict], config: Dict) -> str:
    """Export El Confidencial articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ElConfidencialExporter.export_articles(articles, config)
