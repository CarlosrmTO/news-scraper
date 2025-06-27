"""
Base class for all scrapers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    """
    
    @abstractmethod
    def get_article_urls(self, limit: int = 10, **kwargs) -> List[str]:
        """
        Get a list of article URLs from the source.
        
        Args:
            limit: Maximum number of URLs to return
            **kwargs: Additional arguments specific to the implementation
            
        Returns:
            List of article URLs
        """
        pass
    
    @abstractmethod
    def get_article_data(self, url: str) -> Dict[str, Any]:
        """
        Get article data from a URL.
        
        Args:
            url: URL of the article
            
        Returns:
            Dictionary containing article data
        """
        pass
    
    @classmethod
    def clean_text(cls, text: Optional[str]) -> str:
        """
        Clean text by removing extra whitespace and newlines.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ''
        return ' '.join(str(text).split())
