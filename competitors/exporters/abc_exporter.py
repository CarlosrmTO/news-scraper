"""
Dedicated exporter for ABC articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class ABCExporter(BaseExporter):
    """Dedicated exporter for ABC articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "abc"

def export_abc_articles(articles: List[Dict], config: Dict) -> str:
    """Export ABC articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ABCExporter.export_articles(articles, config)
