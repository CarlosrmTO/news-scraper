"""
Test script for El País scraper.
"""
import sys
import os
import logging
from datetime import datetime, timezone, timedelta

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

def setup_logging():
    """
    Configura el sistema de logging de manera robusta.
    
    Returns:
        logging.Logger: Logger configurado con manejadores de consola y archivo (si es posible).
        Si falla la configuración, devuelve un logger básico que no falla.
    """
    # Primero configuramos un logger básico para asegurar que siempre tengamos logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        # Forzamos a que use el manejador de consola por defecto
        handlers=[logging.StreamHandler()]
    )
    
    logger = logging.getLogger('test_el_pais_scraper')
    
    # Eliminar manejadores existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Configurar el nivel de log
    logger.setLevel(logging.INFO)
    
    # Formato para los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Manejador para consola (siempre disponible)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Intentar configurar archivo de log (opcional, no crítico)
    file_handler = None
    try:
        # Usar directorio temporal si no se puede escribir en el directorio actual
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'test_el_pais_scraper.log')
            
            # Verificar si podemos escribir en el directorio
            test_file = os.path.join(log_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            # Si llegamos aquí, podemos escribir en el directorio
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            
        except (OSError, IOError) as e:
            # Si no podemos escribir en el directorio de logs, usar /tmp
            log_dir = '/tmp/test-el-pais-scraper-logs'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'test_el_pais_scraper.log')
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            
            # Intentar dar permisos amplios para evitar problemas
            try:
                os.chmod(log_dir, 0o777)
                os.chmod(log_file, 0o666) if os.path.exists(log_file) else None
            except:
                pass  # Si falla, continuamos igual
        
        # Configurar el manejador de archivo
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logs guardados en: {log_file}")
        
    except Exception as e:
        # Si falla, solo mostramos un mensaje pero continuamos
        logger.info(f"No se pudo configurar el archivo de log: {str(e)}. Continuando solo con consola.")
    
    return logger

# Configurar logging
logger = setup_logging()

def test_el_pais_scraper():
    """Test the El País scraper."""
    try:
        from competitors.config.el_pais import get_config
        from competitors.scrapers.el_pais_scraper import ElPaisScraper, get_el_pais_articles
        
        # Get the El País configuration
        config = get_config()
        logger.info(f"Testing El País scraper with config: {config['name']}")
        
        # Create a test instance of the scraper
        scraper = ElPaisScraper(config)
        
        # Test fetching RSS entries
        logger.info("Testing RSS feed fetching...")
        entries = scraper.fetch_rss_entries(days_back=1)
        
        if not entries:
            logger.warning("No entries found in the RSS feeds.")
            return False
        
        logger.info(f"Found {len(entries)} recent articles.")
        
        # Display sample article data
        if entries:
            sample = entries[0]
            logger.info("\nSample article data:")
            logger.info(f"Title: {sample.get('title')}")
            logger.info(f"URL: {sample.get('url')}")
            logger.info(f"Published: {sample.get('publish_date')}")
            logger.info(f"Authors: {sample.get('authors')}")
            logger.info(f"Section: {sample.get('section')}")
            logger.info(f"Subsection: {sample.get('subsection')}")
            logger.info(f"Summary: {sample.get('summary', '')[:200]}...")
        
        # Test the exporter
        from competitors.exporters.el_pais_exporter import ElPaisExporter
        
        exporter = ElPaisExporter()
        output_file = exporter.export_articles(entries, config['name'])
        
        if os.path.exists(output_file):
            logger.info(f"Successfully exported articles to: {output_file}")
            
            # Display first few lines of the CSV
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:6]  # Header + first 5 articles
                logger.info("\nCSV file preview:")
                for line in lines:
                    logger.info(line.strip())
            
            return True
        else:
            logger.error("Failed to export articles.")
            return False
            
    except Exception as e:
        logger.error(f"Error testing El País scraper: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting El País scraper test...")
    success = test_el_pais_scraper()
    if success:
        logger.info("El País scraper test completed successfully!")
    else:
        logger.error("El País scraper test failed!")
