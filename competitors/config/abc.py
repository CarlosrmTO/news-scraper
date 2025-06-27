"""
Configuration for ABC sitemap.
"""

def get_config():
    return {
        'name': 'ABC',
        'url': 'https://www.abc.es',
        'sitemap': 'https://www.abc.es/sitemap-google-news.xml',  # Usar sitemap de Google News
        'is_own_site': False,
        'use_gsc': False,
        'exporter_module': 'competitors.exporters.abc_exporter',
        'exporter_class': 'ABCExporter',
        'exporter_function': 'export_abc_articles',
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        },
        'rss_feeds': [
            'https://www.abc.es/rss/2.0/portada/',
            'https://www.abc.es/rss/2.0/espana/',
            'https://www.abc.es/rss/2.0/internacional/',
            'https://www.abc.es/rss/2.0/economia/'
        ],
        'use_rss': True  # Habilitar el uso de RSS como fuente alternativa
    }
