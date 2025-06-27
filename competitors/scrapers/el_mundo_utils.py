"""
Utilidades para el scraping de El Mundo.
"""
import logging
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def clean_title(title):
    """Limpia el título de caracteres no deseados."""
    if not title:
        return ""
    # Eliminar espacios en blanco al principio y final
    title = title.strip()
    # Reemplazar múltiples espacios por uno solo
    title = re.sub(r'\s+', ' ', title)
    return title


def extract_article_metadata(url, timeout=10):
    """
    Extrae metadatos de un artículo de El Mundo.
    
    Args:
        url (str): URL del artículo
        timeout (int): Tiempo máximo de espera para la solicitud
        
    Returns:
        dict: Diccionario con los metadatos extraídos
    """
    metadata = {
        'title': '',
        'authors': [],
        'publish_date': '',
        'section': '',
        'subsection': ''
    }
    
    try:
        # Hacer la solicitud HTTP
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parsear el HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer el título
        # Intenta encontrar el título en varios selectores comunes
        title_selectors = [
            'h1.ue-c-article__headline',  # Selector común en El Mundo
            'h1.ue-c-article__title',     # Alternativa común
            'h1.article-header-title',    # Otra alternativa
            'h1[itemprop="headline"]',   # Usando atributo itemprop
            'h1'                          # Último recurso: cualquier h1
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                metadata['title'] = clean_title(title_elem.get_text())
                if metadata['title']:
                    break
        
        # Extraer autores
        author_selectors = [
            'a.ue-c-article__byline-name',  # Selector común para autores
            '.ue-c-article__byline-name',   # Alternativa sin el enlace
            'a[rel="author"]',             # Usando atributo rel
            '.author-name',                 # Otra alternativa común
            '[itemprop="author"]'          # Usando atributo itemprop
        ]
        
        authors = set()  # Usamos un conjunto para evitar duplicados
        for selector in author_selectors:
            author_elems = soup.select(selector)
            for elem in author_elems:
                author = clean_title(elem.get_text())
                # Filtro para evitar textos largos
                if author and len(author) < 100:
                    authors.add(author)
        
        metadata['authors'] = list(authors)
        
        # Extraer sección y subsección de la URL
        parsed_url = urlparse(url)
        path_parts = [p for p in parsed_url.path.split('/') if p]
        
        # Mapeo de secciones comunes
        section_mapping = {
            'espana': 'España',
            'internacional': 'Internacional',
            'economia': 'Economía',
            'tecnologia': 'Tecnología',
            'ciencia': 'Ciencia',
            'cultura': 'Cultura',
            'deportes': 'Deportes',
            'television': 'Televisión',
            'gente': 'Gente',
            'salud': 'Salud',
            'viajes': 'Viajes',
            'motor': 'Motor',
            'moda': 'Moda',
            'gastro': 'Gastronomía'
        }
        
        if len(path_parts) > 1:
            section = path_parts[0]
            metadata['section'] = section_mapping.get(section, section.capitalize())
            
            if len(path_parts) > 2 and path_parts[1].isdigit() and len(path_parts[1]) == 4:
                # Si el segundo segmento es un año, el tercero podría ser la subsección
                if len(path_parts) > 3:
                    subsection = path_parts[2]
                    metadata['subsection'] = section_mapping.get(
                        subsection, 
                        subsection.capitalize()
                    )
            else:
                # Si no, el segundo segmento es probablemente la subsección
                subsection = path_parts[1]
                metadata['subsection'] = section_mapping.get(
                    subsection, 
                    subsection.capitalize()
                )
        
        # Extraer fecha de publicación
        date_selectors = [
            'time[itemprop="datePublished"]',
            'time[datetime]',
            '.ue-c-article__publishdate',
            '.article-header-date',
            'time'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem and date_elem.get('datetime'):
                metadata['publish_date'] = date_elem['datetime']
                break
            if date_elem and date_elem.get_text():
                metadata['publish_date'] = date_elem.get_text().strip()
                break
        
        return metadata
        
    except Exception as e:
        logger.error("Error al extraer metadatos de %s: %s", url, str(e), exc_info=True)
        return metadata
