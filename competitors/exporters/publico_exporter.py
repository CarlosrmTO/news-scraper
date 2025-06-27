"""
Dedicated exporter for Público articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class PublicoExporter(BaseExporter):
    """Dedicated exporter for Público articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "publico"

def export_publico_articles(articles: List[Dict], config: Dict) -> str:
    """Export Público articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return PublicoExporter.export_articles(articles, config)
