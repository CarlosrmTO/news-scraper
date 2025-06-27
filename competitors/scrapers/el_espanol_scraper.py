"""
Dedicated scraper for El Español articles.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config

from competitors.base_scraper import BaseScraper, USER_AGENTS

logger = logging.getLogger(__name__)

class ElEspanolScraper(BaseScraper):
    """Dedicated scraper for El Español articles."""
    
    def __init__(self, config):
        """Initialize with El Español specific configuration."""
        super().__init__(config)
        self.sitemap_url = config.get('sitemap', 'https://www.elespanol.com/sitemap_google_news.xml')
        
    def get_article_data(self, url: str) -> Dict:
        """
        Extract article data from a single El Español URL.
        
        Args:
            url: URL of the article to scrape
            
        Returns:
            Dict containing article data
        """
        try:
            # First, try to get data from the sitemap
            sitemap_data = self._get_article_data_from_sitemap(url)
            
            # Then get the full article content
            article_data = self._scrape_article_content(url)
            
            # Store the sitemap title if it exists
            sitemap_title = sitemap_data.get('title') if sitemap_data else None
            
            # Merge the data, with sitemap data taking precedence
            if sitemap_data:
                article_data.update(sitemap_data)
                
            # If we have a title from the sitemap, ensure it's used
            if sitemap_title:
                article_data['title'] = sitemap_title
            
            # Ensure all required fields are present
            return self._ensure_required_fields(article_data, url)
            
        except Exception as e:
            logger.error(f"Error getting article data for {url}: {str(e)}")
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
    
    def _get_article_data_from_sitemap(self, url: str) -> Dict:
        """
        Extract article data from the sitemap if available.
        
        Args:
            url: URL of the article to find in the sitemap
            
        Returns:
            Dict with article data from sitemap (title, publication date, etc.)
        """
        try:
            # Fetch the sitemap
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/xml, text/xml, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.elespanol.com/'
            }
            
            logger.debug(f"Fetching sitemap: {self.sitemap_url}")
            response = requests.get(self.sitemap_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Find the URL in the sitemap
            for url_element in root.findall('.//sitemap:url', namespaces):
                loc = url_element.find('sitemap:loc', namespaces)
                if loc is not None and loc.text and loc.text.strip() == url.strip():
                    # Found the URL, extract data
                    news = url_element.find('news:news', namespaces)
                    if news is not None:
                        # Extract title from news:title
                        title_elem = news.find('news:title', namespaces)
                        title = title_elem.text.strip() if title_elem is not None and title_elem.text else None
                        
                        # Extract publication date
                        pub_date_elem = news.find('news:publication_date', namespaces)
                        pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else None
                        
                        # Extract publication info
                        publication = news.find('news:publication', namespaces)
                        source = None
                        language = 'es'  # Default to Spanish
                        
                        if publication is not None:
                            pub_name = publication.find('news:name', namespaces)
                            if pub_name is not None and pub_name.text:
                                source = pub_name.text.strip()
                                
                            pub_lang = publication.find('news:language', namespaces)
                            if pub_lang is not None and pub_lang.text:
                                language = pub_lang.text.strip()
                        
                        # Build result dictionary with only non-None values
                        result = {}
                        if title:
                            result['title'] = title
                        if pub_date:
                            result['publish_date'] = pub_date
                        if source:
                            result['source'] = source
                        if language:
                            result['language'] = language
                            
                        logger.debug(f"Found article in sitemap: {title or 'No title'}")
                        return result
            
            # If we get here, the URL wasn't found in the sitemap
            logger.debug(f"URL {url} not found in sitemap")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting data from sitemap for {url}: {str(e)}", exc_info=True)
            return {}
    
    def _scrape_article_content(self, url: str) -> Dict:
        """
        Scrape the actual article content using newspaper3k.
        
        Args:
            url: URL of the article to scrape
            
        Returns:
            Dict with article content
        """
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
            cleaned_authors = self.clean_authors(raw_authors)
            
            # If no authors found after cleaning, try to extract from meta tags
            if not cleaned_authors and hasattr(article, 'meta_data') and article.meta_data:
                meta = article.meta_data
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
                cleaned_authors = self.clean_authors(raw_authors)
            
            # Extract section and subsection from URL
            section, subsection = self.extract_section_from_url(url)
            
            # Get current date if publish_date is not available
            current_date = datetime.now(timezone.utc).isoformat()
            
            # Handle publish_date safely
            publish_date = article.publish_date.isoformat() if article.publish_date else current_date
            
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
            logger.error(f"Error scraping article content for {url}: {str(e)}")
            raise
    
    def _ensure_required_fields(self, article_data: Dict, url: str) -> Dict:
        """Ensure all required fields are present in the article data."""
        required_fields = {
            'title': 'Sin título',
            'text': '',
            'publish_date': datetime.now(timezone.utc).isoformat(),
            'authors': ['Redacción'],
            'url': url,
            'source': self.name,
            'domain': self.domain,
            'html': '',
            'images': [],
            'keywords': [],
            'summary': '',
            'section': 'general',
            'subsection': ''
        }
        
        # Ensure all required fields exist
        for field, default in required_fields.items():
            if field not in article_data or article_data[field] is None:
                article_data[field] = default
        
        return article_data
        
    def get_recent_article_urls(self, sitemap_url: str, max_days_old: int = 1) -> List[str]:
        """
        Get recent article URLs from the sitemap.
        
        Args:
            sitemap_url: URL of the sitemap to fetch
            max_days_old: Maximum age of articles to include (in days)
            
        Returns:
            List of article URLs
        """
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/xml, text/xml, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.elespanol.com/'
            }
            
            logger.info(f"Fetching sitemap: {sitemap_url}")
            response = requests.get(sitemap_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Get current time for comparison
            now = datetime.now(timezone.utc)
            max_age = timedelta(days=max_days_old)
            
            # Find all URLs in the sitemap
            urls = []
            for url_element in root.findall('.//sitemap:url', namespaces):
                try:
                    # Get the URL
                    loc = url_element.find('sitemap:loc', namespaces)
                    if loc is None or not loc.text:
                        continue
                        
                    url = loc.text.strip()
                    
                    # Get the publication date
                    pub_date = None
                    news = url_element.find('news:news', namespaces)
                    if news is not None:
                        pub_date_elem = news.find('news:publication_date', namespaces)
                        if pub_date_elem is not None and pub_date_elem.text:
                            try:
                                pub_date = datetime.fromisoformat(pub_date_elem.text.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                pass
                    
                    # If we couldn't get the publication date, skip this URL
                    if pub_date is None:
                        continue
                        
                    # Check if the article is recent enough
                    if (now - pub_date) <= max_age:
                        urls.append(url)
                        
                except Exception as e:
                    logger.warning(f"Error processing URL element: {str(e)}")
                    continue
            
            logger.info(f"Found {len(urls)} recent articles in sitemap")
            return urls
            
        except Exception as e:
            logger.error(f"Error getting recent article URLs: {str(e)}")
            return []


# Factory function for creating the scraper
def create_el_espanol_scraper(config: Dict, days_back: int = 1) -> List[Dict]:
    """Create and return a list of articles from El Español.
    
    Args:
        config: Configuration dictionary for the scraper
        days_back: Number of days back to look for articles (default: 1)
        
    Returns:
        List of article dictionaries
    """
    try:
        # Create scraper instance
        scraper = ElEspanolScraper(config)
        
        # Get recent article URLs from sitemap
        sitemap_url = config.get('sitemap')
        if not sitemap_url:
            logger.error("No sitemap URL configured for El Español")
            return []
            
        # Get recent article URLs
        article_urls = scraper.get_recent_article_urls(sitemap_url, max_days_old=days_back)
        if not article_urls:
            logger.warning("No recent articles found in sitemap")
            return []
            
        # Process articles (limit to max_articles if specified)
        max_articles = config.get('max_articles', 10)
        article_urls = article_urls[:max_articles]
        
        articles = []
        for url in article_urls:
            try:
                article_data = scraper.get_article_data(url)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                logger.error(f"Error processing article {url}: {str(e)}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"Error in El Español scraper: {str(e)}")
        return []
