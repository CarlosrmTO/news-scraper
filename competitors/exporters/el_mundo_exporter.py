"""
Dedicated exporter for El Mundo articles.
"""
import logging
from typing import List, Dict, Any, Optional
from ..scrapers.el_mundo_utils import extract_article_metadata
from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

class ElMundoExporter(BaseExporter):
    """Dedicated exporter for El Mundo articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "el_mundo"
    
    @classmethod
    def enrich_article_data(cls, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich article data with metadata extracted from the article page.
        
        Args:
            article: Article data to enrich
            
        Returns:
            Enriched article data
        """
        try:
            url = article.get('url', '')
            if not url:
                logger.warning("No URL provided for article enrichment")
                return article
                
            logger.debug(f"Enriching article data for: {url}")
            
            # Extraer metadatos de la página del artículo
            metadata = extract_article_metadata(url)
            
            # Actualizar el artículo con los metadatos extraídos
            if metadata:
                # Solo actualizar campos que no estén ya definidos o estén vacíos
                if not article.get('title') and metadata.get('title'):
                    article['title'] = metadata['title']
                
                if not article.get('authors') and metadata.get('authors'):
                    article['authors'] = ', '.join(metadata['authors']) if isinstance(metadata['authors'], list) else metadata['authors']
                
                if not article.get('publish_date') and metadata.get('publish_date'):
                    article['publish_date'] = metadata['publish_date']
                
                if not article.get('section') and metadata.get('section'):
                    article['section'] = metadata['section']
                
                if not article.get('subsection') and metadata.get('subsection'):
                    article['subsection'] = metadata['subsection']
                
                logger.debug(f"Enriched article data: {article}")
            else:
                logger.warning(f"No metadata extracted for article: {url}")
            
            return article
            
        except Exception as e:
            logger.error(f"Error enriching article data: {str(e)}", exc_info=True)
            return article
    
    @classmethod
    def export_articles(cls, articles: List[Dict], config: Dict) -> str:
        """
        Export articles with enriched metadata.
        
        Args:
            articles: List of article dictionaries to export
            config: Competitor configuration
            
        Returns:
            str: Path to the exported file
        """
        # Enriquecer los artículos con metadatos adicionales
        enriched_articles = []
        for i, article in enumerate(articles, 1):
            logger.debug(f"Processing article {i}/{len(articles)}")
            enriched_article = cls.enrich_article_data(article)
            enriched_articles.append(enriched_article)
        
        # Llamar al método de la clase base para realizar la exportación
        return super().export_articles(enriched_articles, config)

def export_el_mundo_articles(articles: List[Dict], config: Dict) -> str:
    """Export El Mundo articles using the dedicated exporter.
    
    Args:
        articles: List of article dictionaries to export
        config: Competitor configuration
        
    Returns:
        str: Path to the exported file
    """
    return ElMundoExporter.export_articles(articles, config)
