"""
Dedicated exporter for Libertad Digital articles.
"""
from typing import List, Dict
from .base_exporter import BaseExporter

class LibertadDigitalExporter(BaseExporter):
    """Dedicated exporter for Libertad Digital articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "libertad_digital"

def export_libertad_digital_articles(articles: List[Dict], config: Dict) -> str:
    """Export Libertad Digital articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return LibertadDigitalExporter.export_articles(articles, config)
