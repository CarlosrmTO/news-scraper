"""
Dedicated exporter for El País articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class ElPaisExporter(BaseExporter):
    """Dedicated exporter for El País articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "el_pais"

def export_el_pais_articles(articles: List[Dict], config: Dict) -> str:
    """Export El País articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ElPaisExporter.export_articles(articles, config)
