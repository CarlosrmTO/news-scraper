"""
Dedicated scraper for Vozpópuli articles.
"""
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

from newspaper import Article
import requests
from bs4 import BeautifulSoup
import json

class VozPopuliScraper:
    """Dedicated scraper for Vozpópuli articles."""
    
    def __init__(self, config: Dict):
        """Initialize with a competitor config."""
        self.config = config
        self.name = config['name']
        self.base_url = config['url']
        self.domain = urlparse(self.base_url).netloc
        self.output_dir = os.path.join('output', 'competitors', 'voz_populi')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Headers para simular navegador
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://www.vozpopuli.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def get_article_data(self, url: str) -> Optional[Dict]:
        """Extract article data from a single URL."""
        try:
            # Obtener la página del artículo
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Usar BeautifulSoup para extraer metadatos de forma más precisa
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer metadatos de schema.org (si están disponibles)
            metadata = self._extract_metadata(soup)
            
            # Usar newspaper3k para extraer el contenido principal
            article = Article(url, language='es')
            article.download(input_html=response.text)
            article.parse()
            
            # Extraer autores del HTML (Vozpópuli los tiene en un formato específico)
            authors = self._extract_authors(soup)
            
            # Combinar metadatos con el contenido extraído
            article_data = {
                'title': article.title or metadata.get('headline', ''),
                'url': url,
                'publish_date': self._parse_date(metadata.get('datePublished', '')),
                'authors': authors if authors else ['Redacción Vozpópuli'],
                'content': article.text,
                'section': self._extract_section(url, soup),
                'domain': self.domain,
                'source': 'Vozpópuli',
                'summary': metadata.get('description', '')
            }
            
            return article_data
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None
    
    def _extract_metadata(self, soup):
        """Extraer metadatos de schema.org."""
        metadata = {
            'author': [],
            'datePublished': '',
            'headline': '',
            'description': ''
        }
        
        # Buscar script de tipo application/ld+json
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0] if data else {}
                
                if 'author' in data:
                    if isinstance(data['author'], list):
                        for author in data['author']:
                            if isinstance(author, dict):
                                metadata['author'].append(author.get('name', ''))
                            else:
                                metadata['author'].append(str(author))
                    elif isinstance(data['author'], dict):
                        metadata['author'].append(data['author'].get('name', ''))
                    else:
                        metadata['author'].append(str(data['author']))
                
                if 'datePublished' in data:
                    metadata['datePublished'] = data['datePublished']
                
                if 'headline' in data:
                    metadata['headline'] = data['headline']
                
                if 'description' in data:
                    metadata['description'] = data['description']
                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return metadata
    
    def _extract_authors(self, soup):
        """Extraer autores del HTML de Vozpópuli."""
        authors = []
        
        # Buscar en el div de autores
        author_div = soup.find('div', class_='author')
        if author_div:
            author_links = author_div.find_all('a', rel='author')
            for link in author_links:
                author_name = link.get_text(strip=True)
                if author_name and author_name.lower() not in ['redacción', 'redaccion']:
                    authors.append(author_name)
        
        # Si no encontramos autores, intentar extraer del schema
        if not authors:
            script_data = soup.find('script', type='application/ld+json')
            if script_data:
                try:
                    data = json.loads(script_data.string)
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    if 'author' in data:
                        if isinstance(data['author'], list):
                            for author in data['author']:
                                if isinstance(author, dict):
                                    authors.append(author.get('name', ''))
                                else:
                                    authors.append(str(author))
                        elif isinstance(data['author'], dict):
                            authors.append(data['author'].get('name', ''))
                        else:
                            authors.append(str(data['author']))
                except (json.JSONDecodeError, AttributeError):
                    pass
        
        # Limpiar nombres de autores
        cleaned_authors = []
        for author in authors:
            if author and isinstance(author, str):
                # Eliminar espacios en blanco y caracteres no deseados
                author = ' '.join(author.split())
                author = re.sub(r'^por\s+', '', author, flags=re.IGNORECASE)
                if author and author.lower() not in ['redacción', 'redaccion', 'vozpópuli', 'vozpopuli']:
                    cleaned_authors.append(author)
        
        return cleaned_authors if cleaned_authors else ['Redacción Vozpópuli']
    
    def _parse_date(self, date_str):
        """Parsear fecha de diferentes formatos."""
        if not date_str:
            return None
            
        try:
            # Formato ISO 8601: 2023-06-27T12:34:56Z o 2023-06-27T12:34:56+02:00
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).isoformat()
        except (ValueError, AttributeError):
            return None
    
    def _extract_section(self, url, soup):
        """Extraer la sección de la URL o del HTML."""
        # Intentar extraer del breadcrumb
        breadcrumb = soup.find('ol', class_='breadcrumb')
        if breadcrumb:
            items = breadcrumb.find_all('li', itemprop='itemListElement')
            if len(items) > 1:  # El primer ítem suele ser 'Inicio' o similar
                section = items[1].get_text(strip=True)
                if section and section.lower() not in ['inicio', 'portada']:
                    return section
        
        # Intentar extraer de la URL
        path_parts = urlparse(url).path.strip('/').split('/')
        if path_parts:
            section = path_parts[0]
            if section and section.lower() not in ['noticias', 'actualidad', 'ultima-hora']:
                return section.capitalize()
        
        return 'General'
    
    def get_recent_articles(self, days_back: int = 1, max_articles: int = 10) -> List[Dict]:
        """Get recent articles from Vozpópuli.
        
        Args:
            days_back: Number of days to look back for articles
            max_articles: Maximum number of articles to return
            
        Returns:
            List of article dictionaries
        """
        # Obtener las URLs de los artículos recientes
        urls = self._get_recent_article_urls(days_back, max_articles)
        
        # Procesar cada artículo
        articles = []
        for url in urls[:max_articles]:
            article_data = self.get_article_data(url)
            if article_data:
                articles.append(article_data)
        
        return articles
    
    def _get_recent_article_urls(self, days_back: int, max_urls: int) -> List[str]:
        """Obtener URLs de artículos recientes de Vozpópuli."""
        urls = set()
        
        # Obtener el sitemap principal
        sitemap_urls = []
        if 'sitemap' in self.config:
            if isinstance(self.config['sitemap'], list):
                sitemap_urls.extend(self.config['sitemap'])
            else:
                sitemap_urls.append(self.config['sitemap'])
        
        # Procesar cada sitemap
        for sitemap_url in sitemap_urls:
            try:
                response = requests.get(sitemap_url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                # Parsear el sitemap
                soup = BeautifulSoup(response.content, 'xml')
                
                # Extraer URLs de artículos
                for url_tag in soup.find_all('url'):
                    loc = url_tag.find('loc')
                    if loc and loc.text:
                        urls.add(loc.text.strip())
                    
                    if len(urls) >= max_urls * 2:  # Recolectar más URLs de las necesarias para filtrar después
                        break
                        
            except Exception as e:
                print(f"Error procesando sitemap {sitemap_url}: {str(e)}")
            
            if len(urls) >= max_urls * 2:
                break
        
        # Si no encontramos suficientes URLs en el sitemap, intentar con la portada
        if len(urls) < max_urls:
            try:
                response = requests.get(self.base_url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar enlaces a artículos
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href and '/noticias/' in href and href.endswith('.html'):
                        full_url = urljoin(self.base_url, href)
                        urls.add(full_url)
                    
                    if len(urls) >= max_urls * 2:
                        break
                        
            except Exception as e:
                print(f"Error obteniendo artículos de la portada: {str(e)}")
        
        # Filtrar URLs duplicadas y limitar el número de resultados
        return list(urls)[:max_urls]

def get_articles(config: Dict, days_back: int = 1, max_articles: int = 10) -> List[Dict]:
    """Get recent articles from Vozpópuli.
    
    Args:
        config: Competitor configuration
        days_back: Number of days to look back for articles
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    scraper = VozPopuliScraper(config)
    return scraper.get_recent_articles(days_back, max_articles)
