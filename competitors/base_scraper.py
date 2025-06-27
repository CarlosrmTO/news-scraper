"""
Base module for competitor scrapers.
"""
import os
import re
import random
import logging
import csv
from datetime import datetime, timezone
from newspaper import Article, Config
from urllib.parse import urlparse

def setup_logging():
    """Configura el sistema de logging de manera simple y robusta."""
    try:
        # Configurar el logger básico
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Eliminar manejadores existentes para evitar duplicados
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Formato para los logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Manejador para consola (siempre disponible)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # No configuramos archivo de log aquí, dejamos que los scripts principales lo hagan
        
        return logger
    except Exception as e:
        # Si hay algún error en la configuración del logging, devolvemos un logger básico
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        return logging.getLogger('base_scraper_fallback')

# Configurar logging
logger = setup_logging()

# Common user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
]

class BaseScraper:
    """Base class for all competitor scrapers."""
    
    def __init__(self, config):
        """Initialize with a competitor config."""
        self.config = config
        self.name = config['name']
        self.domain = urlparse(config['url']).netloc
        self.output_dir = os.path.join('output', 'competitors', self.name.lower().replace(' ', '_'))
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_random_user_agent(self):
        """Return a random user agent."""
        return random.choice(USER_AGENTS)
    
    def get_article_data(self, url):
        """Extract article data using newspaper3k."""
        try:
            user_agent = self.get_random_user_agent()
            config = Config()
            config.browser_user_agent = user_agent
            config.request_timeout = 30
            
            article = Article(url, config=config, headers={'User-Agent': user_agent})
            article.download()
            article.parse()
            
            # Extract and clean authors
            raw_authors = article.authors or []
            
            # Try to extract authors from meta tags if none found
            if not raw_authors and hasattr(article, 'meta_data') and article.meta_data:
                meta = article.meta_data
                # Common meta tags for authors
                author_tags = [
                    meta.get('author'),
                    meta.get('article:author'),
                    meta.get('sailthru.author'),
                    meta.get('dc.creator'),
                    meta.get('dcterms.creator'),
                    meta.get('parsely-author'),
                    meta.get('twitter:creator'),
                ]
                # Filter out None and empty strings
                raw_authors = [a for a in author_tags if a and str(a).strip()]
            
            # Clean and filter authors
            cleaned_authors = self.clean_authors(raw_authors)
            
            # If no authors found after cleaning, try to extract from byline or other elements
            if not cleaned_authors and hasattr(article, 'meta_data') and article.meta_data:
                meta = article.meta_data
                # Try to find byline or similar
                byline = meta.get('og:byline') or meta.get('byline') or meta.get('article:byline')
                if byline:
                    cleaned_authors = self.clean_authors([byline])
            
            # Log if we had to clean up authors
            if raw_authors and not cleaned_authors:
                logger.debug(f"No valid authors found after cleaning from: {raw_authors}")
            elif raw_authors and set(a.lower() for a in raw_authors) != set(a.lower() for a in cleaned_authors):
                logger.debug(f"Cleaned authors from {raw_authors} to {cleaned_authors}")
            
            # Extract section and subsection from URL
            section, subsection = self.extract_section_from_url(url)
            
            # Get current date if publish_date is not available
            current_date = datetime.now(timezone.utc).isoformat()
            
            # Handle publish_date safely
            publish_date = current_date  # Default to current date
            if article.publish_date:
                try:
                    if hasattr(article.publish_date, 'isoformat'):
                        publish_date = article.publish_date.isoformat()
                    else:
                        publish_date = str(article.publish_date)
                except Exception as e:
                    logger.warning(f"Error formatting date for {url}: {str(e)}")
                    publish_date = current_date
            
            # Ensure all fields have values
            return {
                'title': self.clean_text(article.title) or 'Sin título',
                'text': article.text,
                'publish_date': publish_date,
                'authors': cleaned_authors if cleaned_authors else ['Redacción'],
                'url': url,
                'source': self.name,
                'domain': self.domain,
                'html': article.html[:500] + '...' if article.html else '',
                'images': list(article.images)[:5],
                'keywords': article.keywords[:10],
                'summary': self.clean_text(article.meta_description or article.text[:200] + '...') or 'Sin resumen disponible',
                'section': section,
                'subsection': subsection
            }
        except Exception as e:
            logger.error(f"Error extracting article data from {url}: {str(e)}")
            # Return minimal data with error information
            return {
                'title': 'Error al extraer el artículo',
                'text': '',
                'publish_date': datetime.now(timezone.utc).isoformat(),
                'authors': ['Error'],
                'url': url,
                'source': self.name,
                'domain': self.domain,
                'html': '',
                'images': [],
                'keywords': [],
                'summary': f'Error al procesar el artículo: {str(e)}',
                'section': 'error',
                'subsection': ''
            }
    
    def extract_section_from_url(self, url):
        """
        Extract section and subsection from URL.
        Returns a tuple of (section, subsection)
        """
        try:
            # Parse the URL and get the path
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p.strip()]
            
            # Common parts to ignore
            ignore_parts = {'www', 'http', 'https', 'com', 'es', 'noticias', 
                          'actualidad', 'ultimas-noticias', 'articulo', 'noticia'}
            
            # Filter out common parts and numeric parts (like dates or IDs)
            relevant_parts = [p for p in path_parts 
                            if p and 
                            p not in ignore_parts and 
                            not p.replace('-', '').isdigit() and 
                            len(p) > 2]  # Ignore short parts
            
            section = relevant_parts[0] if len(relevant_parts) > 0 else 'general'
            subsection = relevant_parts[1] if len(relevant_parts) > 1 else ''
            
            # Clean up the section/subsection names
            section = section.replace('-', ' ').title().strip()
            subsection = subsection.replace('-', ' ').title().strip()
            
            return section, subsection
            
        except Exception as e:
            logger.warning(f"Error extracting section from URL {url}: {str(e)}")
            return 'general', ''
    
    def clean_text(self, text):
        """Clean text by removing extra whitespace and normalizing."""
        if not text:
            return ''
        if isinstance(text, (list, tuple)):
            text = ' '.join(str(item) for item in text if item)
        text = ' '.join(str(text).split())
        return text.strip()
        
    def clean_authors(self, authors, max_name_length=50):
        """
        Clean and filter author information to extract only actual author names.
        
        Args:
            authors: List of author strings or a single author string
            max_name_length: Maximum allowed length for an author name
            
        Returns:
            List of cleaned author names
        """
        if not authors:
            return []
            
        if isinstance(authors, str):
            authors = [authors]
            
        cleaned_authors = []
        
        # Common patterns to exclude
        exclude_patterns = [
            r'\bpor\b', r'\bde\b', r'\bla\b', r'\bel\b', r'\by\b', r'\bpara\b', r'\bcon\b',
            r'\bactualizado\b', r'\bpublicado\b', r'\bcompartir\b', r'\btwitter\b', r'\bfacebook\b',
            r'\binstagram\b', r'\bwhatsapp\b', r'\btelegram\b', r'\bemail\b', r'\bcorreo\b',
            r'\bcontacto\b', r'\bweb\b', r'\bpágina\b', r'\bpagina\b', r'\bpágina web\b',
            r'\bseguir\b', r'\bseguir leyendo\b', r'\bnoticias relacionadas\b',
            r'\bmas en\b', r'\bmás en\b', r'\bver más\b', r'\bver mas\b', r'\bseguir leyendo\b',
            r'\bcomentarios\b', r'\bcomentar\b', r'\bcomenta\b', r'\bcomentario\b',
            r'\bmin\b', r'\bde lectura\b', r'\blectura\b', r'\bminuto\b', r'\bminutos\b',
            r'\b\d+\s*[a-z]*\s*de\s*lectura\b',  # Matches "X min de lectura"
            r'\b\d+\s*[a-z]*\s*min\b',  # Matches "X min"
            r'\b\d+/\d+/\d+\b',  # Dates
            r'\b\d+:\d+\b',  # Times
            r'\b\d+\s*[a-z]*\s*comentarios?\b',  # Comment counts
            r'^[^a-záéíóúüñ\s]+$',  # No letters (only symbols/numbers)
            r'^[\W_]+$',  # Only symbols
            r'^[0-9\s]+$',  # Only numbers and spaces
            r'\b(redacci[óo]n|redaccion)\b',
            r'\b(equipo|staff|editorial|edici[óo]n|nota de prensa|comunicado|agencias?|ef[ei]?)\b',
            r'\b(por\s+)?(el|la|los|las)\s+',
            r'\b(por|de|en|a|con|para|porque|según)\b',
            r'\b(por|de|en|a|con|para|porque|según)\s+',
            r'\s+(por|de|en|a|con|para|porque|según)\b',
            r'\b(por|de|en|a|con|para|porque|según)\s+',
            r'\b(redacci[óo]n|redaccion|equipo|staff|editorial|edici[óo]n|nota de prensa|comunicado|agencias?|ef[ei]?)\b',
            r'\b(redacci[óo]n|redaccion|equipo|staff|editorial|edici[óo]n|nota de prensa|comunicado|agencias?|ef[ei]?)\s+[a-z]+',
            r'\b(redacci[óo]n|redaccion|equipo|staff|editorial|edici[óo]n|nota de prensa|comunicado|agencias?|ef[ei]?)\s+[a-z]+\s+[a-z]+',
            r'\b(redacci[óo]n|redaccion|equipo|staff|editorial|edici[óo]n|nota de prensa|comunicado|agencias?|ef[ei]?)\s+[a-z]+\s+[a-z]+\s+[a-z]+',
        ]
        
        # Common name patterns to include (must match these patterns)
        include_patterns = [
            r'^[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){1,3}$',  # 2-4 name parts, each capitalized
            r'^[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)*\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+$',  # First and last name capitalized
            r'^[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){1,2}(?:\s+[A-ZÁÉÍÓÚÜÑ]\.?)?$',  # Names with optional initial
        ]
        
        for author in authors:
            if not author:
                continue
                
            # Convert to string and clean
            author = str(author).strip()
            
            # Skip if too long (likely not a name)
            if len(author) > max_name_length:
                logger.debug(f"Skipping long author text: {author}")
                continue
                
            # Skip if matches exclude patterns
            if any(re.search(pattern, author, re.IGNORECASE) for pattern in exclude_patterns):
                logger.debug(f"Excluding author matching exclude pattern: {author}")
                continue
                
            # Must match at least one include pattern
            if not any(re.search(pattern, author) for pattern in include_patterns):
                logger.debug(f"Author doesn't match name patterns: {author}")
                continue
                
            # Additional cleaning
            author = re.sub(r'\s+', ' ', author)  # Normalize spaces
            author = author.strip(' ,.-_|')  # Trim edge characters
            
            # Skip if too short after cleaning
            if len(author) < 3 or len(author.split()) < 2:
                logger.debug(f"Skipping too short author name: {author}")
                continue
                
            # Add if not already in the list (case insensitive)
            if not any(a.lower() == author.lower() for a in cleaned_authors):
                cleaned_authors.append(author)
        
        return cleaned_authors
    
    def export_to_csv(self, articles, filename=None):
        """Export articles to a CSV file."""
        if not articles:
            logger.warning("No articles to export")
            return
            
        if not filename:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"{self.name.lower().replace(' ', '_')}_articles_{date_str}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # Define field names in the desired order with new fields
                fieldnames = [
                    'title', 'url', 'publish_date', 'authors', 
                    'source', 'domain', 'summary', 'section', 'subsection'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='^', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                
                for article in articles:
                    if article:  # Only process non-None articles
                        # Ensure all fields are present and not None
                        row = {field: article.get(field, '') for field in fieldnames}
                        
                        # Ensure no None values in the row
                        for key, value in row.items():
                            if value is None:
                                if key in ['authors']:
                                    row[key] = ['Redacción']
                                elif key == 'publish_date':
                                    row[key] = datetime.now(timezone.utc).isoformat()
                                else:
                                    row[key] = ''
                            
                            # Convert lists to strings
                            if isinstance(row[key], (list, tuple)):
                                row[key] = ', '.join(str(x) for x in row[key] if x)
                    
                        writer.writerow(row)
                    
            logger.info(f"Exported {len([a for a in articles if a])} articles to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting articles to CSV: {str(e)}")
            return None
