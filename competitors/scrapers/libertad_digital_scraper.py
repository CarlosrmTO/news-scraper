"""
Dedicated scraper for Libertad Digital articles.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse

from newspaper import Article
import requests
from bs4 import BeautifulSoup

class LibertadDigitalScraper:
    """Dedicated scraper for Libertad Digital articles."""
    
    def __init__(self, config: Dict):
        """Initialize with a competitor config."""
        self.config = config
        self.name = config['name']
        self.base_url = config['url']
        self.domain = urlparse(self.base_url).netloc
        self.output_dir = os.path.join('output', 'competitors', 'libertad_digital')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure user agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        ]
    
    def get_article_data(self, url: str) -> Optional[Dict]:
        """Extract article data from a single URL."""
        try:
            # Use newspaper3k to extract article content
            article = Article(url, language='es')
            article.download()
            article.parse()
            
            # Extract authors from meta tags (common in Libertad Digital)
            authors = []
            if hasattr(article, 'meta_data') and 'author' in article.meta_data:
                authors = [article.meta_data['author']]
            
            # Extract section from URL path
            section = urlparse(url).path.split('/')[1] if len(urlparse(url).path.split('/')) > 1 else ''
            
            return {
                'title': article.title,
                'url': url,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'authors': authors,
                'content': article.text,
                'section': section,
                'domain': self.domain,
                'source': 'Libertad Digital',
                'summary': article.meta_description if hasattr(article, 'meta_description') else ''
            }
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None
    
    def get_recent_articles(self, days_back: int = 1, max_articles: int = 10) -> List[Dict]:
        """Get recent articles from Libertad Digital.
        
        Args:
            days_back: Number of days to look back for articles
            max_articles: Maximum number of articles to return
            
        Returns:
            List of article dictionaries
        """
        # Get sitemap URLs from config
        sitemap_urls = []
        if 'sitemap' in self.config:
            if isinstance(self.config['sitemap'], list):
                sitemap_urls.extend(self.config['sitemap'])
            else:
                sitemap_urls.append(self.config['sitemap'])
        
        # Add RSS feeds if available
        if 'rss_feeds' in self.config:
            sitemap_urls.extend(self.config['rss_feeds'])
        
        # Process each sitemap/RSS feed
        articles = []
        for sitemap_url in sitemap_urls:
            try:
                if 'rss' in sitemap_url.lower():
                    # Handle RSS feed
                    articles.extend(self._process_rss_feed(sitemap_url, days_back, max_articles - len(articles)))
                else:
                    # Handle sitemap
                    articles.extend(self._process_sitemap(sitemap_url, days_back, max_articles - len(articles)))
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                print(f"Error processing {sitemap_url}: {str(e)}")
        
        return articles[:max_articles]
    
    def _process_sitemap(self, sitemap_url: str, days_back: int, max_articles: int) -> List[Dict]:
        """Process a sitemap and return recent articles."""
        try:
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            # Extract URLs from sitemap
            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')][:max_articles]
            
            # Process each URL
            articles = []
            for url in urls:
                article_data = self.get_article_data(url)
                if article_data:
                    articles.append(article_data)
                
                if len(articles) >= max_articles:
                    break
            
            return articles
            
        except Exception as e:
            print(f"Error processing sitemap {sitemap_url}: {str(e)}")
            return []
    
    def _process_rss_feed(self, rss_url: str, days_back: int, max_articles: int) -> List[Dict]:
        """Process an RSS feed and return recent articles."""
        try:
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
            
            # Parse RSS feed
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:max_articles]
            
            # Process each item
            articles = []
            for item in items:
                url = item.find('link').text
                article_data = self.get_article_data(url)
                if article_data:
                    articles.append(article_data)
                
                if len(articles) >= max_articles:
                    break
            
            return articles
            
        except Exception as e:
            print(f"Error processing RSS feed {rss_url}: {str(e)}")
            return []

def get_articles(config: Dict, days_back: int = 1, max_articles: int = 10) -> List[Dict]:
    """Get recent articles from Libertad Digital.
    
    Args:
        config: Competitor configuration
        days_back: Number of days to look back for articles
        max_articles: Maximum number of articles to return
        
    Returns:
        List of article dictionaries
    """
    scraper = LibertadDigitalScraper(config)
    return scraper.get_recent_articles(days_back, max_articles)
