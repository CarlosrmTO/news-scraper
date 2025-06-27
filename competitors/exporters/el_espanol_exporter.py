"""
Dedicated exporter for El Español articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class ElEspanolExporter(BaseExporter):
    """Dedicated exporter for El Español articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "el_espanol"

def export_el_espanol_articles(articles: List[Dict], config: Dict) -> str:
    """Export El Español articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ElEspanolExporter.export_articles(articles, config)
