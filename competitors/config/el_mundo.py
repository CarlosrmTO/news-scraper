"""
Configuration for El Mundo using sitemaps.
"""

def get_config():
    return {
        'name': 'El Mundo',
        'url': 'https://www.elmundo.es',
        'sitemaps': [
            'https://www.elmundo.es/sitemaps/noticia_news_ahcoupiaCazadei7kae6theepho5no7o.xml',
            'https://www.elmundo.es/sitemaps/directo_news_ahcoupiafssfdsdfi7kae6theepho5no7o.xml',
            'https://www.elmundo.es/sitemaps/videoct_news_ba306c30e4f41fc8f7a5e2d166e42a3b.xml'
        ],
        'is_own_site': False,
        'use_gsc': False,
        'exporter_module': 'competitors.exporters.el_mundo_exporter',
        'exporter_class': 'ElMundoExporter',
        'exporter_function': 'export_el_mundo_articles'
    }
