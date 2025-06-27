"""
Configuration for OKDiario with dedicated scraper.
"""

def get_config():
    return {
        'name': 'OKDiario',
        'url': 'https://okdiario.com',
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.okdiario_scraper',
        'scraper_function': 'create_okdiario_scraper',
        'exporter_module': 'competitors.exporters.okdiario_exporter',
        'exporter_class': 'OKDiarioExporter',
        'exporter_function': 'export_okdiario_articles',
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': False,  # OKDiario usa sitemaps comprimidos
            'timeout': 20  # Aumentar tiempo de espera para este sitio
        },
        'rss_feeds': [
            'https://okdiario.com/feed',
            'https://okdiario.com/feed/actualidad',
            'https://okdiario.com/feed/espana',
            'https://okdiario.com/feed/economia',
            'https://okdiario.com/feed/tecnologia'
        ],
        'use_rss': True,  # Usar RSS como respaldo
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'max_articles': 50,  # Límite de artículos a procesar
        'request_timeout': 15  # Timeout para peticiones HTTP
    }
