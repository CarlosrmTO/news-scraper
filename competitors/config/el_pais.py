"""
Configuration for El País RSS feed.
"""

def get_config():
    return {
        'name': 'El País',
        'url': 'https://elpais.com',
        'rss_feeds': [
            # Main feeds
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',  # Main feed
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ultimas-noticias/portada',  # Latest news
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/lo-mas-visto/portada',  # Most viewed
            
            # Main sections
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada',  # Spain
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',  # International
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada',  # Economy
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada',  # Science
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada',  # Technology
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/cultura/portada',  # Culture
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/estilo/portada',  # Lifestyle
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada',  # Sports
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/television/portada',  # TV
            'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/gente/portada',  # People
            
            # Special sections
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/opinion',  # Opinion
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/clima-y-medio-ambiente',  # Climate & Environment
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/educacion',  # Education
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/gastronomia',  # Gastronomy
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/planeta-futuro',  # Future Planet
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/ideas',  # Ideas
            
            # Magazines & Supplements
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/eps',  # EPS magazine
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/babelia',  # Babelia (Culture)
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/elviajero',  # El Viajero (Travel)
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/icon',  # ICON Design
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/smoda',  # S Moda
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/mamas-papas',  # Mamas & Papas
            
            # Multimedia
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/gallery',  # Photos
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/videos',  # Videos
            'https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/section/podcasts'  # Podcasts
        ],
        'is_own_site': False,
        'use_gsc': False,
        'use_rss': True,  # Indicate that we're using RSS feeds
        'exporter_module': 'competitors.exporters.el_pais_exporter',
        'exporter_class': 'ElPaisExporter',
        'exporter_function': 'export_el_pais_articles',
        'scraper_module': 'competitors.scrapers.el_pais_scraper',  # Dedicated scraper module
        'scraper_function': 'get_el_pais_articles',  # Function to call in the scraper module
        'exporter_module': 'competitors.exporters.el_pais_exporter',  # Dedicated exporter module
        'exporter_function': 'export_el_pais_articles',  # Function to call in the exporter module
        'max_articles_per_feed': 50,  # Reduced to avoid hitting rate limits
        'request_delay': 1,  # 1 second delay between requests
        'timeout': 15,  # 15 seconds timeout for requests
        'retry_attempts': 3,  # Number of retry attempts for failed requests
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'headers': {
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': 'https://elpais.com',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
    }
