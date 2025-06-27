#!/usr/bin/env python3
"""
Script de automatización para ejecutar el scraping de noticias tres veces al día.
Sobrescribe únicamente los archivos del día actual y sube los resultados a Google Drive.
"""

import os
import sys
import json
import logging
import tarfile
import datetime
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timedelta

def setup_logging():
    """Configura el sistema de logging de manera simple y robusta."""
    # Configurar el logger básico solo para consola
    logger = logging.getLogger('news_scraper')
    logger.setLevel(logging.INFO)
    
    # Eliminar manejadores existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Formato para los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Manejador para consola (siempre disponible)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Intentar configurar archivo de log (opcional)
    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        LOGS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, 'logs'))
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        log_file = os.path.join(LOGS_DIR, 'scraper_automation.log')
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Log guardado en: {log_file}")
    except Exception as e:
        # Si falla, continuamos sin archivo de log
        logger.warning(f"No se pudo configurar archivo de log: {e}")
    
    return logger

# Configurar logging al inicio
logger = setup_logging()

# Crear un logger temporal hasta que configuremos el final
logger = logging.getLogger('news_scraper')
logger.info("Iniciando configuración del sistema de logging...")

# Intentar importar las dependencias de Google Drive
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Advertencia: No se encontraron las dependencias de Google Drive. La subida a Drive estará deshabilitada.")

def setup_logging():
    """Configura el sistema de logging con manejo robusto de directorios y permisos."""
    # Configuración inicial del logger
    logger = logging.getLogger('news_scraper')
    logger.setLevel(logging.INFO)
    
    # Eliminar handlers existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Configurar formateador
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configurar handler para consola (siempre disponible)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Intentar configurar el archivo de log
    try:
        # Determinar la ubicación del directorio de logs
        possible_log_dirs = [
            # 1. Directorio del script
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'),
            # 2. Directorio de trabajo actual
            os.path.join(os.getcwd(), 'logs'),
            # 3. Directorio de GitHub Actions (si está disponible)
            os.path.join(os.environ.get('GITHUB_WORKSPACE', ''), 'logs'),
            # 4. Directorio temporal del sistema
            os.path.join('/tmp', 'news-scraper-logs')
        ]
        
        logs_dir = None
        for log_dir in possible_log_dirs:
            try:
                if not log_dir:  # Saltar rutas vacías
                    continue
                    
                # Crear directorio si no existe
                os.makedirs(log_dir, exist_ok=True)
                
                # Verificar permisos de escritura
                test_file = os.path.join(log_dir, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                
                # Si llegamos aquí, el directorio es utilizable
                logs_dir = log_dir
                break
                
            except (OSError, IOError) as e:
                continue
        
        # Si no se pudo encontrar un directorio válido, lanzar excepción
        if not logs_dir:
            raise RuntimeError("No se pudo encontrar un directorio válido para los logs")
        
        # Configurar el archivo de log
        log_file = os.path.join(logs_dir, 'scraper_automation.log')
        
        # Configurar el handler de archivo
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Mensajes de depuración
        logger.info("=" * 60)
        logger.info(f"Directorio de logs: {logs_dir}")
        logger.info(f"Archivo de log: {log_file}")
        logger.info(f"Permisos del directorio: {oct(os.stat(logs_dir).st_mode)[-3:]}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.warning(f"No se pudo configurar el archivo de log: {str(e)}")
        logger.warning("Usando solo consola para logging")
    
    return logger
        
    return logger

# Configurar logging final
logger = setup_logging()
logger.info("Configuración de logging completada correctamente")

def load_config():
    """Cargar configuración desde el archivo JSON."""
    try:
        config_path = Path(__file__).parent / 'config.json'
        logger.info(f"Intentando cargar configuración desde: {config_path}")
        
        if not config_path.exists():
            logger.warning(f"Archivo de configuración no encontrado: {config_path}")
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info("Configuración cargada exitosamente")
            return config
            
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar el archivo de configuración: {e}")
    except Exception as e:
        logger.error(f"Error inesperado al cargar la configuración: {e}")
    
    return {}  # Retornar diccionario vacío en caso de error

def get_today_files(output_dir):
    """Obtener la lista de archivos del día actual."""
    today = datetime.now().strftime('%Y%m%d')
    pattern = f"*{today}*.csv"
    return list(Path(output_dir).rglob(pattern))

def cleanup_old_files(output_dir, days_to_keep):
    """Eliminar archivos más antiguos que el número de días especificado."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    logger.info(f"Limpiando archivos más antiguos que {cutoff_date.strftime('%Y-%m-%d')}")
    
    for file_path in Path(output_dir).rglob('*.csv'):
        try:
            # Extraer fecha del nombre del archivo (formato: *_YYYYMMDD_*.csv)
            date_str = file_path.stem.split('_')[-2]
            file_date = datetime.strptime(date_str, '%Y%m%d')
            
            if file_date < cutoff_date:
                file_path.unlink()
                logger.info(f"Eliminado archivo antiguo: {file_path}")
        except (IndexError, ValueError) as e:
            logger.warning(f"No se pudo procesar la fecha del archivo {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error al procesar el archivo {file_path}: {e}")

def create_archive(output_dir):
    """Crea un archivo comprimido con los archivos CSV generados."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f"news_export_{timestamp}.tar.gz"
    
    with tarfile.open(archive_name, 'w:gz') as tar:
        for file_path in Path(output_dir).rglob('*.csv'):
            tar.add(file_path, arcname=file_path.name)
    
    logger.info(f"Archivo comprimido creado: {archive_name}")
    return archive_name

class GoogleDriveUploader:
    """Clase para manejar la subida de archivos a Google Drive."""
    
    def __init__(self, credentials_file='google-credentials.json'):
        """Inicializa el cliente de Google Drive."""
        self.credentials_file = credentials_file
        self.service = None
        
        if not os.path.exists(credentials_file):
            logger.warning(f"No se encontró el archivo de credenciales: {credentials_file}")
            return
            
        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_file, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Error al inicializar Google Drive: {e}")
    
    def upload_file(self, file_path, folder_id):
        """Sube un archivo a Google Drive."""
        if not self.service:
            logger.warning("No se pudo inicializar el servicio de Google Drive")
            return False
            
        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id] if folder_id else []
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            logger.info(f"Archivo subido a Google Drive: {file.get('name')}")
            logger.info(f"URL de visualización: {file.get('webViewLink')}")
            return True
            
        except HttpError as error:
            logger.error(f"Error al subir el archivo a Google Drive: {error}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al subir a Google Drive: {e}")
            return False

def run_scraping():
    """Ejecutar el proceso de scraping."""
    try:
        # Importar aquí para evitar importaciones circulares
        from export_competitors import main as export_competitors
        
        # Configurar argumentos para export_competitors
        args = argparse.Namespace(
            competitors=None,  # Todos los competidores
            days_back=1,      # Solo hoy
            max_articles=100, # Límite de artículos por competidor
            debug=True        # Mostrar logs detallados
        )
        
        logger.info("Iniciando proceso de scraping...")
        export_competitors(args)
        logger.info("Proceso de scraping completado")
        return True
    except Exception as e:
        logger.error(f"Error durante el scraping: {e}", exc_info=True)
        return False

def main():
    """Función principal del script de automatización."""
    # Cargar configuración
    config = load_config()
    output_dir = config.get('output_dir', 'output/competitors')
    days_to_keep = config.get('days_to_keep', 7)
    google_drive_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    # Crear directorios necesarios
    Path('logs').mkdir(exist_ok=True)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info(f"Iniciando ejecución automática - {datetime.now()}")
    
    try:
        # 1. Ejecutar el scraping
        success = run_scraping()
        
        if success:
            # 2. Limpiar archivos antiguos
            cleanup_old_files(output_dir, days_to_keep)
            
            # 3. Verificar archivos generados
            today_files = get_today_files(output_dir)
            logger.info(f"Archivos generados hoy ({len(today_files)}):")
            for f in today_files:
                logger.info(f"- {f}")
            
            # 4. Crear archivo comprimido con los resultados
            if today_files and GOOGLE_DRIVE_AVAILABLE and google_drive_folder_id:
                archive_path = create_archive(output_dir)
                
                # 5. Subir a Google Drive si está configurado
                if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.path.exists('google-credentials.json'):
                    credentials_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
                    uploader = GoogleDriveUploader(credentials_file)
                    upload_success = uploader.upload_file(archive_path, google_drive_folder_id)
                    
                    if upload_success:
                        logger.info("Archivo subido exitosamente a Google Drive")
                    else:
                        logger.error("Error al subir el archivo a Google Drive")
                else:
                    logger.warning("No se encontraron credenciales de Google Drive")
        else:
            logger.error("El scraping no se completó correctamente")
            
    except Exception as e:
        logger.error(f"Error en la ejecución automática: {e}", exc_info=True)
    
    logger.info(f"Ejecución completada - {datetime.now()}")
    logger.info("=" * 80 + "\n")

if __name__ == "__main__":
    main()
