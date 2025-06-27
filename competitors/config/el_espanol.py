"""
Configuration for El Español sitemap.
"""

def get_config():
    return {
        'name': 'El Español',
        'url': 'https://www.elespanol.com',
        'sitemap': 'https://www.elespanol.com/sitemap_google_news.xml',  # Usar sitemap de Google News
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.el_espanol_scraper',
        'scraper_class': 'ElEspanolScraper',
        'scraper_function': 'create_el_espanol_scraper',
        'exporter_module': 'competitors.exporters.el_espanol_exporter',
        'exporter_class': 'ElEspanolExporter',
        'exporter_function': 'export_el_espanol_articles',
        'sitemap_options': {
            'news_sitemap': True,  # Es un sitemap de noticias
            'ignore_gz': True,
            'timeout': 20,  # Aumentar tiempo de espera para este sitio
            'follow_sitemap_links': False  # No seguir enlaces dentro del sitemap
        },
        'rss_feeds': [
            # Deshabilitados temporalmente debido a errores 404
            # 'https://www.elespanol.com/feeds/rss/portada.xml',
            # 'https://www.elespanol.com/feeds/rss/espana.xml',
            # 'https://www.elespanol.com/feeds/rss/internacional.xml',
            # 'https://www.elespanol.com/feeds/rss/economia.xml'
        ],
        'use_rss': False,  # Deshabilitar temporalmente RSS
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://www.elespanol.com/'
        },
        'date_from': 'now-1d',  # Solo artículos del último día
        'date_to': 'now',
        'max_articles': 50  # Límite de artículos a procesar
    }
