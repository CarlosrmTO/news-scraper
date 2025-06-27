"""
Scraper for El Mundo articles using sitemaps.
"""
import os
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import requests
import re

def setup_logging():
    """
    Configura el sistema de logging de manera robusta.
    
    Returns:
        logging.Logger: Logger configurado con manejadores de consola.
    """
    # Configurar el logger básico
    logger = logging.getLogger('el_mundo_scraper')
    
    # Eliminar manejadores existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Configurar el nivel de log
    logger.setLevel(logging.INFO)
    
    # Formato para los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Manejador para consola (siempre disponible)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Configurar logging
logger = setup_logging()

def clean_text(text):
    """Limpia el texto de caracteres no deseados."""
    if not text:
        return ""
    # Eliminar espacios múltiples y saltos de línea
    text = ' '.join(str(text).split())
    # Eliminar caracteres especiales
    text = re.sub(r'[\r\n\t]+', ' ', text)
    return text.strip()

def parse_date(date_str):
    """Intenta parsear una fecha desde un string."""
    try:
        # Formato de fecha en el sitemap: '2025-06-26T16:31:36Z'
        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        return dt.isoformat()
    except (ValueError, TypeError) as e:
        logger.warning(f"Error al parsear fecha {date_str}: {e}")
        return datetime.now().isoformat()

def extract_section(url):
    """Extrae la sección de la URL."""
    try:
        parsed = urlparse(url)
        # La sección suele ser el primer segmento de la ruta
        path_parts = [p for p in parsed.path.split('/') if p]
        return path_parts[0] if path_parts else ""
    except Exception as e:
        logger.warning(f"Error extrayendo sección de {url}: {e}")
        return ""

def fetch_sitemap(url):
    """Descarga y parsea un sitemap XML."""
    try:
        logger.info(f"Fetching sitemap: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response content (first 500 chars): {response.text[:500]}...")
        
        # Parsear el XML
        root = ET.fromstring(response.content)
        
        # Definir namespaces - usando el namespace por defecto (sin prefijo) para el sitemap
        ns = {
            '': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9',
            'image': 'http://www.google.com/schemas/sitemap-image/1.1'
        }
        
        logger.info(f"Successfully parsed sitemap: {url}")
        return root, ns
    except Exception as e:
        logger.error(f"Error fetching sitemap {url}: {e}", exc_info=True)
        return None, None

def process_sitemap(url, min_date, max_articles):
    """Procesa un sitemap y devuelve los artículos encontrados."""
    articles = []
    logger.info(f"Processing sitemap: {url}")
    logger.info(f"Looking for articles newer than: {min_date}")
    
    root, ns = fetch_sitemap(url)
    
    if not root or not ns:
        logger.warning(f"No se pudo obtener el sitemap o no se definieron namespaces para: {url}")
        return articles
    
    logger.info(f"Namespaces definidos: {ns}")
    logger.info(f"Buscando elementos URL en el sitemap...")
    
    try:
        # Buscar todas las URLs en el sitemap
        url_elements = root.findall('.//url', ns)
        logger.info(f"Se encontraron {len(url_elements)} elementos URL en el sitemap")
        
        for idx, url_elem in enumerate(url_elements, 1):
            if len(articles) >= max_articles:
                logger.info(f"Se alcanzó el límite máximo de artículos ({max_articles})")
                break
                
            logger.debug(f"Procesando URL {idx}/{len(url_elements)}")
                
            try:
                # Extraer URL
                loc_elem = url_elem.find('loc', ns)
                if loc_elem is None:
                    continue
                    
                url = loc_elem.text.strip()
                
                # Extraer fecha de última modificación
                lastmod_elem = url_elem.find('lastmod', ns)
                pub_date = parse_date(lastmod_elem.text) if lastmod_elem is not None else datetime.now().isoformat()
                pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                
                # Filtrar por fecha
                logger.debug(f"Artículo con fecha: {pub_dt} (mínima requerida: {min_date})")
                if pub_dt < min_date:
                    logger.debug(f"Artículo demasiado antiguo, saltando...")
                    continue
                    
                logger.debug(f"Artículo dentro del rango de fechas, procesando...")
                
                # Extraer información de noticias (si está disponible)
                logger.debug("Buscando información de noticias en el elemento...")
                news_elem = url_elem.find('news:news', ns)
                if news_elem is not None:
                    logger.debug("Se encontró información de noticias")
                else:
                    logger.debug("No se encontró información de noticias en este elemento")
                if news_elem is not None:
                    title_elem = news_elem.find('news:title', ns)
                    title = clean_text(title_elem.text) if title_elem is not None else ""
                    
                    pub_elem = news_elem.find('news:publication_date', ns)
                    if pub_elem is not None and pub_elem.text:
                        pub_date = parse_date(pub_elem.text)
                        pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                else:
                    # Si no hay información de noticias, extraer el título de la URL
                    title = clean_text(url.split('/')[-1].replace('-', ' ').title())
                
                # Extraer sección
                section = extract_section(url)
                
                # Crear diccionario con la información del artículo
                article = {
                    'title': title,
                    'url': url,
                    'publish_date': pub_date,
                    'authors': '',  # No disponible directamente en el sitemap
                    'source': 'El Mundo',
                    'domain': 'elmundo.es',
                    'summary': '',  # No disponible en el sitemap
                    'section': section,
                    'subsection': ''  # No disponible en el sitemap
                }
                
                articles.append(article)
                logger.debug(f"Added article: {title}")
                
            except Exception as e:
                logger.error(f"Error procesando artículo: {e}", exc_info=True)
                continue
                
    except Exception as e:
        logger.error(f"Error procesando sitemap {url}: {e}", exc_info=True)
    
    return articles

def scrape_el_mundo_articles(config, max_articles=10, days_back=1):
    """
    Extrae artículos de los sitemaps de El Mundo.
    
    Args:
        config (dict): Configuración del competidor
        max_articles (int): Número máximo de artículos a extraer
        days_back (int): Número de días hacia atrás para filtrar artículos
        
    Returns:
        list: Lista de diccionarios con la información de los artículos
    """
    articles = []
    try:
        # Obtener la lista de sitemaps desde la configuración
        sitemaps = config.get('sitemaps', [])
        if not sitemaps:
            logger.error("No se encontraron sitemaps en la configuración")
            return articles
        
        # Calcular la fecha mínima para los artículos
        min_date = datetime.now() - timedelta(days=days_back)
        
        # Procesar cada sitemap hasta alcanzar el número máximo de artículos
        for sitemap_url in sitemaps:
            if len(articles) >= max_articles:
                break
                
            # Procesar el sitemap
            sitemap_articles = process_sitemap(
                sitemap_url, 
                min_date, 
                max_articles - len(articles)
            )
            articles.extend(sitemap_articles)
        
        logger.info(f"Total articles fetched from sitemaps: {len(articles)}")
        
    except Exception as e:
        logger.error(f"Error en scrape_el_mundo_articles: {e}", exc_info=True)
    
    return articles
