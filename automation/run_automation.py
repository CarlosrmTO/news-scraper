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

# Configuración de rutas para asegurar que los imports funcionen en cualquier entorno
try:
    # Obtener la ruta absoluta del directorio raíz del proyecto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Añadir el directorio raíz al path de Python si no está ya
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Añadir también el directorio automation/ al path por si acaso
    automation_dir = os.path.dirname(os.path.abspath(__file__))
    if automation_dir not in sys.path:
        sys.path.insert(0, automation_dir)
    
    # Debug: Mostrar el path actual de Python
    print("\n=== DEBUG: Python Path ===")
    for i, path in enumerate(sys.path, 1):
        print(f"{i}. {path}")
    print("======================\n")
    
    # Debug: Verificar si los archivos importantes existen
    files_to_check = [
        'export_competitors.py',
        'competitors/__init__.py',
        'competitors/exporters/__init__.py'
    ]
    
    print("=== Verificando archivos importantes ===")
    for file in files_to_check:
        full_path = os.path.join(project_root, file)
        print(f"{file}: {'Existe' if os.path.exists(full_path) else 'No existe'}")
    print("======================================\n")
    
except Exception as e:
    print(f"Error al configurar el path de Python: {e}")
    raise

# Configuración de importaciones para Google Drive
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Advertencia: No se encontraron las dependencias de Google Drive. La subida a Drive estará deshabilitada.")

def setup_logging(disable_file_logging=False):
    """
    Configura el sistema de logging de manera robusta.
    
    Args:
        disable_file_logging (bool): Si es True, deshabilita el logging a archivo.
        
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
    
    logger = logging.getLogger('news_scraper')
    
    # Eliminar manejadores existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Si el logging a archivo está deshabilitado, terminamos aquí
    if disable_file_logging:
        logger.info("Logging a archivo deshabilitado (solo consola)")
        return logger
    
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
            log_file = os.path.join(log_dir, 'scraper_automation.log')
            
            # Verificar si podemos escribir en el directorio
            test_file = os.path.join(log_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            # Si llegamos aquí, podemos escribir en el directorio
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            
        except (OSError, IOError) as e:
            # Si no podemos escribir en el directorio de logs, usar /tmp
            log_dir = '/tmp/news-scraper-logs'
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'scraper_automation.log')
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

# Asegurar que el directorio de logs exista
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
try:
    os.makedirs(log_dir, exist_ok=True)
    # Intentar dar permisos completos para evitar problemas
    os.chmod(log_dir, 0o777)
except Exception as e:
    print(f"No se pudo crear el directorio de logs: {e}")

# Configurar logging final
# Deshabilitar logging a archivo en entornos CI
is_ci = os.getenv('CI', '').lower() in ('true', '1', 't')
logger = setup_logging(disable_file_logging=is_ci)

if is_ci:
    logger.info("Modo CI detectado: Logging a archivo deshabilitado")
else:
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
        # Debug: Mostrar el directorio de trabajo actual
        print("\n=== DEBUG: Directorio de trabajo actual ===")
        print(f"Directorio actual: {os.getcwd()}")
        print("Contenido del directorio:", os.listdir('.'))
        print("======================================\n")
        
        # Lista de posibles rutas de importación a intentar
        import_attempts = [
            ('importación directa', 'export_competitors'),
            ('importación desde raíz', f'{os.path.basename(project_root)}.export_competitors'),
            ('importación absoluta', 'news_scraper.export_competitors')
        ]
        
        export_competitors = None
        last_error = None
        
        for attempt_name, module_path in import_attempts:
            try:
                print(f"\n=== Intentando {attempt_name} desde: {module_path} ===")
                module = __import__(module_path, fromlist=['main'])
                if hasattr(module, 'main'):
                    export_competitors = module.main
                    print(f"✓ {attempt_name} exitosa")
                    break
                else:
                    print(f"✗ {attempt_name}: El módulo no tiene función 'main'")
            except Exception as e:
                last_error = e
                print(f"✗ {attempt_name} falló: {str(e)}")
        
        if export_competitors is None:
            print("\n=== Todas las importaciones fallaron ===")
            print("Último error:", str(last_error))
            print("sys.path:", sys.path)
            print("Directorio actual:", os.getcwd())
            print("======================================\n")
            raise ImportError(f"No se pudo importar export_competitors. Último error: {last_error}")
        
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
