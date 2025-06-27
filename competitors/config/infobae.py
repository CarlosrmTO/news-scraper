"""
Configuration for Infobae sitemap and RSS feeds.
"""

def get_config():
    return {
        'name': 'Infobae',
        'url': 'https://www.infobae.com/espana',
        'sitemap': [
            'https://www.infobae.com/arc/outboundfeeds/sitemap2/',
            'https://www.infobae.com/arc/outboundfeeds/sitemap-news/sitemap.xml'
        ],
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.infobae_scraper',
        'scraper_class': 'InfobaeScraper',
        'scraper_function': 'get_articles',
        'exporter_module': 'competitors.exporters.infobae_exporter',
        'exporter_class': 'InfobaeExporter',
        'exporter_function': 'export_infobae_articles',
        'rss_feeds': [
            'https://www.infobae.com/feeds/rss/',
            'https://www.infobae.com/espana/feed/',
            'https://www.infobae.com/america/feed/'
        ],
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        },
        'use_rss': True
    }
