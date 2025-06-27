"""
Export articles from competitor news sites.
"""
import os
import sys
import time
import random
import logging
import importlib
import requests
import feedparser
import xml.etree.ElementTree as ET
import csv
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from typing import Dict, List, Optional, Any, Tuple

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

from competitors import get_all_competitors, get_competitor_by_name
from competitors.base_scraper import BaseScraper

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
        
        # Intentar configurar archivo de log (opcional, no crítico)
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'export_competitors.log')
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logs guardados en: {log_file}")
        except Exception as e:
            # Si falla, solo mostramos un mensaje pero continuamos
            logger.info("No se pudo configurar el archivo de log. Continuando solo con consola.")
        
        return logger
    except Exception as e:
        # Si hay algún error en la configuración del logging, devolvemos un logger básico
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        return logging.getLogger('export_competitors_fallback')

# Configurar logging
logger = setup_logging()

class CompetitorExporter:
    """Handle exporting articles from competitor sites."""
    
    def __init__(self, max_articles: int = 50, days_back: int = 1):
        """Initialize the exporter.
        
        Args:
            max_articles: Maximum number of articles to process per competitor
            days_back: Number of days back to look for articles
        """
        self.max_articles = max_articles
        self.days_back = days_back
        self.output_dir = 'output/competitors'
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _get_exporter_for_competitor(self, competitor: Dict[str, Any]) -> Any:
        """Dynamically load and return the exporter for a competitor.
        
        Args:
            competitor: Competitor configuration dictionary
            
        Returns:
            An instance of the competitor's exporter class, or None if not found
        """
        try:
            # Check for explicit exporter configuration
            if 'exporter_module' in competitor and 'exporter_class' in competitor:
                try:
                    # Dynamically import the exporter module and class
                    module = importlib.import_module(competitor['exporter_module'])
                    exporter_class = getattr(module, competitor['exporter_class'])
                    logger.info(f"Using dedicated exporter for {competitor['name']}")
                    return exporter_class()
                except ImportError as e:
                    logger.warning(f"Could not import exporter module {competitor['exporter_module']}: {e}")
                except AttributeError as e:
                    logger.warning(f"Exporter class {competitor['exporter_class']} not found in {competitor['exporter_module']}")
                except Exception as e:
                    logger.error(f"Error initializing exporter for {competitor['name']}: {str(e)}", exc_info=True)
            
            # Default to None if no exporter is configured or if there was an error
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error getting exporter for {competitor.get('name', 'unknown')}: {str(e)}", exc_info=True)
            return None
    
    def discover_sitemaps(self, base_url):
        """Discover sitemaps from robots.txt and common locations."""
        sitemaps = set()
        
        # Common sitemap locations to check
        common_paths = [
            '/robots.txt',
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap-news.xml',
            '/sitemaps/sitemap.xml',
            '/sitemap/sitemap.xml'
        ]
        
        # Check robots.txt first
        try:
            robots_url = f"{base_url.rstrip('/')}/robots.txt"
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemaps.add(sitemap_url)
        except Exception as e:
            logger.debug(f"Could not fetch robots.txt from {base_url}: {str(e)}")
        
        # Check common sitemap locations
        for path in common_paths:
            sitemap_url = f"{base_url.rstrip('/')}{path}"
            sitemaps.add(sitemap_url)
        
        return list(sitemaps)
    
    def get_sitemap_urls(self, sitemap_url):
        """Extract URLs from a sitemap or sitemap index."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/xml, text/xml',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            
            # If this is a base URL, try to discover sitemaps
            if 'sitemap' not in sitemap_url.lower() and 'robots.txt' not in sitemap_url.lower():
                logger.info(f"Discovering sitemaps for {sitemap_url}")
                sitemaps = self.discover_sitemaps(sitemap_url)
                if sitemaps:
                    all_urls = []
                    for sitemap in sitemaps:
                        all_urls.extend(self.get_sitemap_urls(sitemap))
                    return all_urls
                return []
            
            # If this is robots.txt, parse it for sitemaps
            if sitemap_url.endswith('robots.txt'):
                response = requests.get(sitemap_url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()
                sitemaps = []
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap = line.split(':', 1)[1].strip()
                        sitemaps.append(sitemap)
                if sitemaps:
                    all_urls = []
                    for sitemap in sitemaps:
                        all_urls.extend(self.get_sitemap_urls(sitemap))
                    return all_urls
                return []
            
            # Process regular sitemap
            logger.info(f"Fetching sitemap: {sitemap_url}")
            response = requests.get(sitemap_url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Check if it's gzipped
            if response.headers.get('Content-Type', '').lower() == 'application/x-gzip':
                import gzip
                from io import BytesIO
                with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                    content = f.read()
                root = ET.fromstring(content)
            else:
                root = ET.fromstring(response.content)
            
            # Handle different sitemap formats
            if 'sitemapindex' in root.tag.lower():
                # It's a sitemap index, process each sitemap
                sitemap_urls = []
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None and loc.text:
                        sitemap_urls.append(loc.text)
                
                # Process all found sitemaps
                all_urls = []
                for sitemap in sitemap_urls[:5]:  # Limit to first 5 sitemaps to avoid too many requests
                    all_urls.extend(self.get_sitemap_urls(sitemap))
                return all_urls
            
            # It's a regular sitemap, extract URLs
            urls = []
            for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None and loc.text:
                    urls.append(loc.text)
            
            logger.info(f"Found {len(urls)} URLs in {sitemap_url}")
            return urls
            
        except requests.RequestException as e:
            logger.warning(f"Request error getting sitemap {sitemap_url}: {str(e)}")
            return []
        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML from {sitemap_url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error processing {sitemap_url}: {str(e)}", exc_info=True)
            return []
    
    def get_recent_article_urls(self, sitemap_url, max_days_old=1):
        """Extract recent article URLs from a sitemap or robots.txt."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/xml, text/xml, text/plain',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            logger.info(f"Fetching sitemap: {sitemap_url}")
            
            response = requests.get(sitemap_url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Log response headers for debugging
            logger.debug(f"Response status: {response.status_code}")
            content_type = response.headers.get('Content-Type', '').lower()
            logger.debug(f"Content-Type: {content_type}")
            
            # Check if this is a robots.txt file
            if 'robots.txt' in sitemap_url or 'text/plain' in content_type:
                logger.info("Detected robots.txt, looking for sitemap references")
                sitemap_urls = []
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line[8:].strip()
                        sitemap_urls.append(sitemap_url)
                
                if sitemap_urls:
                    logger.info(f"Found {len(sitemap_urls)} sitemap references in robots.txt")
                    all_urls = []
                    for sitemap in sitemap_urls:
                        try:
                            urls = self.get_recent_article_urls(sitemap, max_days_old)
                            all_urls.extend(urls)
                            logger.info(f"Found {len(urls)} URLs in {sitemap}")
                        except Exception as e:
                            logger.error(f"Error processing sitemap {sitemap}: {str(e)}")
                    return all_urls
                else:
                    logger.warning("No sitemap references found in robots.txt")
                    return []
            
            # Try to parse as XML for sitemap
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError as e:
                logger.error(f"Failed to parse XML from {sitemap_url}: {str(e)}")
                # Try to log first 200 chars of response for debugging
                logger.debug(f"Response content (first 200 chars): {response.text[:200]}")
                return []
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            recent_urls = []
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9',
                'news_sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                '': 'http://www.sitemaps.org/schemas/sitemap/0.9'  # Default namespace
            }
            
            # Try different namespace variations for URL paths
            url_paths = [
                './/sitemap:url',
                './/{http://www.sitemaps.org/schemas/sitemap/0.9}url',
                './/url',
                './/ns:url',
                './/news_sitemap:url'
            ]
            
            # Find all URLs using different namespace variations
            urls = []
            for url_path in url_paths:
                try:
                    found_urls = root.findall(url_path, namespaces=namespaces) if any(ns in url_path for ns in ['sitemap:', 'ns:', 'news_sitemap:']) else root.findall(url_path)
                    if found_urls:
                        logger.info(f"Found {len(found_urls)} URLs using path: {url_path}")
                        urls = found_urls
                        break
                except Exception as e:
                    logger.debug(f"Failed with path {url_path}: {str(e)}")
            
            if not urls:
                logger.error("No valid URLs found in sitemap")
                # Try to log the root tag for debugging
                logger.debug(f"Root tag: {root.tag}")
                logger.debug(f"Root attributes: {root.attrib}")
                return []
            
            # Log the first URL element for debugging
            if len(urls) > 0:
                logger.debug(f"First URL element: {ET.tostring(urls[0], encoding='unicode', method='xml')[:500]}")
            
            processed_count = 0
            skipped_count = 0
            
            for url in urls[:200]:  # Limit to first 200 URLs for testing
                try:
                    # Try different namespace variations for loc
                    loc = None
                    loc_variants = [
                        ('sitemap:loc', namespaces),
                        ('{http://www.sitemaps.org/schemas/sitemap/0.9}loc', None),
                        ('loc', None),
                        ('ns:loc', namespaces),
                        ('news_sitemap:loc', namespaces)
                    ]
                    
                    for loc_path, ns in loc_variants:
                        try:
                            loc = url.find(loc_path, ns) if ns else url.find(loc_path)
                            if loc is not None and loc.text:
                                break
                        except Exception as e:
                            logger.debug(f"Error finding loc with {loc_path}: {str(e)}")
                    
                    if loc is None or not loc.text:
                        logger.debug("Skipping URL without loc")
                        skipped_count += 1
                        continue
                    
                    # Get the URL and clean it
                    url_text = loc.text.strip()
                    
                    # Check lastmod if available
                    lastmod = None
                    lastmod_variants = [
                        ('sitemap:lastmod', namespaces),
                        ('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod', None),
                        ('lastmod', None),
                        ('ns:lastmod', namespaces),
                        ('news:publication_date', namespaces),
                        ('news:publication', namespaces)
                    ]
                    
                    for lastmod_path, ns in lastmod_variants:
                        try:
                            lastmod = url.find(lastmod_path, ns) if ns else url.find(lastmod_path)
                            if lastmod is not None and lastmod.text:
                                break
                        except Exception as e:
                            logger.debug(f"Error finding lastmod with {lastmod_path}: {str(e)}")
                    
                    # If no lastmod, try to get publication date from news namespace
                    if lastmod is None or not lastmod.text:
                        try:
                            news = url.find('news:news', namespaces)
                            if news is not None:
                                publication = news.find('news:publication_date', namespaces)
                                if publication is not None and publication.text:
                                    lastmod = publication
                        except Exception as e:
                            logger.debug(f"Error getting publication date: {str(e)}")
                    
                    # Check if the article is recent
                    is_recent = True
                    if lastmod is not None and lastmod.text:
                        try:
                            lastmod_text = lastmod.text.strip()
                            # Handle different date formats
                            if 'T' in lastmod_text:
                                # ISO format with time
                                if '+' in lastmod_text or 'Z' in lastmod_text:
                                    # Has timezone info
                                    lastmod_date = datetime.fromisoformat(lastmod_text.replace('Z', '+00:00'))
                                else:
                                    # No timezone, assume UTC
                                    lastmod_date = datetime.strptime(lastmod_text, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                            else:
                                # Date only
                                lastmod_date = datetime.strptime(lastmod_text, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            
                            # Compare dates (ignoring timezones for comparison)
                            if lastmod_date.replace(tzinfo=None) < today - timedelta(days=max_days_old):
                                logger.debug(f"Skipping old article from {lastmod_date.date()}: {url_text}")
                                skipped_count += 1
                                is_recent = False
                                continue
                            
                            logger.debug(f"Article date: {lastmod_date}, URL: {url_text}")
                            
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Error parsing date '{lastmod.text}': {str(e)}")
                            # If we can't parse the date, include it to be safe
                            pass
                    
                    if is_recent:
                        logger.debug(f"Adding URL: {url_text}")
                        recent_urls.append(url_text)
                        processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing sitemap entry: {str(e)}", exc_info=True)
                    skipped_count += 1
            
            logger.info(f"Processed {processed_count + skipped_count} URLs: {processed_count} recent, {skipped_count} skipped")
            logger.info(f"Found {len(recent_urls)} recent articles")
            return recent_urls
            
        except requests.RequestException as e:
            logger.error(f"Request error getting sitemap {sitemap_url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error processing {sitemap_url}: {str(e)}", exc_info=True)
            return []
    
    def get_rss_entries(self, rss_url, max_days_old=1, rss_format=None):
        """Fetch and parse RSS feed entries.
        
        Args:
            rss_url (str): URL of the RSS feed
            max_days_old (int): Maximum age of articles to include (in days)
            rss_format (str, optional): Format of the RSS feed ('mrss', 'atom', 'rss', or None for auto-detect)
        """
        try:
            logger.info(f"Fetching RSS feed: {rss_url}")
            
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, application/rss+xml, application/rdf+xml',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
                'Referer': 'https://elpais.com/'
            }
            
            # First, try to get the feed with requests to handle redirects properly
            response = requests.get(rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Check content type to determine feed format if not specified
            content_type = response.headers.get('Content-Type', '').lower()
            if rss_format is None:
                if 'rss' in content_type or 'xml' in content_type:
                    rss_format = 'rss'
                elif 'atom' in content_type:
                    rss_format = 'atom'
                elif 'mrss' in content_type or 'feed' in content_type:
                    rss_format = 'mrss'
                else:
                    # Default to RSS if we can't determine
                    rss_format = 'rss'
            
            # Parse the feed content with feedparser
            feed = feedparser.parse(response.content)
            
            if feed.bozo and not feed.entries:
                logger.warning(f"Error parsing RSS feed {rss_url}: {feed.bozo_exception}")
                # Try to get the feed directly without parsing
                try:
                    root = ET.fromstring(response.content)
                    # Handle the feed as XML directly
                    entries = []
                    today = datetime.now(timezone.utc).date()
                    
                    # Try different XPath expressions to find items
                    for item in root.findall('.//item') or root.findall('.//{*}item'):
                        try:
                            # Get URL
                            link_elem = item.find('link') or item.find('{*}link')
                            if link_elem is None or not link_elem.text:
                                continue
                                
                            # Get title
                            title_elem = item.find('title') or item.find('{*}title')
                            title = title_elem.text if title_elem is not None else 'No title'
                            
                            # Get publication date
                            pub_date = None
                            for date_field in ['pubDate', 'pubdate', 'date', '{http://purl.org/dc/elements/1.1/}date']:
                                date_elem = item.find(date_field) or item.find(f'{{{item.tag.split("}")[0][1:]}}}' + date_field.split('}')[-1] if '}' in date_field else date_field)
                                if date_elem is not None and date_elem.text:
                                    try:
                                        # Try to parse the date in various formats
                                        from dateutil import parser
                                        pub_date = parser.parse(date_elem.text)
                                        if pub_date.tzinfo is None:
                                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                                        break
                                    except (ValueError, AttributeError):
                                        continue
                            
                            # Skip if we can't determine the date or it's too old
                            if pub_date is None or (today - pub_date.date()).days > max_days_old:
                                continue
                            
                            # Get description/summary
                            desc_elem = item.find('description') or item.find('{*}description') or \
                                      item.find('summary') or item.find('{*}summary') or \
                                      item.find('content:encoded', {'content': 'http://purl.org/rss/1.0/modules/content/'})
                            
                            entries.append({
                                'url': link_elem.text.strip(),
                                'title': title.strip() if title else 'No title',
                                'published': pub_date,
                                'summary': desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error processing RSS item: {str(e)}")
                            continue
                    
                    logger.info(f"Found {len(entries)} recent entries in RSS feed (raw XML parsing)")
                    return entries
                    
                except Exception as e:
                    logger.error(f"Error parsing RSS feed as raw XML: {str(e)}")
                    return []
            
            # If we have entries from feedparser, process them
            entries = []
            today = datetime.now(timezone.utc).date()
            
            # Handle MRSS format specifically
            if rss_format == 'mrss':
                if hasattr(feed, 'entries') and feed.entries:
                    # MRSS with entries
                    for entry in feed.entries:
                        try:
                            # Get URL
                            url = entry.get('link', '')
                            if not url and hasattr(entry, 'links') and entry.links:
                                url = entry.links[0].get('href', '')
                            
                            # Skip if no valid URL
                            if not url or not url.startswith(('http://', 'https://')):
                                continue
                            
                            # Get title
                            title = entry.get('title', 'No title')
                            
                            # Get publication date
                            pub_date = None
                            for date_field in ['published_parsed', 'updated_parsed', 'created_parsed', 'date_parsed']:
                                if hasattr(entry, date_field) and getattr(entry, date_field):
                                    pub_date = datetime(*getattr(entry, date_field)[:6], tzinfo=timezone.utc)
                                    break
                            
                            # If no parsed date, try to parse from string
                            if not pub_date:
                                for date_field in ['published', 'updated', 'created', 'date', 'dc:date']:
                                    if hasattr(entry, date_field) and getattr(entry, date_field):
                                        try:
                                            from dateutil import parser
                                            pub_date = parser.parse(str(getattr(entry, date_field)))
                                            if pub_date.tzinfo is None:
                                                pub_date = pub_date.replace(tzinfo=timezone.utc)
                                            break
                                        except (ValueError, AttributeError, TypeError) as e:
                                            logger.debug(f"Error parsing date from {date_field}: {str(e)}")
                                            continue
                            
                            # Skip if we can't determine the date
                            if not pub_date:
                                logger.debug(f"Skipping entry with no date: {url}")
                                continue
                            
                            # Check if the entry is recent enough
                            if (today - pub_date.date()).days > max_days_old:
                                logger.debug(f"Skipping old entry from {pub_date.date()}: {url}")
                                continue
                            
                            # Get description/summary
                            summary = entry.get('summary', entry.get('description', ''))
                            
                            # Add entry data
                            entries.append({
                                'url': url,
                                'title': title,
                                'published': pub_date,
                                'summary': summary
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error processing MRSS entry: {str(e)}")
                            continue
                return entries
            
            # Process standard RSS/Atom feeds
            for entry in feed.entries:
                try:
                    # Get publication date
                    pub_date = None
                    
                    # Try different date fields
                    for date_field in ['published_parsed', 'updated_parsed', 'created_parsed', 'date_parsed']:
                        if hasattr(entry, date_field) and getattr(entry, date_field):
                            pub_date = datetime(*getattr(entry, date_field)[:6], tzinfo=timezone.utc)
                            break
                    
                    # If no parsed date, try to parse from string
                    if not pub_date:
                        for date_field in ['published', 'updated', 'created', 'date', 'dc:date']:
                            if hasattr(entry, date_field) and getattr(entry, date_field):
                                try:
                                    from dateutil import parser
                                    pub_date = parser.parse(getattr(entry, date_field))
                                    if pub_date.tzinfo is None:
                                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                                    break
                                except (ValueError, AttributeError):
                                    continue
                    
                    # Skip if we can't determine the date
                    if not pub_date:
                        logger.debug(f"Skipping entry with no date: {entry.get('link', 'No URL')}")
                        continue
                    
                    # Check if the entry is recent enough
                    if (today - pub_date.date()).days > max_days_old:
                        logger.debug(f"Skipping old entry from {pub_date.date()}: {entry.get('link', 'No URL')}")
                        continue
                    
                    # Get URL - handle both direct and CDATA-wrapped URLs
                    url = ''
                    if hasattr(entry, 'link'):
                        url = entry.link
                    elif hasattr(entry, 'links') and entry.links:
                        url = entry.links[0].get('href', '')
                    
                    # Clean up URL if it's wrapped in CDATA
                    if url.startswith('<![CDATA[') and url.endswith(']]>'):
                        url = url[9:-3].strip()
                    
                    # Skip if no valid URL
                    if not url or not url.startswith(('http://', 'https://')):
                        continue
                    
                    # Clean up title
                    title = entry.get('title', '')
                    if title.startswith('<![CDATA[') and title.endswith(']]>'):
                        title = title[9:-3].strip()
                    
                    # Clean up summary/description
                    summary = entry.get('summary', entry.get('description', ''))
                    if summary.startswith('<![CDATA[') and summary.endswith(']]>'):
                        summary = summary[9:-3].strip()
                    
                    # Add entry data
                    entries.append({
                        'url': url,
                        'title': title or 'No title',
                        'published': pub_date,
                        'summary': summary
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {str(e)}")
                    continue
            
            logger.info(f"Found {len(entries)} recent entries in RSS feed")
            return entries
            
        except requests.RequestException as e:
            logger.error(f"Request error fetching RSS feed {rss_url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error processing RSS feed {rss_url}: {str(e)}", exc_info=True)
            return []
    


    def process_competitor(self, competitor: Dict[str, Any]) -> Optional[str]:
        """Process a single competitor.
        
        Args:
            competitor: Competitor configuration dictionary
            
        Returns:
            str: Path to the exported file, or None if export failed
        """
        try:
            competitor_name = competitor.get('name', 'Unknown')
            logger.info(f"Processing competitor: {competitor_name}")
            logger.debug(f"Competitor configuration: {competitor}")
            
            # Get the appropriate exporter for this competitor
            logger.debug("Getting exporter for competitor")
            exporter = self._get_exporter_for_competitor(competitor)
            logger.debug(f"Exporter for {competitor_name}: {exporter}")
            
            # Check if using a dedicated scraper module
            if 'scraper_module' in competitor and 'scraper_function' in competitor:
                try:
                    logger.debug(f"Using dedicated scraper module: {competitor['scraper_module']}.{competitor['scraper_function']}")
                    # Dynamically import the scraper module and function
                    module = importlib.import_module(competitor['scraper_module'])
                    scraper_func = getattr(module, competitor['scraper_function'])
                    
                    # Call the scraper function with the competitor config and days_back
                    logger.debug(f"Calling scraper function with days_back={self.days_back}")
                    articles = scraper_func(competitor, self.days_back)
                    logger.debug(f"Scraper returned {len(articles) if articles else 0} articles")
                    
                    # Export articles using the dedicated exporter if available, otherwise use default
                    if articles:
                        logger.debug(f"Preparing to export {len(articles)} articles")
                        if exporter:
                            logger.debug("Using dedicated exporter for export")
                            try:
                                output_file = exporter.export_articles(articles, competitor_name)
                                logger.info(f"Exported {len(articles)} articles using dedicated exporter to {output_file}")
                                return output_file
                            except Exception as e:
                                logger.error(f"Error in dedicated exporter: {str(e)}", exc_info=True)
                                return None
                        else:
                            logger.debug("Using default CSV exporter")
                            try:
                                output_file = self.export_articles_to_csv(articles, competitor_name)
                                logger.info(f"Exported {len(articles)} articles using default exporter to {output_file}")
                                return output_file
                            except Exception as e:
                                logger.error(f"Error in default exporter: {str(e)}", exc_info=True)
                                return None
                    else:
                        logger.warning("No articles to export from scraper")
                        return None
                    
                except ImportError as e:
                    logger.error(f"Error importing scraper module {competitor['scraper_module']}: {str(e)}")
                except AttributeError as e:
                    logger.error(f"Scraper function {competitor['scraper_function']} not found in {competitor['scraper_module']}")
                except Exception as e:
                    logger.error(f"Error in {competitor['scraper_module']}.{competitor['scraper_function']}: {str(e)}", exc_info=True)
                
                # Fall back to default processing if scraper fails
                logger.info("Falling back to default processing")
        
            # Default processing (original logic)
            logger.debug("Starting default processing (no dedicated scraper module)")
            article_urls = []
            
            # Check if using RSS feeds
            rss_entries = []
            if competitor.get('use_rss') and competitor.get('rss_feeds'):
                logger.info(f"Using RSS feeds for {competitor['name']}")
                logger.debug(f"RSS feeds: {competitor['rss_feeds']}")
                for rss_url in competitor['rss_feeds']:
                    logger.debug(f"Processing RSS feed: {rss_url}")
                    entries = self.get_rss_entries(rss_url, self.days_back)
                    logger.debug(f"Found {len(entries)} entries in RSS feed")
                    rss_entries.extend(entries)
                    article_urls.extend([entry['url'] for entry in entries])
                logger.debug(f"Total article URLs from RSS: {len(article_urls)}")
            # Fall back to sitemap or sitemaps
            elif 'sitemap' in competitor or 'sitemaps' in competitor:
                sitemap_list = []
                
                # Handle both 'sitemap' (single) and 'sitemaps' (list) for backward compatibility
                if 'sitemap' in competitor and competitor['sitemap']:
                    logger.debug(f"Using single sitemap from 'sitemap' key")
                    if isinstance(competitor['sitemap'], list):
                        sitemap_list.extend(competitor['sitemap'])
                    else:
                        sitemap_list.append(competitor['sitemap'])
                
                if 'sitemaps' in competitor and competitor['sitemaps']:
                    logger.debug(f"Using sitemaps from 'sitemaps' key")
                    if isinstance(competitor['sitemaps'], list):
                        sitemap_list.extend(competitor['sitemaps'])
                    else:
                        sitemap_list.append(competitor['sitemaps'])
                
                logger.info(f"Using {len(sitemap_list)} sitemaps for {competitor['name']}")
                
                # Process each sitemap and collect recent article URLs
                article_urls = []
                for sitemap_url in sitemap_list:
                    try:
                        logger.debug(f"Processing sitemap for recent articles: {sitemap_url}")
                        # Use get_recent_article_urls which already filters by date
                        recent_urls = self.get_recent_article_urls(sitemap_url, self.days_back)
                        logger.debug(f"Found {len(recent_urls)} recent URLs in sitemap")
                        article_urls.extend(recent_urls)
                    except Exception as e:
                        logger.error(f"Error processing sitemap {sitemap_url}: {str(e)}", exc_info=True)
                
                logger.debug(f"Found total of {len(article_urls)} recent article URLs across all sitemaps")
                
                if not article_urls:
                    logger.warning("No recent articles found in any sitemap")
            else:
                logger.warning("No RSS feeds or sitemap configured for this competitor")
            
            # Process the article URLs
            logger.debug(f"Processing {min(len(article_urls), self.max_articles)} article URLs (max_articles={self.max_articles})")
            articles = []
            for i, url in enumerate(article_urls[:self.max_articles], 1):
                try:
                    logger.debug(f"Processing URL {i}/{min(len(article_urls), self.max_articles)}: {url}")
                    
                    # Extract basic metadata from URL
                    url_parts = url.strip('/').split('/')
                    base_domain = competitor.get('url', '').replace('https://', '').replace('http://', '').split('/')[0]
                    
                    # Create article with basic metadata
                    article_data = {
                        'url': url,
                        'title': ' '.join(part.replace('-', ' ').title() for part in url_parts[-1].split('-') if part),
                        'publish_date': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                        'authors': '',
                        'source': competitor.get('name', ''),
                        'domain': base_domain,
                        'summary': '',
                        'section': url_parts[-2].replace('-', ' ').title() if len(url_parts) > 1 else '',
                        'subsection': url_parts[-3].replace('-', ' ').title() if len(url_parts) > 2 else ''
                    }
                    logger.debug(f"Created article data: {article_data}")
                    
                    # If we have RSS entries, try to find a matching entry for more metadata
                    if 'rss_entries' in locals() and rss_entries:
                        logger.debug(f"Checking {len(rss_entries)} RSS entries for URL: {url}")
                        for entry in rss_entries:
                            if entry.get('url') == url:
                                logger.debug(f"Found matching RSS entry for URL: {url}")
                                article_data.update({
                                    'title': entry.get('title', article_data['title']),
                                    'publish_date': entry.get('published', article_data['publish_date']),
                                    'summary': entry.get('summary', '')
                                })
                                logger.debug(f"Updated article data from RSS: {article_data}")
                                break
                    
                    articles.append(article_data)
                    logger.debug(f"Added article to export list (total: {len(articles)})")
                    
                    # Be nice to the server
                    sleep_time = random.uniform(0.5, 1.5)
                    logger.debug(f"Sleeping for {sleep_time:.2f} seconds before next request")
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"Error processing article {url}: {str(e)}", exc_info=True)
                    continue
            
            # Export to CSV using the appropriate exporter
            if articles:
                logger.debug(f"Preparing to export {len(articles)} articles")
                if exporter:
                    logger.debug("Using dedicated exporter for export")
                    try:
                        output_file = exporter.export_articles(articles, competitor_name)
                        logger.info(f"Exported {len(articles)} articles using dedicated exporter to {output_file}")
                        return output_file
                    except Exception as e:
                        logger.error(f"Error in dedicated exporter: {str(e)}", exc_info=True)
                        return None
                else:
                    logger.debug("Using default CSV exporter")
                    try:
                        output_file = self.export_articles_to_csv(articles, competitor_name)
                        logger.info(f"Exported {len(articles)} articles using default exporter to {output_file}")
                        return output_file
                    except Exception as e:
                        logger.error(f"Error in default exporter: {str(e)}", exc_info=True)
                        return None
            else:
                logger.warning("No articles to export")
                return None
            
        except Exception as e:
            logger.error(f"Error processing competitor {competitor.get('name', 'unknown')}: {str(e)}", exc_info=True)
            return None
    
    def filter_recent_urls(self, urls: List[Dict], max_days_old: int = 1) -> List[Dict]:
        """Filter URLs to only include those from the last N days.
        
        Args:
            urls: List of URL entries (dicts with 'url' and optional 'lastmod')
            max_days_old: Maximum number of days old an article can be
            
        Returns:
            List of URL entries that are from the last N days
        """
        if not urls:
            return []
            
        recent_urls = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_days_old)
        
        for entry in urls:
            try:
                url = entry['url'] if isinstance(entry, dict) else entry
                
                # Try to get lastmod from the entry if available (common in sitemaps)
                if isinstance(entry, dict) and 'lastmod' in entry and entry['lastmod']:
                    try:
                        # Try to parse lastmod string to datetime
                        if isinstance(entry['lastmod'], str):
                            # Handle different datetime formats
                            for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z', 
                                      '%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d'):
                                try:
                                    article_date = datetime.strptime(entry['lastmod'], fmt)
                                    if article_date.tzinfo is None:
                                        article_date = article_date.replace(tzinfo=timezone.utc)
                                    if article_date >= cutoff_date:
                                        recent_urls.append(entry)
                                    break
                                except ValueError:
                                    continue
                        continue  # Skip URL-based date extraction if lastmod was available
                    except Exception as e:
                        logger.debug(f"Could not parse lastmod date: {str(e)}")
                
                # Fallback: Try to extract date from URL (common pattern: /YYYY/MM/DD/)
                parsed = urlparse(url)
                path_parts = [p for p in parsed.path.split('/') if p]
                
                # Look for a date pattern in the path
                for i, part in enumerate(path_parts):
                    if part.isdigit() and len(part) == 4:  # Found a year
                        year = int(part)
                        if i + 2 < len(path_parts) and path_parts[i+1].isdigit() and path_parts[i+2].isdigit():
                            month = int(path_parts[i+1])
                            day = int(path_parts[i+2])
                            try:
                                article_date = datetime(year, month, day, tzinfo=timezone.utc)
                                if article_date >= cutoff_date:
                                    recent_urls.append(entry if isinstance(entry, dict) else {'url': url})
                                break
                            except ValueError:
                                continue
            except Exception as e:
                logger.warning(f"Error processing URL {url}: {str(e)}")
                continue
                
        return recent_urls
        
    def export_articles_to_csv(self, articles: List[Dict[str, Any]], competitor_name: str) -> str:
        """Export articles to a CSV file.
        
        Args:
            articles: List of article dictionaries to export
            competitor_name: Name of the competitor (used in folder and filename)
            
        Returns:
            str: Path to the exported CSV file
        """
        try:
            # Clean up the competitor name for use in filenames (lowercase and remove special chars)
            safe_name = "".join(c if c.isalnum() else "_" for c in competitor_name.lower())
            
            # Create competitor-specific output directory if it doesn't exist
            output_dir = os.path.join(self.output_dir, safe_name)
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with date (no timestamp to avoid duplicates)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{safe_name}_articles_{date_str}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # Ensure all articles have all fields
            fieldnames = [
                'title', 'url', 'publish_date', 'authors', 'source', 'domain', 
                'summary', 'section', 'subsection'
            ]
            
            # Write articles to CSV with UTF-8 encoding and ^ delimiter
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=fieldnames, 
                    extrasaction='ignore',
                    delimiter='^',
                    quoting=csv.QUOTE_MINIMAL
                )
                writer.writeheader()
                for article in articles:
                    # Ensure all fields are present and properly encoded
                    row = {}
                    for field in fieldnames:
                        value = article.get(field, '')
                        # Convert to string and ensure proper encoding
                        if value is None:
                            value = ''
                        elif not isinstance(value, str):
                            value = str(value)
                        row[field] = value
                    writer.writerow(row)
            
            logger.info(f"Exported {len(articles)} articles to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting articles to CSV: {str(e)}", exc_info=True)
            raise

    def export_all_competitors(self, competitor_names: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """Export articles for all or specified competitors.
        
        Args:
            competitor_names: Optional list of competitor names to process. If None, all competitors will be processed.
            
        Returns:
            List of tuples containing (competitor_name, output_file_path) for successful exports
        """
        if competitor_names:
            competitors = []
            for name in competitor_names:
                competitor = get_competitor_by_name(name)
                if competitor:
                    competitors.append(competitor)
                else:
                    logger.warning(f"Competitor not found: {name}")
        else:
            competitors = get_all_competitors()
        
        if not competitors:
            logger.error("No competitors to process")
            return []
        
        logger.info(f"Processing {len(competitors)} competitors")
        
        results = []
        
        # Process competitors in parallel with a thread pool
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_competitor = {
                executor.submit(self.process_competitor, comp): comp for comp in competitors
            }
            
            for future in as_completed(future_to_competitor):
                competitor = future_to_competitor[future]
                try:
                    result = future.result()
                    if result:
                        results.append((competitor['name'], result))
                        logger.info(f"Successfully exported articles for {competitor['name']} to {result}")
                    else:
                        logger.warning(f"No articles exported for {competitor['name']}")
                except Exception as e:
                    logger.error(f"Error processing {competitor.get('name', 'unknown')}: {str(e)}", exc_info=True)
        
        logger.info(f"Export complete. Successfully processed {len(results)} out of {len(competitors)} competitors.")
        return results

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Export articles from competitor news sites.')
    parser.add_argument('--competitors', nargs='+', help='Specific competitors to process')
    parser.add_argument('--max-articles', type=int, default=50, help='Maximum number of articles per competitor')
    parser.add_argument('--days-back', type=int, default=1, help='Number of days back to look for articles')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.setLevel(log_level)
    
    # Actualizar el nivel de los handlers existentes
    for handler in logger.handlers:
        handler.setLevel(log_level)
    
    # Asegurarse de que los mensajes se propaguen a los handlers raíz
    logger.propagate = True
    
    exporter = CompetitorExporter(
        max_articles=args.max_articles,
        days_back=args.days_back
    )
    
    logger.info("Starting export process...")
    results = exporter.export_all_competitors(args.competitors)
    
    logger.info("\nExport complete! Results:")
    for name, filepath in results:
        logger.info(f"- {name}: {filepath}")
    
    logger.info("\nAll done!")

if __name__ == "__main__":
    main()
