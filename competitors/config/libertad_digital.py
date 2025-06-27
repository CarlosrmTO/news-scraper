"""
Configuration for Libertad Digital sitemap and RSS feeds.
"""

def get_config():
    return {
        'name': 'Libertad Digital',
        'url': 'https://www.libertaddigital.com',
        'sitemap': 'https://www.libertaddigital.com/sitemap_ultimasnoticias.xml',
        'is_own_site': False,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.libertad_digital_scraper',
        'scraper_class': 'LibertadDigitalScraper',
        'scraper_function': 'get_articles',
        'exporter_module': 'competitors.exporters.libertad_digital_exporter',
        'exporter_class': 'LibertadDigitalExporter',
        'exporter_function': 'export_libertad_digital_articles',
        'rss_feeds': [
            'https://www.libertaddigital.com/rss',
            'https://www.libertaddigital.com/espana/rss.xml',
            'https://www.libertaddigital.com/economia/rss.xml',
            'https://www.libertaddigital.com/ciencia-tecnologia/rss.xml'
        ],
        'sitemap_options': {
            'news_sitemap': True,
            'ignore_gz': True
        },
        'use_rss': True
    }
