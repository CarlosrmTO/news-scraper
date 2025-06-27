"""
Dedicated exporter for OKDiario articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class OKDiarioExporter(BaseExporter):
    """Dedicated exporter for OKDiario articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "okdiario"

def export_okdiario_articles(articles: List[Dict], config: Dict) -> str:
    """Export OKDiario articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return OKDiarioExporter.export_articles(articles, config)
