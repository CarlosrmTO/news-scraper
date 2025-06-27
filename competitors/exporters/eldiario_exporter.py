"""
Dedicated exporter for ElDiario.es articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class ElDiarioExporter(BaseExporter):
    """Dedicated exporter for ElDiario.es articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "eldiario"

def export_eldiario_articles(articles: List[Dict], config: Dict) -> str:
    """Export ElDiario.es articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ElDiarioExporter.export_articles(articles, config)
