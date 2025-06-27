"""
Configuration for Vozpópuli sitemap and RSS feeds.
"""

def get_config():
    return {
        'name': 'Vozpópuli',
        'url': 'https://www.vozpopuli.com',
        'sitemap': [
            'https://www.vozpopuli.com/sitemaps/sitemap-news2.xml',
            'https://www.vozpopuli.com/sitemap_index.xml'
        ],
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.voz_populi_scraper',
        'scraper_class': 'VozPopuliScraper',
        'scraper_function': 'get_articles',
        'exporter_module': 'competitors.exporters.voz_populi_exporter',
        'exporter_class': 'VozPopuliExporter',
        'exporter_function': 'export_voz_populi_articles',
        'rss_feeds': [
            'https://www.vozpopuli.com/rss',
            'https://www.vozpopuli.com/rss/portada.xml',
            'https://www.vozpopuli.com/rss/ultima-hora.xml'
        ],
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        },
        'use_rss': True
    }
