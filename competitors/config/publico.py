"""
Configuration for Público sitemap.
"""

def get_config():
    return {
        'name': 'Público',
        'url': 'https://www.publico.es',
        'sitemap': 'https://www.publico.es/sitemap-google-news.xml',  # Usar sitemap de Google News
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.publico_scraper',
        'scraper_function': 'create_publico_scraper',
        'exporter_module': 'competitors.exporters.publico_exporter',
        'exporter_class': 'PublicoExporter',
        'exporter_function': 'export_publico_articles',
        'sitemap_options': {
            'ignore_gz': True,  # Ignorar sitemaps comprimidos
            'news_sitemap': True  # Indica que es un sitemap de noticias
        }
    }
