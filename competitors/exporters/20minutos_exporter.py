"""
Dedicated exporter for 20minutos articles.
"""
import logging
import re
import csv
import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from newspaper import Article, Config
from bs4 import BeautifulSoup
from ..scrapers.base_scraper import BaseScraper
from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

class VeinteMinutosExporter(BaseExporter):
    """Dedicated exporter for 20minutos articles."""
    
    @classmethod
    def get_competitor_name(cls) -> str:
        """Return the name of the competitor in a filesystem-friendly format."""
        return "20minutos"
    
    @classmethod
    def clean_author_name(cls, author: Optional[str]) -> Optional[str]:
        """Limpia un nombre de autor individual"""
        if not author or not isinstance(author, str):
            return None
            
        # Eliminar espacios al inicio y final
        author = author.strip()
        
        # Patrones a eliminar
        patterns_to_remove = [
            r'(?i)redactor[\w\s]*',
            r'(?i)periodista[\w\s]*',
            r'(?i)en \w+',
            r'(?i)en linkedin',
            r'(?i)en x',
            r'(?i)en twitter',
            r'(?i)ver sus artículos',
            r'(?i)líder en los diarios más leídos',
            r'(?i)consulta las últimas noticias',
            r'(?i)diario gratuito',
            r'(?i)referencia en españa',
            r'\s+',  # Múltiples espacios
            r'[\.,;]$'  # Puntos o comas al final
        ]
        
        for pattern in patterns_to_remove:
            author = re.sub(pattern, ' ', author, flags=re.IGNORECASE)
            
        # Limpiar espacios adicionales
        author = ' '.join(author.split())
        
        # Si después de limpiar está vacío o es muy corto, descartar
        if len(author) < 3 or len(author) > 50:
            return None
            
        return author
    
    @classmethod
    def extract_authors(cls, article: Dict[str, Any]) -> List[str]:
        """Extrae los autores del artículo de manera efectiva"""
        authors = set()
        
        # 1. Intentar extraer autores de los metadatos del artículo
        if article.get('authors') and isinstance(article['authors'], list):
            for author in article['authors']:
                cleaned = cls.clean_author_name(author)
                if cleaned:
                    authors.add(cleaned)
        
        # 2. Si no hay autores, intentar extraer del HTML
        if not authors and 'html' in article:
            soup = BeautifulSoup(article['html'], 'html.parser')
            
            # Buscar en meta tags
            for meta in soup.find_all('meta', {'name': ['author', 'Author', 'byl']}):
                if meta.get('content'):
                    cleaned = cls.clean_author_name(meta['content'])
                    if cleaned:
                        authors.add(cleaned)
            
            # Buscar en elementos con clase de autor
            for elem in soup.select('.author-name, .author, .autor, .byline, .byline__author'):
                if elem.text.strip():
                    cleaned = cls.clean_author_name(elem.text)
                    if cleaned:
                        authors.add(cleaned)
        
        # 3. Si aún no hay autores, intentar con newspaper3k
        if not authors and 'url' in article:
            try:
                config = Config()
                config.browser_user_agent = random.choice(article.get('user_agents', []))
                config.request_timeout = 10
                
                art = Article(article['url'], language='es', config=config)
                art.download()
                art.parse()
                
                if art.authors:
                    for author in art.authors:
                        cleaned = cls.clean_author_name(author)
                        if cleaned:
                            authors.add(cleaned)
            except Exception as e:
                logger.warning(f"Error al extraer autores con newspaper3k: {e}")
        
        return list(authors)
    
    @classmethod
    def get_article_data(cls, url: str, config: Dict) -> Dict[str, Any]:
        """Obtiene el contenido de un artículo"""
        try:
            # Configuración para newspaper3k
            newspaper_config = Config()
            newspaper_config.browser_user_agent = random.choice(config.get('user_agents', []))
            newspaper_config.request_timeout = 10
            
            # Descargar y parsear el artículo
            article = Article(url, language='es', config=newspaper_config)
            article.download()
            article.parse()
            
            # Extraer metadatos
            publish_date = article.publish_date.strftime('%Y-%m-%d %H:%M:%S') if article.publish_date else ''
            
            return {
                'url': url,
                'title': article.title,
                'text': article.text,
                'publish_date': publish_date,
                'authors': article.authors,
                'html': article.html,
                'user_agents': config.get('user_agents', [])
            }
            
        except Exception as e:
            logger.error(f"Error al obtener datos del artículo {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """Limpia el texto para ser guardado en CSV"""
        if not text:
            return ''
            
        # Eliminar caracteres problemáticos
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text = re.sub(r'\s+', ' ', text)  # Múltiples espacios a uno solo
        text = text.strip()
        
        return text
    
    @classmethod
    def is_today(cls, date_str: str, date_format: str = '%Y-%m-%d %H:%M:%S%z') -> bool:
        """Verifica si una fecha es de hoy"""
        try:
            # Intentar con el formato con timezone
            try:
                article_date = datetime.strptime(date_str, date_format)
            except ValueError:
                # Si falla, intentar sin timezone
                date_format = '%Y-%m-%d %H:%M:%S'
                article_date = datetime.strptime(date_str, date_format)
            
            # Obtener fechas de hoy
            today = datetime.now()
            today_start = datetime(today.year, today.month, today.day)
            today_end = today_start + timedelta(days=1)
            
            # Verificar si la fecha del artículo está dentro de hoy
            return today_start <= article_date < today_end
            
        except Exception as e:
            logger.warning(f"Error al verificar fecha {date_str}: {e}")
            return False
    
    @classmethod
    def export_articles(cls, articles: List[Dict], config: Dict) -> str:
        """
        Exporta los artículos a un archivo CSV con codificación UTF-8, usando ^ como delimitador
        
        Args:
            articles: Lista de artículos a exportar
            config: Configuración del competidor
            
        Returns:
            str: Ruta al archivo exportado
        """
        if not articles:
            logger.warning("No hay artículos para exportar")
            return ""
        
        # Crear directorio de salida si no existe
        output_dir = os.path.join('output', 'competitors', cls.get_competitor_name())
        os.makedirs(output_dir, exist_ok=True)
        
        # Generar nombre de archivo con fecha
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{cls.get_competitor_name()}_{date_str}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # Preparar los datos para exportar
        rows = []
        fields = [
            'title', 'url', 'publish_date', 'authors', 
            'section', 'subsection', 'text'
        ]
        
        for article in articles:
            # Extraer autores si no están ya en el artículo
            if 'authors' not in article or not article['authors']:
                article['authors'] = cls.extract_authors(article)
            
            # Limpiar los campos de texto
            row = {}
            for field in fields:
                if field == 'authors':
                    # Unir múltiples autores con '; '
                    authors = article.get(field, [])
                    if isinstance(authors, list):
                        row[field] = '; '.join(authors)
                    else:
                        row[field] = str(authors) if authors else ''
                else:
                    value = article.get(field, '')
                    row[field] = cls.clean_text(str(value)) if value else ''
            
            rows.append(row)
        
        # Escribir el archivo CSV con codificación UTF-8 y delimitador ^
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=fields,
                    delimiter='^',
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL
                )
                writer.writeheader()
                writer.writerows(rows)
                
            logger.info(f"Exportados {len(rows)} artículos a {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error al exportar a CSV: {e}")
            return ""


def export_20minutos_articles(articles: List[Dict], config: Dict) -> str:
    """
    Función de conveniencia para exportar artículos de 20minutos.
    
    Args:
        articles: Lista de artículos a exportar
        config: Configuración del competidor
        
    Returns:
        str: Ruta al archivo exportado
    """
    return VeinteMinutosExporter.export_articles(articles, config)
