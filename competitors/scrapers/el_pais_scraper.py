"""
Dedicated scraper for El País news articles.
"""
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

# Configure requests session for better performance
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://elpais.com'
})

class ElPaisScraper:
    """Dedicated scraper for El País news articles."""
    
    def __init__(self, config: Dict):
        """Initialize the scraper with configuration."""
        self.config = config
        self.name = config.get('name', 'El País')
        self.base_url = config.get('url', 'https://elpais.com')
        self.rss_feeds = config.get('rss_feeds', [])
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': self.base_url
        }
    
    def fetch_rss_entries(self, days_back: int = 1) -> List[Dict]:
        """
        Fetch and parse RSS feed entries from all configured feeds.
        
        Args:
            days_back: Maximum age of articles to fetch in days
            
        Returns:
            List of unique article dictionaries
        """
        all_entries = []
        seen_urls = set()
        max_articles = self.config.get('max_articles_per_feed', 100)
        
        for rss_url in self.rss_feeds:
            try:
                logger.info(f"Fetching RSS feed: {rss_url}")
                feed_entries = self._fetch_single_feed(rss_url, days_back, max_articles)
                
                # Add only new, unique articles
                new_entries = [
                    entry for entry in feed_entries 
                    if entry['url'] not in seen_urls
                ]
                
                all_entries.extend(new_entries)
                seen_urls.update(entry['url'] for entry in new_entries)
                
                logger.info(f"Added {len(new_entries)} new articles from {rss_url}")
                
                # Be nice to the server
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing feed {rss_url}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Total unique articles fetched: {len(all_entries)}")
        return all_entries
        
    def _fetch_single_feed(self, url: str, days_back: int, max_articles: int) -> List[Dict]:
        """
        Fetch and process a single RSS feed.
        
        Args:
            url: RSS feed URL
            days_back: Maximum age of articles to fetch
            max_articles: Maximum number of articles to process per feed
            
        Returns:
            List of article dictionaries
        """
        try:
            # Use the session for better performance
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"No entries found in feed: {url}")
                return []
                
            # Process entries and filter by date
            min_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            articles = []
            
            for entry in feed.entries[:max_articles]:
                try:
                    article_data = self._process_rss_entry(entry, days_back)
                    if article_data:
                        # Double-check the date in case _process_rss_entry didn't filter it
                        pub_date = date_parser.parse(article_data['publish_date'])
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                            
                        if pub_date >= min_date:
                            articles.append(article_data)
                            
                except Exception as e:
                    logger.warning(f"Error processing entry in {url}: {str(e)}")
                    continue
                    
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {str(e)}")
            return []
    
    def _process_rss_entry(self, entry: Dict, max_days_old: int) -> Optional[Dict]:
        """
        Process a single RSS entry and extract article data.
        
        Args:
            entry: Raw RSS entry data
            max_days_old: Maximum age of articles to process in days
            
        Returns:
            Processed article data as a dictionary, or None if entry should be skipped
        """
        try:
            # Get URL - handle different feed formats
            url = entry.get('link', '')
            if not url and hasattr(entry, 'links') and entry.links:
                url = entry.links[0].get('href', '')
            
            # Clean up URL
            if not url or not isinstance(url, str):
                return None
                
            # Remove tracking parameters and fragments
            url = url.split('#')[0].split('?')[0].strip()
            
            if not url.startswith(('http://', 'https://')):
                return None
            
            # Get title
            title = entry.get('title', 'No title')
            if not title or not isinstance(title, str):
                title = 'No title'
            title = title.strip()
            
            # Get publication date
            pub_date = self._extract_publish_date(entry)
            if not pub_date:
                logger.debug(f"Skipping entry with no date: {url}")
                return None
                
            # Ensure timezone info is present
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            # Check if the entry is recent enough using actual datetime comparison
            if (datetime.now(timezone.utc) - pub_date).days > max_days_old:
                logger.debug(f"Skipping old entry from {pub_date}: {url}")
                return None
            
            # Get author(s)
            authors = self._extract_authors(entry, url)
            
            # Get summary/description
            summary = entry.get('summary', entry.get('description', ''))
            if summary and isinstance(summary, str):
                # Clean up summary text
                summary = ' '.join(summary.split())
                
            # Extract section and subsection from URL
            section, subsection = self._extract_sections(url)
            
            # Try to get section from feed if not found in URL
            if not section and hasattr(entry, 'tags') and entry.tags:
                section = getattr(entry.tags[0], 'term', '') if entry.tags else ''
                if section and isinstance(section, str):
                    section = section.strip()
            
            return {
                'url': url,
                'title': title,
                'publish_date': pub_date.isoformat(),
                'authors': '; '.join(authors) if authors else 'Unknown',
                'source': self.name,
                'domain': self.base_url.replace('https://', '').replace('http://', '').split('/')[0],
                'summary': summary,
                'section': section,
                'subsection': subsection
            }
            
        except Exception as e:
            logger.warning(f"Error processing entry: {str(e)}")
            return None
    
    def _extract_publish_date(self, entry: Dict) -> Optional[datetime]:
        """Extract and parse the publication date from an RSS entry."""
        # Try different date fields in order of preference
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed', 'date_parsed']:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    return datetime(*getattr(entry, date_field)[:6], tzinfo=timezone.utc)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Error parsing {date_field}: {str(e)}")
                    continue
        
        # If no parsed date, try to parse from string fields
        for date_field in ['published', 'updated', 'created', 'date', 'dc:date']:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    date_str = str(getattr(entry, date_field))
                    pub_date = date_parser.parse(date_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    return pub_date
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Error parsing date from {date_field}: {str(e)}")
                    continue
        
        return None
    
    def _extract_authors(self, entry: Dict, url: str) -> List[str]:
        """
        Extract author information from RSS entry or fall back to scraping the article page.
        
        Args:
            entry: Raw RSS entry data
            url: Article URL for fallback scraping
            
        Returns:
            List of author names
        """
        authors = set()
        
        # Try to get authors from RSS entry fields
        if hasattr(entry, 'author') and entry.author:
            if isinstance(entry.author, str):
                authors.add(entry.author.strip())
            elif hasattr(entry.author, 'name') and entry.author.name:
                authors.add(entry.author.name.strip())
        
        if hasattr(entry, 'authors') and entry.authors:
            for author in entry.authors:
                if hasattr(author, 'name') and author.name:
                    author_name = author.name.strip()
                elif hasattr(author, 'email') and author.email:
                    author_name = author.email.split('@')[0].replace('.', ' ').title()
                else:
                    continue
                
                # Clean up author names
                author_name = self._clean_author_name(author_name)
                if author_name:
                    authors.add(author_name)
        
        # If still no authors found, try to scrape the article page
        if not authors:
            try:
                article_authors = self._scrape_article_authors(url)
                for author in article_authors:
                    clean_author = self._clean_author_name(author)
                    if clean_author:
                        authors.add(clean_author)
            except Exception as e:
                logger.debug(f"Error scraping authors from {url}: {str(e)}")
        
        return list(authors)
        
    def _clean_author_name(self, name: str) -> str:
        """
        Clean and normalize author names.
        
        Args:
            name: Raw author name
            
        Returns:
            Cleaned author name or empty string if invalid
        """
        if not name or not isinstance(name, str):
            return ''
            
        # Remove common unwanted text
        name = re.sub(r'\s*[,\n].*$', '', name)  # Remove anything after comma or newline
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
        name = re.sub(r'(?i)\b(por|by|de|en|at|ver perfil|ver bi[oó]graf[ií]a|@[^\s]+|\d+\s*(?:min|hora|d[ií]a|semanas?|mes|años?)\s*(?:de lectura)?\s*|\s*\|\s*[^|]*$)', '', name)
        name = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ-]', '', name)  # Remove special chars but keep accented letters and hyphens
        name = name.strip(' -')  # Remove leading/trailing spaces and hyphens
        
        # Skip names that are too short or generic
        if len(name) < 2 or name.lower() in ['redacción', 'redaccion', 'elpais', 'el país', '']:
            return ''
            
        # Title case the name
        return ' '.join(word.capitalize() for word in name.split())
    
    def _scrape_article_authors(self, url: str) -> List[str]:
        """
        Scrape author information from the article page.
        
        Args:
            url: Article URL to scrape
            
        Returns:
            List of author names found on the page
        """
        try:
            # Use the session for better performance
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check content type to avoid processing non-HTML responses
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.debug(f"Skipping non-HTML response from {url}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. First try to find authors in JSON-LD metadata
            authors = self._extract_authors_from_jsonld(soup)
            if authors:
                return authors
            
            # 2. Check meta tags
            authors.update(self._extract_authors_from_meta(soup))
            
            # 3. Check common author selectors specific to El País
            authors.update(self._extract_authors_from_selectors(soup))
            
            # 4. Check for author links in the article header
            authors.update(self._extract_authors_from_article_header(soup))
            
            return list(authors)
            
        except requests.RequestException as e:
            logger.warning(f"Request error scraping authors from {url}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error scraping authors from {url}: {str(e)}", exc_info=True)
            
        return []
    
    def _extract_authors_from_jsonld(self, soup: BeautifulSoup) -> Set[str]:
        """Extract authors from JSON-LD structured data."""
        authors = set()
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Handle both single item and list of items
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    # Check for author in different possible locations
                    if isinstance(item, dict):
                        # Check for author array
                        if 'author' in item:
                            author = item['author']
                            if isinstance(author, list):
                                for a in author:
                                    if isinstance(a, dict) and 'name' in a:
                                        authors.add(a['name'].strip())
                            elif isinstance(author, dict) and 'name' in author:
                                authors.add(author['name'].strip())
                            elif isinstance(author, str):
                                authors.add(author.strip())
                                
                        # Check for creator
                        if 'creator' in item:
                            creator = item['creator']
                            if isinstance(creator, list):
                                authors.update(c.strip() for c in creator if isinstance(c, str))
                            elif isinstance(creator, str):
                                authors.add(creator.strip())
                                
            except (json.JSONDecodeError, AttributeError):
                continue
                
        return authors
    
    def _extract_authors_from_meta(self, soup: BeautifulSoup) -> Set[str]:
        """Extract authors from meta tags."""
        authors = set()
        
        # Common meta tags for authors
        meta_selectors = [
            {'name': 'author'},
            {'name': 'byl'},
            {'name': 'sailthru.author'},
            {'property': 'article:author'},
            {'property': 'og:article:author'},
            {'name': 'twitter:creator'},
            {'name': 'parsely-author'},
            {'name': 'sailthru.author'},
            {'name': 'article:author'},
        ]
        
        for selector in meta_selectors:
            for meta in soup.find_all('meta', selector):
                content = meta.get('content', '').strip()
                if content:
                    # Clean up the content
                    content = re.sub(r'^https?://[^/]+/', '', content)  # Remove URL parts
                    content = re.sub(r'^@', '', content)  # Remove @ from Twitter handles
                    authors.add(content)
        
        return authors
    
    def _extract_authors_from_selectors(self, soup: BeautifulSoup) -> Set[str]:
        """Extract authors using CSS selectors specific to El País."""
        authors = set()
        
        # El País specific selectors
        selectors = [
            'a[rel="author"]',
            '.a_hi',  # Author link in El País
            '.a_ti',  # Author title in El País
            '.autor-nombre',
            '.author',
            '.author-name',
            '.author_link',
            '.autor-nombre',
            '.byline',
            '.byline__name',
            '.c-byline__author',
            '.entry-author',
            '.firma',
            '.firma a',
            '.firma-autor',
            '.firma_apellidos',
            '.firma_nombre',
            '.firmas_articulo',
            '.firma_autor',
            '.g-author',
            '.nombre_autor',
            '.signature',
            '.vcard',
            'address[class*="author"]',
            'meta[name="author"]',
            'span[class*="author"]',
            'span[class*="byline"]',
            'span[itemprop="author"]',
            'span[itemprop="name"]',
            'time[class*="byline"] + span',
        ]
        
        for selector in selectors:
            for element in soup.select(selector):
                try:
                    # Get text and clean it up
                    text = element.get_text(' ', strip=True)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    # Skip if too long or contains common non-author text
                    if (not text or len(text) > 100 or 
                        any(x in text.lower() for x in ['redacción', 'redaccion', 'elpais.com', 'comentar', 'comentarios', 'seguir'])):
                        continue
                        
                    # Clean up the text
                    text = re.sub(r'^[bB]y\s+', '', text)  # Remove leading "By "
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    if text and len(text) > 1:  # At least 2 characters
                        authors.add(text)
                        
                except Exception as e:
                    logger.debug(f"Error processing selector {selector}: {str(e)}")
                    continue
                    
        return authors
    
    def _extract_authors_from_article_header(self, soup: BeautifulSoup) -> Set[str]:
        """Extract authors from article header sections."""
        authors = set()
        
        # Try to find the article header
        header = (soup.find('header', class_=re.compile(r'(?i)article-header|entry-header')) or 
                 soup.find('div', class_=re.compile(r'(?i)article-header|entry-header')))
        
        if header:
            # Look for author links in the header
            for link in header.find_all('a', href=re.compile(r'(?i)autor|author|escritor|writer')):
                text = link.get_text(strip=True)
                if text and len(text) < 100 and not any(x in text.lower() for x in ['@', 'http', '//']):
                    authors.add(text)
            
            # Look for spans with author-like classes
            for span in header.find_all('span', class_=re.compile(r'(?i)author|byline|firma|firmante|escritor')):
                text = span.get_text(strip=True)
                if (text and 2 <= len(text) <= 100 and 
                    not any(x in text.lower() for x in ['@', 'http', '//', 'comentar', 'comentarios'])):
                    authors.add(text)
        
        return authors
    
    def _extract_sections(self, url: str) -> tuple:
        """Extract section and subsection from URL."""
        try:
            # Remove protocol and domain
            path = url.replace('https://', '').replace('http://', '').split('/', 1)[1]
            
            # Split into parts
            parts = [p for p in path.split('/') if p and not p.startswith('20')]  # Remove date parts
            
            section = parts[0] if len(parts) > 0 else ''
            subsection = parts[1] if len(parts) > 1 else ''
            
            # Clean up section/subsection names
            section = section.replace('-', ' ').title()
            subsection = subsection.replace('-', ' ').title()
            
            return section, subsection
            
        except Exception as e:
            logger.debug(f"Error extracting sections from URL {url}: {str(e)}")
            return '', ''


def get_el_pais_articles(config: Dict, days_back: int = 1) -> List[Dict]:
    """Get recent articles from El País."""
    scraper = ElPaisScraper(config)
    return scraper.fetch_rss_entries(days_back)
