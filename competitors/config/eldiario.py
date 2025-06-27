"""
Configuration for eldiario.es sitemap and RSS feeds.
"""

def get_config():
    return {
        'name': 'eldiario.es',
        'url': 'https://www.eldiario.es',
        'sitemap': 'https://www.eldiario.es/sitemap_google_news_25b87.xml',
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.eldiario_scraper',
        'scraper_class': 'ElDiarioScraper',
        'scraper_function': 'get_articles',
        'exporter_module': 'competitors.exporters.eldiario_exporter',
        'exporter_class': 'ElDiarioExporter',
        'exporter_function': 'export_eldiario_articles',
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        },
        'rss_feeds': [
            'https://www.eldiario.es/rss/',
            'https://www.eldiario.es/rss/espana/',
            'https://www.eldiario.es/rss/economia/',
            'https://www.eldiario.es/rss/sociedad/'
        ],
        'use_rss': True
    }
