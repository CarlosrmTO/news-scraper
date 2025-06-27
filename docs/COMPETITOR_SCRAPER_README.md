# Competitor News Scraper

## Overview
This system scrapes news articles from competitor websites, extracts relevant metadata, and exports them to CSV files. The system is designed to be modular, allowing easy addition of new competitors.

## Features
- Extracts article metadata including title, URL, publish date, authors, and content
- Extracts section and subsection from article URLs
- Cleans and normalizes author information
- Handles various date formats and provides fallbacks
- Exports to CSV with proper encoding and field handling
- Robust error handling and logging

## Directory Structure
```
competitors/
├── base_scraper.py    # Base scraper class with common functionality
├── config/           # Configuration files for each competitor
├── export_competitors.py  # Main script to run the scrapers
└── output/           # Output directory for CSV files
```

## Configuration
Each competitor requires a JSON configuration file in the `competitors/config/` directory with the following structure:

```json
{
    "name": "Competitor Name",
    "url": "https://www.competitor.com",
    "sitemap": "https://www.competitor.com/sitemap.xml",
    "sitemap_type": "sitemap_index"  # Optional: "sitemap_index" or "sitemap"
}
```

## Usage

### Running a Specific Competitor
```bash
python -c "import export_competitors; exporter = export_competitors.CompetitorExporter(); exporter.process_competitor('CompetitorName')"
```

### Running All Competitors
```bash
python -c "import export_competitors; exporter = export_competitors.CompetitorExporter(); exporter.process_all_competitors()"
```

## Known Issues and Workarounds

### Sitemap Discovery
- Some competitors may not have standard sitemap locations
- The system tries common sitemap locations if the configured one fails
- For problematic sites, manual configuration of sitemap URL may be required

### Common Errors
1. **NoneType errors**: Usually indicates a missing or incorrect competitor name
2. **Sitemap parsing errors**: Some sites return HTML instead of XML for their sitemap
3. **Date parsing issues**: Fallback to current date is implemented

## Output Format
CSV files are saved in the `output/competitors/[competitor_name]/` directory with the following fields:
- title
- url
- publish_date
- authors (comma-separated)
- source
- domain
- summary
- section
- subsection

## Adding a New Competitor
1. Create a new JSON config file in `competitors/config/`
2. Add the competitor's name to the `COMPETITORS` list in `export_competitors.py`
3. Test the scraper with the new configuration

## Dependencies
- Python 3.8+
- newspaper3k
- beautifulsoup4
- requests
- lxml
- python-dateutil

## Logging
Logs are output to the console with timestamps and log levels. The log level can be adjusted in the code if needed.
