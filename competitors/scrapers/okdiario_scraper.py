"""
Dedicated scraper for OKDiario news articles.
"""
import gzip
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Configure requests session for better performance
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://okdiario.com'
})

class OKDiarioScraper(BaseScraper):
    """Dedicated scraper for OKDiario news articles."""
    
    def __init__(self, config: Dict):
        """Initialize the scraper with configuration."""
        self.config = config
        self.name = config.get('name', 'OKDiario')
        self.base_url = config.get('url', 'https://okdiario.com')
        self.sitemap_url = 'https://okdiario.com/sitemaps/okd-sitemap-index.xml'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': self.base_url
        }
        
    def get_article_urls(self, limit: int = 10, **kwargs) -> List[str]:
        """
        Get a list of recent article URLs from OKDiario.
        
        Args:
            limit: Maximum number of URLs to return
            **kwargs: Additional arguments
            
        Returns:
            List of article URLs
        """
        days_back = kwargs.get('days_back', 1)
        max_articles = kwargs.get('max_articles', limit)
        
        try:
            # First try to get URLs from the Google News sitemap
            sitemap_urls = self._get_sitemap_urls()
            article_urls = self._process_sitemap_urls(sitemap_urls, days_back, max_articles)
            
            # If not enough articles, try the RSS feed as fallback
            if len(article_urls) < max_articles:
                rss_urls = self._get_rss_entries(days_back)
                for url in rss_urls:
                    if url not in article_urls and len(article_urls) < max_articles:
                        article_urls.append(url)
            
            return article_urls[:max_articles]
            
        except Exception as e:
            logger.error(f"Error getting article URLs: {e}")
            return []
    
    def get_article_data(self, url: str) -> Dict[str, Any]:
        """
        Get article data from a URL with proper encoding handling.
        
        Args:
            url: URL of the article
            
        Returns:
            Dictionary containing article data with proper encoding
        """
        try:
            # Get the page content with explicit encoding and headers
            response = session.get(url, headers={
                'User-Agent': self.headers['User-Agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'TE': 'Trailers',
            }, timeout=30)
            
            # Force UTF-8 decoding and handle potential encoding issues
            response.encoding = 'utf-8'
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Get the raw content and normalize line endings
            content = response.text
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Parse with BeautifulSoup using the HTML5 parser for better HTML5 handling
            soup = BeautifulSoup(content, 'html5lib')
            
            # If parsing failed, try with lxml as fallback
            if not soup or not soup.find('body'):
                soup = BeautifulSoup(content, 'lxml')
            
            # Extraer título - múltiples posibles ubicaciones
            title = ''
            title_elem = (soup.find('h1', class_='title') or 
                         soup.find('h1', class_='entry-title') or
                         soup.find('h1', class_='article-title') or
                         soup.find('h1'))
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extraer autor(es) - múltiples posibles ubicaciones
            authors = []
            
            # 1. Buscar en meta tags
            author_meta = soup.find('meta', attrs={'name': 'author'}) or \
                         soup.find('meta', attrs={'property': 'article:author'}) or \
                         soup.find('meta', attrs={'name': 'twitter:creator'})
            
            if author_meta and author_meta.get('content'):
                author_name = author_meta['content'].strip()
                if author_name and not author_name.startswith('@'):
                    authors.append(author_name)
            
            # 2. Buscar en elementos de autor específicos de OKDiario
            author_selectors = [
                'a[rel="author"]',
                '.author-name',
                '.author',
                '.entry-author',
                '.article-author',
                '.byline',
                '.autor',
                '.firma',
                '.signature',
                'span[itemprop="author"]',
                'div[itemprop="author"]'
            ]
            
            for selector in author_selectors:
                for elem in soup.select(selector):
                    author_text = elem.get_text(strip=True)
                    # Filtrar texto que no parece ser un nombre de autor
                    if (author_text and 
                        len(author_text) > 3 and 
                        not any(word in author_text.lower() for word in ['por', 'publicado', 'actualizado', 'compartir', 'redacción', 'equipo', 'staff', 'redaccion'])):
                        # Limpiar el nombre del autor
                        author_text = re.sub(r'^[pP]or\s+', '', author_text)  # Eliminar 'Por ' al inicio
                        author_text = re.sub(r'\s*\|.*$', '', author_text)  # Eliminar todo después de |
                        author_text = re.sub(r'\s*@.*$', '', author_text)    # Eliminar menciones de Twitter
                        author_text = author_text.strip()
                        if author_text and len(author_text) > 3:
                            authors.append(author_text)
            
            # 3. Buscar en el texto de la firma o pie de autor
            signature_selectors = [
                '.entry-meta',
                '.article-meta',
                '.post-meta',
                '.firma-articulo',
                '.autor-noticia'
            ]
            
            for selector in signature_selectors:
                for elem in soup.select(selector):
                    text = elem.get_text(' ', strip=True)
                    # Buscar patrones como 'Por Nombre Apellido' o 'Por N. Apellido'
                    match = re.search(r'(?:^|\s)[Pp]or\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)', text)
                    if match:
                        author_name = match.group(1).strip()
                        if len(author_name) > 3:  # Filtrar textos muy cortos
                            authors.append(author_name)
            
            # 4. Si no se encontraron autores, buscar en el contenido
            if not authors:
                content_elem = soup.find('div', class_=lambda x: x and 'content' in (x or '').lower())
                if content_elem:
                    # Buscar párrafos al inicio del contenido que puedan contener el autor
                    first_paragraphs = content_elem.find_all(['p', 'div'], limit=3)
                    for p in first_paragraphs:
                        text = p.get_text(strip=True)
                        if text.startswith(('Por ', 'por ')) and len(text) < 100:  # Asumimos que es una firma
                            author_name = re.sub(r'^[Pp]or\s+', '', text).split('|')[0].strip()
                            if len(author_name) > 3:
                                authors.append(author_name)
                                break
            
            # Limpiar y filtrar autores
            cleaned_authors = []
            for author in authors:
                # Eliminar caracteres no deseados
                author = re.sub(r'[\n\t•·]', ' ', author).strip()
                # Eliminar fechas, horas, etc.
                author = re.sub(r'\d{1,2}[\/\.]\d{1,2}[\/\.]\d{2,4}', '', author)
                author = re.sub(r'\d{1,2}[h:]\d{2}', '', author)
                # Eliminar palabras comunes que no son nombres
                author = re.sub(r'\b(?:por|de|la|el|los|las|en|a|y|e|o|u|del|al|un|una|unos|unas|es|son|para|con|porque|según)\b', '', author, flags=re.IGNORECASE)
                author = re.sub(r'\s+', ' ', author).strip()
                
                # Validar que el autor tenga un formato razonable
                if (len(author) > 3 and 
                    not any(word in author.lower() for word in ['redacción', 'redaccion', 'equipo', 'staff', 'okdiario']) and
                    not re.search(r'^[\W\d_]+$', author)):  # No solo símbolos o números
                    cleaned_authors.append(author)
            
            # Eliminar duplicados manteniendo el orden
            seen = set()
            authors = [a for a in cleaned_authors if not (a.lower() in seen or seen.add(a.lower()))]
            
            # Extraer fecha de publicación
            publish_date = ''
            date_elem = (soup.find('time') or 
                        soup.find('meta', property='article:published_time') or
                        soup.find('meta', attrs={'name': 'pubdate'}) or
                        soup.find('meta', attrs={'name': 'publish_date'}))
            
            if date_elem:
                if hasattr(date_elem, 'get'):
                    date_str = date_elem.get('datetime') or date_elem.get('content') or ''
                else:
                    date_str = date_elem.get_text(strip=True)
                
                if date_str:
                    try:
                        publish_date = date_parser.parse(date_str).isoformat()
                    except Exception as e:
                        logger.warning(f'Error parsing date {date_str}: {e}')
            
            # Extraer contenido - múltiples posibles contenedores
            content = ''
            content_elems = soup.find_all(['div', 'article'], class_=lambda x: x and 
                                        any(cls in x.lower() for cls in ['entry-content', 'article-body', 'content', 'article-content']))
            
            if not content_elems:
                # Si no se encuentra por clase, buscar por estructura semántica
                content_elems = soup.find_all('article') or soup.find_all('div', role='article')
            
            for elem in content_elems:
                # Extraer párrafos, excluyendo elementos de navegación, publicidad, etc.
                paragraphs = []
                for p in elem.find_all('p'):
                    # Excluir párrafos que probablemente no son contenido
                    if (p.parent and p.parent.name in ['footer', 'nav', 'aside', 'header'] or
                        any(x in p.get('class', []) for x in ['ad', 'publicidad', 'related', 'comentarios'])):
                        continue
                    
                    text = p.get_text(strip=True)
                    # Filtrar párrafos muy cortos que probablemente no son contenido
                    if len(text) > 30:  # Ajustar según sea necesario
                        paragraphs.append(text)
                
                if paragraphs:
                    content = ' '.join(paragraphs)
                    break
            
            # Extraer sección de la URL
            parsed_url = urlparse(url)
            path_parts = [p for p in parsed_url.path.split('/') if p]
            section = path_parts[0] if path_parts else ''
            
            return {
                'title': title,
                'url': url,
                'authors': authors,
                'publish_date': publish_date,
                'content': content,
                'section': section,
                'source': self.name
            }
            
        except Exception as e:
            logger.error(f"Error getting article data from {url}: {e}")
            return {}
    
    def _get_sitemap_urls(self) -> List[str]:
        """Get list of sitemap URLs from the sitemap index."""
        try:
            response = session.get(self.sitemap_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'xml')
            sitemap_tags = soup.find_all('sitemap')
            
            # Filter for Google News sitemap first, then other sitemaps
            sitemap_urls = []
            for sitemap in sitemap_tags:
                loc = sitemap.find('loc')
                if loc and 'google-news' in loc.text:
                    sitemap_urls.insert(0, loc.text)  # Google News first
                elif loc:
                    sitemap_urls.append(loc.text)
            
            return sitemap_urls
            
        except Exception as e:
            logger.error(f"Error getting sitemap URLs: {e}")
            return []
    
    def _process_sitemap_urls(self, sitemap_urls: List[str], days_back: int, max_articles: int) -> List[str]:
        """Process sitemap URLs and return recent article URLs."""
        article_urls = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for sitemap_url in sitemap_urls:
            if len(article_urls) >= max_articles:
                break
                
            try:
                response = session.get(sitemap_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                # Handle gzipped sitemaps
                if sitemap_url.endswith('.gz'):
                    content = gzip.decompress(response.content).decode('utf-8')
                    soup = BeautifulSoup(content, 'xml')
                else:
                    soup = BeautifulSoup(response.text, 'xml')
                
                # Find all URL entries
                for url_tag in soup.find_all('url'):
                    if len(article_urls) >= max_articles:
                        break
                        
                    loc = url_tag.find('loc')
                    if not loc:
                        continue
                        
                    # Check lastmod date if available
                    lastmod = url_tag.find('lastmod')
                    if lastmod and lastmod.text:
                        try:
                            lastmod_date = date_parser.parse(lastmod.text)
                            if lastmod_date < cutoff_date:
                                continue
                        except Exception:
                            pass
                    
                    article_urls.append(loc.text)
                
            except Exception as e:
                logger.warning(f"Error processing sitemap {sitemap_url}: {e}")
                continue
                
        return article_urls
    
    def _get_rss_entries(self, days_back: int) -> List[str]:
        """Get recent article URLs from RSS feed with proper encoding handling."""
        rss_urls = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            # Get the RSS feed content with explicit encoding
            response = session.get('https://okdiario.com/feed', headers={
                'User-Agent': self.headers['User-Agent'],
                'Accept': 'application/rss+xml, application/xml',
                'Accept-Charset': 'utf-8',
                'Accept-Encoding': 'gzip, deflate',
            }, timeout=15)
            
            # Force UTF-8 decoding
            response.encoding = 'utf-8'
            
            # Parse the feed with explicit encoding
            feed = feedparser.parse(response.text)
            
            # If parsing failed, try with the raw content
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                logger.warning(f"Feed parsing error: {feed.bozo_exception}")
                # Try with BeautifulSoup to handle the encoding
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')
                
                for item in items:
                    try:
                        link = item.find('link')
                        if not link or not link.text:
                            continue
                            
                        # Get publication date
                        pub_date = item.find('pubDate')
                        if not pub_date or not pub_date.text:
                            continue
                            
                        try:
                            entry_datetime = date_parser.parse(pub_date.text)
                        except Exception:
                            continue
                            
                        if entry_datetime >= cutoff_date:
                            rss_urls.append(link.text.strip())
                            
                    except Exception as e:
                        logger.warning(f"Error processing RSS item: {e}")
                        continue
                        
                return rss_urls
            
            # Process feed entries normally if no parsing error
            for entry in feed.entries:
                try:
                    # Skip entries without a published date
                    if not hasattr(entry, 'published_parsed') and not hasattr(entry, 'updated_parsed'):
                        continue
                        
                    # Use updated_parsed if available, otherwise published_parsed
                    entry_date = entry.get('updated_parsed') or entry.published_parsed
                    entry_datetime = datetime(*entry_date[:6])
                    
                    if entry_datetime >= cutoff_date:
                        # Ensure the link is properly encoded
                        link = entry.get('link', '').strip()
                        if link:
                            rss_urls.append(link)
                            
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            
        return rss_urls


def create_okdiario_scraper(competitor: Dict, days_back: int = 1, **kwargs) -> OKDiarioScraper:
    """
    Create and return an instance of OKDiarioScraper.
    
    Args:
        competitor: Competitor configuration dictionary
        days_back: Number of days to look back for articles
        **kwargs: Additional arguments to pass to the scraper
        
    Returns:
        OKDiarioScraper instance
    """
    return OKDiarioScraper(competitor, **kwargs)


def get_okdiario_articles(config: Dict, days_back: int = 1, max_articles: int = 10) -> List[Dict]:
    """
    Get recent articles from OKDiario.
    
    Args:
        config: Configuration dictionary
        days_back: Number of days to look back for articles
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    scraper = OKDiarioScraper(config)
    article_urls = scraper.get_article_urls(limit=max_articles, days_back=days_back, max_articles=max_articles)
    
    articles = []
    for url in article_urls[:max_articles]:
        article_data = scraper.get_article_data(url)
        if article_data:
            articles.append(article_data)
    
    return articles
