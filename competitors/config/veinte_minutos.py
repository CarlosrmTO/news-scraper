"""
Configuration for 20minutos using the existing scraper with a wrapper.
"""

def get_config():
    return {
        'name': '20minutos',
        'url': 'https://www.20minutos.es',
        'is_own_site': True,
        'use_gsc': False,
        'scraper_module': 'competitors.scrapers.veinte_minutos_scraper',
        'scraper_function': 'get_articles',
        'exporter_module': 'competitors.exporters.base_exporter',
        'exporter_function': 'export_articles_to_csv',
        'output_file': 'output/noticias_20minutos.csv'  # Mantener la misma ruta de salida
    }
