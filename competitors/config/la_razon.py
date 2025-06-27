"""
Configuration for La Razón sitemap.
"""

def get_config():
    return {
        'name': 'La Razón',
        'url': 'https://www.larazon.es',
        'sitemap': 'https://www.larazon.es/sitemaps/news.xml',
        'is_own_site': False,
        'use_gsc': False,
        'exporter_module': 'competitors.exporters.la_razon_exporter',
        'exporter_class': 'LaRazonExporter',
        'exporter_function': 'export_la_razon_articles'
    }
