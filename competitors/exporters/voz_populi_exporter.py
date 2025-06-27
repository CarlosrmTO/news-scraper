"""
Dedicated exporter for Vozpópuli articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class VozPopuliExporter(BaseExporter):
    """Dedicated exporter for Vozpópuli articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "voz_populi"

def export_voz_populi_articles(articles: List[Dict], config: Dict) -> str:
    """Export Vozpópuli articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return VozPopuliExporter.export_articles(articles, config)
