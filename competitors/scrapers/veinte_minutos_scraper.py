"""
Wrapper for the 20minutos scraper to integrate with the modular system.
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add the parent directory to the path to import the scraper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scraper_20minutos_simple import (
    fetch_rss_feed, parse_rss, get_article_data, 
    is_today, clean_author_name, extract_authors
)

def get_articles(competitor_config=None, days_back: int = 1) -> List[Dict[str, Any]]:
    """
    Get articles from 20minutos by directly using the functions from the original script.
    
    Args:
        competitor_config: Configuration dictionary for the competitor
        days_back: Number of days to look back for articles
        
    Returns:
        List of article dictionaries with metadata
    """
    print("\nIniciando scraper de 20minutos...\n")
    
    # URL del feed RSS de 20minutos
    feed_url = "https://www.20minutos.es/rss/"
    
    print(f"Procesando feed: 20Min home")
    xml_content = fetch_rss_feed(feed_url)
    if not xml_content:
        print("No se pudo obtener el feed RSS")
        return []
    
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
                # Verificar si el artículo es de hoy o dentro del rango de días
                    
                # Convertir el formato de fecha si es necesario
                publish_date = article_data.get('publish_date', '')
                if publish_date:
                    try:
                        # Intentar parsear la fecha
                        dt = None
                        if isinstance(publish_date, str):
                            # Formato: '2025-06-27 12:00:00+02:00'
                            try:
                                dt = datetime.strptime(publish_date, '%Y-%m-%d %H:%M:%S%z')
                            except ValueError:
                                # Intentar otro formato si el primero falla
                                dt = datetime.strptime(publish_date, '%Y-%m-%d')
                        else:
                            # Asumir que ya es un objeto datetime
                            dt = publish_date
                        
                        # Verificar si está dentro del rango de días
                        days_diff = (datetime.now(dt.tzinfo) - dt).days
                        if days_diff <= days_back:
                            articles.append(article_data)
                            today_articles += 1
                            
                            # Mostrar información básica
                            print(f"    Título: {article_data.get('title', 'Sin título')}")
                            print(f"    URL: {url}")
                            print(f"    Fecha: {publish_date}")
                            print(f"    Autores: {', '.join(article_data.get('authors', ['Desconocido']))}")
                            print(f"    Resumen: {article_data.get('summary', 'Sin resumen')[:100]}...")
                        else:
                            print(f"    Saltado: Artículo fuera del rango de fechas ({days_diff} días)")
                    except Exception as e:
                        print(f"    Error al procesar fecha {publish_date}: {str(e)}")
                        # Si hay error, lo incluimos por si acaso
                        articles.append(article_data)
                else:
                    # Si no hay fecha, lo incluimos por si acaso
                    articles.append(article_data)
            
            # Pequeña pausa para no saturar el servidor
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    Error al procesar el artículo: {str(e)}")
            continue
    
    print(f"\n✅ Se han encontrado {len(articles)} artículos en total")
    
    # Convertir al formato esperado por el exportador
    formatted_articles = []
    for article in articles:
        formatted_articles.append({
            'url': article.get('url', ''),
            'title': article.get('title', ''),
            'date': article.get('publish_date', ''),
            'section': article.get('section', ''),
            'authors': article.get('authors', []),
            'summary': article.get('summary', ''),
            'text': article.get('text', '')
        })
    
    return formatted_articles
