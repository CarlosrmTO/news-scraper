"""
Dedicated scraper for El Confidencial articles.
"""
import logging
import xml.etree.ElementTree as ET
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from newspaper import Article, Config
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ElConfidencialScraper(BaseScraper):
    """Dedicated scraper for El Confidencial articles."""
    
    def __init__(self, config):
        """Initialize with El Confidencial specific configuration."""
        super().__init__(config)
        self.rss_feeds = config.get('rss_feeds', [])
        
    def get_article_data(self, url: str) -> Dict:
        """
        Extract article data from a single El Confidencial URL.
        
        Args:
            url: URL of the article to scrape
            
        Returns:
            Dict containing article data
        """
        try:
            # Get the full article content
            article_data = self._scrape_article_content(url)
            
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
    
    def get_rss_entries(self, rss_url: str, days_back: int = 1) -> List[Dict]:
        """
        Get recent entries from an RSS feed.
        
        Args:
            rss_url: URL of the RSS feed
            days_back: Maximum age of articles to include (in days)
            
        Returns:
            List of article dictionaries with title, url, and publish_date
        """
        try:
            logger.info(f"Fetching RSS feed: {rss_url}")
            
            # Parse the RSS feed with a custom user agent
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/rss+xml, application/xml, text/xml',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Referer': 'https://www.elconfidencial.com/'
            }
            
            # First try with the direct URL
            feed = feedparser.parse(rss_url, request_headers=headers, agent=headers['User-Agent'])
            
            # If there's a parsing error due to encoding, try downloading the content manually
            # and forcing UTF-8 encoding before parsing
            if feed.bozo and feed.bozo_exception and 'document declared as us-ascii, but parsed as utf-8' in str(feed.bozo_exception):
                logger.debug("Detected encoding issue, trying manual download with forced UTF-8")
                import requests
                from io import BytesIO
                
                response = requests.get(rss_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Force UTF-8 encoding
                content = response.content.decode('utf-8')
                feed = feedparser.parse(content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Error parsing RSS feed {rss_url}: {feed.bozo_exception}")
                return []
                
            entries = []
            now = datetime.now(timezone.utc)
            max_age = timedelta(days=days_back)
            
            for entry in feed.entries:
                try:
                    # Get publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_date = now  # Default to current time if no date found
                    
                    # Skip if too old
                    age = now - pub_date
                    if age > max_age:
                        logger.debug(f"Skipping old article: {entry.get('title', 'No title')} (age: {age} > {max_age})")
                        continue
                    
                    # Extract section from URL if possible
                    section, subsection = self.extract_section_from_url(entry.get('link', ''))
                    
                    # Create article data
                    article_data = {
                        'title': entry.get('title', 'Sin título'),
                        'url': entry.get('link', ''),
                        'publish_date': pub_date.isoformat(),
                        'section': section or 'general',
                        'subsection': subsection or '',
                        'summary': entry.get('summary', entry.get('description', ''))[:500],
                        'authors': self.clean_authors([entry.get('author', '')]) if entry.get('author') else [],
                        'source': self.name,
                        'domain': self.domain
                    }
                    
                    # Clean the data
                    article_data = self._clean_article_data(article_data)
                    
                    entries.append(article_data)
                    logger.debug(f"Added RSS entry: {article_data.get('title')} (published: {pub_date})")
                    
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Found {len(entries)} recent articles in RSS feed: {rss_url}")
            return entries
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {rss_url}: {str(e)}", exc_info=True)
            return []
    
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
                
        # Clean the data
        return self._clean_article_data(article_data)
    
    def _clean_article_data(self, article_data: Dict) -> Dict:
        """Clean and format article data."""
        # Clean text fields
        for field in ['title', 'text', 'summary', 'section', 'subsection']:
            if field in article_data and article_data[field] is not None:
                article_data[field] = self.clean_text(article_data[field])
        
        # Ensure authors is a list
        if 'authors' in article_data and not isinstance(article_data['authors'], list):
            article_data['authors'] = [article_data['authors']] if article_data['authors'] else ['Redacción']
        
        # Clean authors
        if 'authors' in article_data:
            article_data['authors'] = self.clean_authors(article_data['authors'])
            if not article_data['authors']:
                article_data['authors'] = ['Redacción']
        
        # Ensure publish_date is in ISO format
        if 'publish_date' in article_data and article_data['publish_date']:
            try:
                if isinstance(article_data['publish_date'], str):
                    # Try to parse the date string
                    dt = datetime.fromisoformat(article_data['publish_date'].replace('Z', '+00:00'))
                    article_data['publish_date'] = dt.isoformat()
                elif isinstance(article_data['publish_date'], (datetime, datetime.date)):
                    # Convert datetime/date to ISO format string
                    article_data['publish_date'] = article_data['publish_date'].isoformat()
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error formatting publish_date: {str(e)}")
                article_data['publish_date'] = datetime.now(timezone.utc).isoformat()
        else:
            article_data['publish_date'] = datetime.now(timezone.utc).isoformat()
        
        return article_data
    
    def get_recent_article_urls(self, sitemap_url: str = None, max_days_old: int = 1) -> List[str]:
        """
        Get recent article URLs from RSS feeds since El Confidencial doesn't have a public sitemap.
        
        Args:
            sitemap_url: Ignored, kept for compatibility with base class
            max_days_old: Maximum age of articles to include (in days)
            
        Returns:
            List of article URLs
        """
        logger.info("El Confidencial doesn't have a public sitemap, using RSS feeds instead")
        
        # Get articles from all RSS feeds
        all_articles = []
        for feed_url in self.rss_feeds:
            try:
                articles = self.get_rss_entries(feed_url, max_days_old)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error getting articles from RSS feed {feed_url}: {str(e)}", exc_info=True)
        
        # Extract unique URLs
        unique_urls = []
        seen_urls = set()
        
        for article in all_articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(url)
        
        logger.info(f"Found {len(unique_urls)} unique recent articles from RSS feeds")
        return unique_urls


def create_el_confidencial_scraper(config: Dict, days_back: int = 1) -> List[Dict]:
    """
    Create and return a list of articles from El Confidencial.
    
    Args:
        config: Configuration dictionary for the scraper
        days_back: Number of days back to look for articles (default: 1)
        
    Returns:
        List of article dictionaries
    """
    try:
        logger.info(f"Creating El Confidencial scraper for the last {days_back} days")
        
        # Create scraper instance
        scraper = ElConfidencialScraper(config)
        
        # Get recent article URLs from RSS feeds (primary source for El Confidencial)
        urls = []
        if config.get('use_rss', False) and config.get('rss_feeds'):
            logger.info("Fetching articles from RSS feeds")
            for rss_url in config['rss_feeds']:
                try:
                    rss_entries = scraper.get_rss_entries(rss_url, days_back)
                    if rss_entries:
                        urls.extend([entry['url'] for entry in rss_entries])
                        logger.info(f"Found {len(rss_entries)} articles in RSS feed: {rss_url}")
                except Exception as e:
                    logger.error(f"Error processing RSS feed {rss_url}: {str(e)}", exc_info=True)
        
        if not urls:
            logger.warning("No recent articles found in RSS feeds")
            return []
        
        # Process each URL to get article data
        articles = []
        max_articles = config.get('max_articles', 50)  # Default to 50 if not specified
        
        for i, url in enumerate(urls):
            if i >= max_articles:
                logger.info(f"Reached maximum number of articles to process ({max_articles})")
                break
                
            try:
                article_data = scraper.get_article_data(url)
                if article_data:
                    articles.append(article_data)
                    logger.info(f"Processed article {i+1}/{min(len(urls), max_articles)}: {article_data.get('title', 'No title')}")
                else:
                    logger.warning(f"No data returned for URL: {url}")
            except Exception as e:
                logger.error(f"Error processing article {url}: {str(e)}", exc_info=True)
        
        logger.info(f"Successfully processed {len(articles)} articles from El Confidencial")
        return articles
        
    except Exception as e:
        logger.error(f"Error in create_el_confidencial_scraper: {str(e)}", exc_info=True)
        raise
