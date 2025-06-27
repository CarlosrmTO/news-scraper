# Sistema de Monitoreo de Competidores

Este directorio contiene el código para monitorear y exportar noticias de los principales competidores de 20minutos.

## Estructura del Proyecto

```
competitors/
├── config/           # Configuraciones de cada competidor
├── scrapers/         # Scrapers específicos por competidor
├── exporters/        # Exportadores específicos por competidor
└── utils/            # Utilidades compartidas
```

## Medios Integrados

- 20minutos
- El País
- El Mundo
- El Confidencial
- La Razón
- El Español
- OKDiario
- Público
- Libertad Digital
- eldiario.es
- Infobae
- Vozpópuli
- El Periódico

## Cómo Añadir un Nuevo Competidor

1. **Crear un archivo de configuración** en `config/`:
   ```python
   # Ejemplo: config/ejemplo.py
   CONFIG = {
       'name': 'Nombre del Medio',
       'base_url': 'https://www.ejemplo.com',
       'sitemaps': [
           'https://www.ejemplo.com/sitemap.xml',
       ],
       'scraper': 'scrapers.ejemplo_scraper',
       'exporter': 'exporters.ejemplo_exporter',
       'enabled': True
   }
   ```

2. **Implementar el scraper** en `scrapers/`:
   ```python
   # scrapers/ejemplo_scraper.py
   def get_articles(competitor_config=None, days_back=1):
       # Lógica para obtener artículos
       return articles_list
   ```

3. **Implementar el exportador** en `exporters/` (opcional):
   ```python
   # exporters/ejemplo_exporter.py
   def export_articles(articles, output_file):
       # Lógica de exportación personalizada
       pass
   ```

4. **Probar la integración**:
   ```bash
   python export_competitors.py --competitors "Nombre del Medio" --days-back 1 --debug
   ```

## Ejecución

### Exportar todos los competidores habilitados:
```bash
python export_competitors.py --days-back 1
```

### Exportar competidores específicos:
```bash
python export_competitors.py --competitors "El País" "El Mundo" --days-back 2
```

### Opciones disponibles:
- `--competitors`: Nombres de los competidores a exportar (entre comillas, separados por espacios)
- `--days-back`: Número de días hacia atrás para filtrar artículos (por defecto: 1)
- `--max-articles`: Número máximo de artículos a exportar por competidor (opcional)
- `--debug`: Mostrar mensajes de depuración

## Formato de Salida

Los archivos de salida se guardan en `output/competitors/[nombre_medio]/` con el siguiente formato:
- Nombre: `[nombre_medio]_articles_YYYYMMDD.csv`
- Codificación: UTF-8
- Delimitador: `^` (circunflejo)
- Campos: `title^url^publish_date^authors^source^domain^summary^section^subsection^text`

## Integración de 20minutos

El módulo de 20minutos utiliza un enfoque especial:
- **Scraper**: `scrapers/veinte_minutos_scraper.py`
- **Configuración**: `config/veinte_minutos.py`
- **Características**:
  - Utiliza el feed RSS de 20minutos
  - Filtra artículos por fecha
  - Extrae metadatos completos
  - Maneja múltiples formatos de fecha

Para ejecutar solo 20minutos:
```bash
python export_competitors.py --competitors "20minutos" --days-back 1
```

## Registro de Actividad

Los registros se guardan en `export_competitors.log` con el siguiente formato:
```
[FECHA HORA] - NIVEL - MENSAJE
```

## Notas de Implementación

- Los scrapers deben ser independientes entre sí
- Cada competidor puede tener su propia lógica de extracción
- Los exportadores personalizados son opcionales
- El sistema maneja automáticamente la creación de directorios
- Los errores se registran y no detienen la ejecución de otros competidores
