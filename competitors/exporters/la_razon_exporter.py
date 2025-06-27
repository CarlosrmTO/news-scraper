"""
Dedicated exporter for La Razón articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class LaRazonExporter(BaseExporter):
    """Dedicated exporter for La Razón articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "la_razon"

def export_la_razon_articles(articles: List[Dict], config: Dict) -> str:
    """Export La Razón articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return LaRazonExporter.export_articles(articles, config)
