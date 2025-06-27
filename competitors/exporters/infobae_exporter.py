"""
Dedicated exporter for Infobae articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class InfobaeExporter(BaseExporter):
    """Dedicated exporter for Infobae articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "infobae"

def export_infobae_articles(articles: List[Dict], config: Dict) -> str:
    """Export Infobae articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return InfobaeExporter.export_articles(articles, config)
