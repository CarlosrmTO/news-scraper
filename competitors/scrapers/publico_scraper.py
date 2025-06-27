"""
Dedicated scraper for Público articles.
"""
import logging
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from newspaper import Article, Config
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PublicoScraper(BaseScraper):
    """Dedicated scraper for Público articles."""
    
    def __init__(self, config):
        """Initialize with Público specific configuration."""
        super().__init__(config)
        self.sitemap_url = config.get('sitemap', 'https://www.publico.es/sitemap-google-news.xml')
        
    def get_article_data(self, url: str) -> Dict:
        """
        Extract article data from a single Público URL.
        
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
            logger.info(f"Fetching sitemap: {self.sitemap_url}")
            response = requests.get(
                self.sitemap_url,
                headers={'User-Agent': self.get_random_user_agent()},
                timeout=15
            )
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Define namespaces for Público's sitemap
            namespaces = {
                'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1'
            }
            
            # Find the article in the sitemap
            for url_elem in root.findall('.//ns:url', namespaces):
                loc_elem = url_elem.find('ns:loc', namespaces)
                if loc_elem is not None and loc_elem.text.strip() == url:
                    # Found the article, extract data
                    news_elem = url_elem.find('news:news', namespaces)
                    if news_elem is not None:
                        title_elem = news_elem.find('news:title', namespaces)
                        pub_date_elem = news_elem.find('news:publication_date', namespaces)
                        
                        # Extract section from URL
                        section, subsection = self.extract_section_from_url(url)
                        
                        # Format the result
                        result = {
                            'title': title_elem.text if title_elem is not None else None,
                            'publish_date': pub_date_elem.text if pub_date_elem is not None else None,
                            'section': section,
                            'subsection': subsection
                        }
                        
                        logger.debug(f"Found article in sitemap: {result.get('title', 'No title')}")
                        return self._clean_article_data(result)
            
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
        Get recent article URLs from the sitemap.
        
        Args:
            sitemap_url: URL of the sitemap to fetch (defaults to the one in config)
            max_days_old: Maximum age of articles to include (in days)
            
        Returns:
            List of article URLs
        """
        if sitemap_url is None:
            sitemap_url = self.sitemap_url
            
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/xml, text/xml, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.publico.es/'
            }
            
            logger.info(f"Fetching sitemap: {sitemap_url}")
            response = requests.get(sitemap_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Define namespaces for Público's sitemap
            namespaces = {
                'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1'
            }
            
            # Get current time for comparison
            now = datetime.now(timezone.utc)
            max_age = timedelta(days=max_days_old)
            
            # Find all URLs in the sitemap
            urls = []
            for url_elem in root.findall('.//ns:url', namespaces):
                try:
                    # Get the URL
                    loc_elem = url_elem.find('ns:loc', namespaces)
                    if loc_elem is None or not loc_elem.text:
                        continue
                        
                    url = loc_elem.text.strip()
                    
                    # Get the publication date
                    pub_date = None
                    news_elem = url_elem.find('news:news', namespaces)
                    if news_elem is not None:
                        pub_date_elem = news_elem.find('news:publication_date', namespaces)
                        if pub_date_elem is not None and pub_date_elem.text:
                            try:
                                # Handle different date formats
                                pub_date_str = pub_date_elem.text
                                if 'Z' in pub_date_str:
                                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                                else:
                                    pub_date = datetime.fromisoformat(pub_date_str)
                                    
                                # If the datetime is naive, assume it's in UTC
                                if pub_date.tzinfo is None:
                                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                            except (ValueError, AttributeError) as e:
                                logger.warning(f"Error parsing date '{pub_date_elem.text}': {str(e)}")
                                continue
                    
                    # If we couldn't get the publication date, skip this URL
                    if pub_date is None:
                        logger.debug(f"Skipping URL {url} - no publication date found")
                        continue
                        
                    # Check if the article is recent enough
                    age = now - pub_date
                    if age <= max_age:
                        urls.append(url)
                        logger.debug(f"Added URL: {url} (published: {pub_date}, age: {age})")
                    else:
                        logger.debug(f"Skipping old article: {url} (published: {pub_date}, age: {age} > {max_age})")
                        
                except Exception as e:
                    logger.warning(f"Error processing URL element: {str(e)}")
                    continue
            
            logger.info(f"Found {len(urls)} recent articles in sitemap")
            return urls
            
        except Exception as e:
            logger.error(f"Error fetching recent article URLs from {sitemap_url}: {str(e)}", exc_info=True)
            return []


def create_publico_scraper(config: Dict, days_back: int = 1) -> List[Dict]:
    """
    Create and return a list of articles from Público.
    
    Args:
        config: Configuration dictionary for the scraper
        days_back: Number of days back to look for articles (default: 1)
        
    Returns:
        List of article dictionaries
    """
    try:
        logger.info(f"Creating Público scraper for the last {days_back} days")
        
        # Create scraper instance
        scraper = PublicoScraper(config)
        
        # Get recent article URLs
        sitemap_url = config.get('sitemap', 'https://www.publico.es/sitemap-google-news.xml')
        urls = scraper.get_recent_article_urls(sitemap_url, days_back)
        
        if not urls:
            logger.warning("No recent articles found in the sitemap")
            return []
        
        # Process each URL to get article data
        articles = []
        for url in urls:
            try:
                article_data = scraper.get_article_data(url)
                if article_data:
                    articles.append(article_data)
                    logger.info(f"Processed article: {article_data.get('title', 'No title')}")
                else:
                    logger.warning(f"No data returned for URL: {url}")
            except Exception as e:
                logger.error(f"Error processing article {url}: {str(e)}", exc_info=True)
        
        logger.info(f"Successfully processed {len(articles)} articles from Público")
        return articles
        
    except Exception as e:
        logger.error(f"Error in create_publico_scraper: {str(e)}", exc_info=True)
        raise
