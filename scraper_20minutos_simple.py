import requests
import json
import time
import random
import re  # Para manejar expresiones regulares
import argparse
import csv
import os
from newspaper import Article, Config
from datetime import datetime, timedelta

# Configuración
site = '20min'

FEEDS_RSS = [
    ('20Min home', 'https://www.20minutos.es/rss')
]

user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
]

def clean_author_name(author):
    """Limpia un nombre de autor individual"""
    if not author or not isinstance(author, str):
        return None
        
    # Eliminar espacios al inicio y final
    author = author.strip()
    
    # Patrones a eliminar
    patterns_to_remove = [
        r'(?i)redactor[\w\s]*',
        r'(?i)periodista[\w\s]*',
        r'(?i)en \w+',
        r'(?i)en linkedin',
        r'(?i)en x',
        r'(?i)en twitter',
        r'(?i)ver sus artículos',
        r'(?i)líder en los diarios más leídos',
        r'(?i)consulta las últimas noticias',
        r'(?i)diario gratuito',
        r'(?i)referencia en españa',
        r'\s+',  # Múltiples espacios
        r'[\.,;]$'  # Puntos o comas al final
    ]
    
    # Aplicar patrones de limpieza
    for pattern in patterns_to_remove:
        author = re.sub(pattern, ' ', author)
    
    # Eliminar caracteres no deseados
    author = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ-]', ' ', author)
    
    # Normalizar espacios
    author = ' '.join(author.split())
    
    # Verificar si el autor es válido
    if len(author) < 3 or len(author.split()) > 5:
        return None
        
    # Capitalizar nombres propios
    author = ' '.join(word.capitalize() for word in author.split())
    
    return author if author and len(author) > 2 else None

def extract_authors(article):
    """Extrae los autores del artículo de manera más efectiva"""
    # Primero intentamos con article.authors
    authors = []
    
    # Extraer de article.authors
    if hasattr(article, 'authors') and article.authors:
        authors.extend(article.authors)
    
    # Extraer de metadatos
    if hasattr(article, 'meta_data'):
        # De meta_data.author
        if article.meta_data.get('author'):
            authors.append(article.meta_data['author'])
            
        # De meta_data.og
        if 'og' in article.meta_data and article.meta_data['og'].get('author'):
            authors.append(article.meta_data['og']['author'])
    
    # Limpiar y filtrar autores
    cleaned_authors = []
    seen = set()
    
    for author in authors:
        if not author:
            continue
            
        # Si es una lista, extender en lugar de añadir
        if isinstance(author, (list, tuple)):
            cleaned_authors.extend(author)
        else:
            cleaned_authors.append(author)
    
    # Limpiar cada autor
    final_authors = []
    for author in cleaned_authors:
        if not author:
            continue
            
        # Si el autor es una cadena con múltiples nombres separados por comas
        if isinstance(author, str) and (',' in author or ' y ' in author):
            # Separar por comas o 'y'
            sub_authors = re.split(r'[,;]|\s+y\s+', author)
            for sub_author in sub_authors:
                cleaned = clean_author_name(sub_author)
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    final_authors.append(cleaned)
        else:
            cleaned = clean_author_name(author)
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                final_authors.append(cleaned)
    
    # Si no encontramos autores, usar la fuente como último recurso
    if not final_authors and hasattr(article, 'source_url'):
        source = article.source_url
        if '20minutos' in source:
            final_authors = ['20minutos']
    
    return final_authors if final_authors else ['20minutos']  # Valor por defecto

def get_article_data(url):
    """Obtiene el contenido de un artículo"""
    try:
        user_agent = random.choice(user_agents)
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 30
        
        article = Article(url, config=config, headers={'User-Agent': user_agent})
        article.download()
        article.parse()
        
        # Extraer autores mejorados
        authors = extract_authors(article)
        
        return {
            'title': article.title,
            'text': article.text,
            'publish_date': article.publish_date,
            'authors': authors,  # Usar los autores extraídos
            'url': url,
            'html': article.html[:500] + '...' if article.html else '',  # Solo guardamos un fragmento
            'images': list(article.images)[:5],  # Limitar a 5 imágenes
            'keywords': article.keywords[:10],  # Limitar a 10 palabras clave
            'summary': article.summary
        }
    except Exception as e:
        print(f"Error al procesar {url}: {str(e)}")
        return None

def fetch_rss_feed(feed_url):
    """Obtiene el feed RSS"""
    try:
        headers = {'User-Agent': random.choice(user_agents)}
        response = requests.get(feed_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error al obtener el feed RSS: {str(e)}")
        return None

def parse_rss(xml_content):
    """Parsea el contenido XML del feed RSS"""
    # Esta es una implementación básica. Para producción, considera usar una biblioteca como feedparser
    from xml.etree import ElementTree as ET
    
    try:
        root = ET.fromstring(xml_content)
        items = []
        
        # Buscar todos los elementos 'item' en el feed
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else 'Sin título'
            link = item.find('link').text if item.find('link') is not None else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
            
            items.append({
                'title': title,
                'link': link,
                'pub_date': pub_date
            })
            
        return items
    except Exception as e:
        print(f"Error al parsear el RSS: {str(e)}")
        return []

def clean_text(text):
    """Limpia el texto para ser guardado en CSV"""
    if text is None:
        return ''
    # Convertir a string por si acaso
    text = str(text)
    # Reemplazar saltos de línea por espacios
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Eliminar comas múltiples y espacios extras
    text = ' '.join(text.split())
    # Escapar comillas dobles
    text = text.replace('"', '""')
    return text

def save_to_csv(articles, filename='noticias_20minutos.csv'):
    """Guarda los artículos en un archivo CSV con codificación UTF-8, usando ^ como delimitador"""
    if not articles:
        print("No hay artículos para guardar.")
        return
    
    # Crear directorio de salida si no existe
    os.makedirs('output', exist_ok=True)
    filepath = os.path.join('output', filename)
    
    # Definir el orden de las columnas que queremos
    default_columns = [
        'title', 'url', 'publish_date', 'authors', 
        'summary', 'text', 'keywords', 'images', 'html'
    ]
    
    # Obtener todas las claves únicas de todos los artículos
    all_columns = set()
    for article in articles:
        all_columns.update(article.keys())
    
    # Ordenar las columnas: primero las que están en default_columns (en ese orden), luego el resto
    ordered_columns = []
    for col in default_columns:
        if col in all_columns:
            ordered_columns.append(col)
            all_columns.remove(col)
    
    # Añadir el resto de columnas que no estaban en default_columns
    ordered_columns.extend(sorted(all_columns))
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            # Escribir encabezados
            f.write('^'.join(ordered_columns) + '\n')
            
            for article in articles:
                row = []
                for key in ordered_columns:
                    value = article.get(key, '')
                    
                    # Manejar diferentes tipos de datos
                    if isinstance(value, (list, tuple)):
                        # Unir listas con comas, limpiando cada elemento
                        value = ', '.join([clean_text(str(i)) for i in value])
                    elif value is None:
                        value = ''
                    else:
                        # Limpiar texto
                        value = clean_text(str(value))
                    
                    # Truncar el contenido HTML para evitar filas demasiado largas
                    if key == 'html' and len(value) > 1000:
                        value = value[:1000] + '... [TRUNCATED]'
                    
                    # Reemplazar saltos de línea y el delimitador ^
                    value = value.replace('\n', ' ').replace('\r', '').replace('^', ' ')
                    
                    # Asegurar que el valor sea una cadena
                    if not isinstance(value, str):
                        value = str(value)
                    
                    row.append(value)
                
                # Unir los campos con ^ y escribir la línea
                f.write('^'.join(row) + '\n')
        
        print(f"\n✅ Se han guardado {len(articles)} artículos en {filepath}")
        print(f"   Codificación: UTF-8")
        print(f"   Delimitador: ^")
        print(f"   Columnas: {'^'.join(ordered_columns[:3])}...")
        
    except Exception as e:
        print(f"❌ Error al guardar el archivo CSV: {str(e)}")
        import traceback
        traceback.print_exc()

def is_today(date_str, date_format='%Y-%m-%d %H:%M:%S%z'):
    """Verifica si una fecha es de hoy"""
    try:
        from datetime import datetime, timezone
        
        # Si no hay fecha, asumimos que es de hoy
        if not date_str:
            return False
            
        # Convertir la fecha del artículo a datetime
        article_date = datetime.strptime(date_str, date_format)
        
        # Obtener fecha actual con zona horaria
        now = datetime.now(timezone.utc).astimezone()
        
        # Comparar solo año, mes y día
        return (article_date.year == now.year and 
                article_date.month == now.month and 
                article_date.day == now.day)
    except Exception as e:
        print(f"Error al verificar fecha: {str(e)}")
        return False

def main():
    print("\nIniciando scraper de 20minutos...\n")
    
    parser = argparse.ArgumentParser(description='Scraper de noticias de 20minutos')
    parser.add_argument('--output', type=str, default='noticias_20minutos.csv', 
                       help='Nombre del archivo de salida (por defecto: noticias_20minutos.csv)')
    parser.add_argument('--days-back', type=int, default=0,
                       help='Número de días hacia atrás para buscar noticias (0 = hoy)')
    args = parser.parse_args()
    
    # URL del feed RSS de 20minutos
    feed_url = "https://www.20minutos.es/rss/"
    
    print(f"Procesando feed: 20Min home")
    xml_content = fetch_rss_feed(feed_url)
    if not xml_content:
        print("No se pudo obtener el feed RSS")
        return
    
    items = parse_rss(xml_content)
    print(f"Encontrados {len(items)} artículos en el feed")
    
    articles = []
    today_articles = 0
    
    for i, item in enumerate(items, 1):
        try:
            url = item['link']
            print(f"\nProcesando artículo {i}/{len(items)}: {item['title']}")
            
            article_data = get_article_data(url)
            
            if article_data:
                # Verificar si el artículo es de hoy
                if is_today(str(article_data.get('publish_date', ''))):
                    articles.append(article_data)
                    today_articles += 1
                    
                    # Mostrar información básica
                    print(f"    Título: {article_data.get('title', 'Sin título')}")
                    print(f"    URL: {url}")
                    print(f"    Fecha: {article_data.get('publish_date', 'No disponible')}")
                    print(f"    Autores: {', '.join(article_data.get('authors', ['Desconocido']))}")
                    print(f"    Resumen: {article_data.get('summary', 'Sin resumen')[:100]}...")
                else:
                    print(f"    Saltado: Artículo no es de hoy")
            
            # Pequeña pausa para no saturar el servidor
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    Error al procesar el artículo: {str(e)}")
            continue
    
    # Guardar a CSV
    if articles:
        print(f"\n✅ Se han encontrado {today_articles} artículos de hoy")
        save_to_csv(articles, args.output)
    else:
        print("\nNo se encontraron artículos de hoy para guardar.")

if __name__ == "__main__":
    main()
