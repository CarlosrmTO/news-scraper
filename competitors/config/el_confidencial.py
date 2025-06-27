"""
Configuration for El Confidencial.

Note: El Confidencial doesn't have a public sitemap, so we rely on RSS feeds.
"""

def get_config():
    return {
        'name': 'El Confidencial',
        'url': 'https://www.elconfidencial.com',
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.el_confidencial_scraper',
        'scraper_function': 'create_el_confidencial_scraper',
        'exporter_module': 'competitors.exporters.el_confidencial_exporter',
        'exporter_class': 'ElConfidencialExporter',
        'exporter_function': 'export_el_confidencial_articles',
        # List of RSS feeds to use as content sources
        'rss_feeds': [
            'https://rss.elconfidencial.com/espana/',
            'https://rss.elconfidencial.com/economia/',
            'https://rss.elconfidencial.com/tecnologia/',
            'https://rss.elconfidencial.com/mundo/',
            'https://rss.elconfidencial.com/empresas/',
            'https://rss.elconfidencial.com/mercados/'
        ],
        'use_rss': True,  # RSS is the primary source for El Confidencial
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'max_articles': 100,  # Increased limit since we're using RSS feeds
        'request_timeout': 15  # Timeout for HTTP requests in seconds
    }
