"""
Configuration for El Periódico sitemap.
"""

def get_config():
    return {
        'name': 'El Periódico',
        'url': 'https://www.elperiodico.com',
        'sitemap': 'https://www.elperiodico.com/es/google-news.xml',
        'is_own_site': False,
        'use_gsc': False,
        'exporter_module': 'competitors.exporters.el_periodico_exporter',
        'exporter_class': 'ElPeriodicoExporter',
        'exporter_function': 'export_el_periodico_articles',
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        }
    }
