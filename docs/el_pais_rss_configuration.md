# El País RSS Feed Configuration

This document outlines the configuration and usage of the El País RSS feed scraper.

## Overview

The El País scraper uses RSS feeds to collect articles from various sections of the El País website. This approach was chosen because:
1. It's more reliable than web scraping
2. It provides structured data
3. It's less likely to be blocked than direct web scraping

## Configuration

The main configuration is located in:
```
competitors/config/el_pais.py
```

### Current Feed Configuration

#### Main Feeds
- `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada` - Main feed
- `https://elpais.com/rss/elpais/portada.xml` - Alternative main feed
- `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/ultimas_noticias` - Latest news

#### News Sections
- `https://elpais.com/rss/elpais/espana.xml` - Spain news
- `https://elpais.com/rss/elpais/internacional.xml` - International news
- `https://elpais.com/rss/elpais/america.xml` - Americas news
- `https://elpais.com/rss/elpais/europa.xml` - Europe news

#### Topics
- `https://elpais.com/rss/elpais/economia.xml` - Economy
- `https://elpais.com/rss/elpais/tecnologia.xml` - Technology
- `https://elpais.com/rss/elpais/cultura.xml` - Culture
- `https://elpais.com/rss/elpais/deportes.xml` - Sports
- `https://elpais.com/rss/elpais/ciencia.xml` - Science
- `https://elpais.com/rss/elpais/gente.xml` - People
- `https://elpais.com/rss/elpais/opinion.xml` - Opinion

#### Special Sections
- `https://elpais.com/rss/elpais/eps.xml` - EPS magazine
- `https://elpais.com/rss/elpais/icon.xml` - ICON design
- `https://elpais.com/rss/elpais/elviajero.xml` - Travel
- `https://elpais.com/rss/elpais/babelia.xml` - Culture & Books

## Usage

### Running the Scraper

To run the El País scraper:

```bash
python test_el_pais_scraper.py
```

### Output

Articles are exported to:
```
output/competitors/el_país/el_país_articles_YYYYMMDD.csv
```

### Configuration Options

- `max_articles_per_feed`: Maximum number of articles to fetch per feed (default: 50)
- `request_delay`: Delay between requests in seconds (default: 1)
- `timeout`: Request timeout in seconds (default: 15)
- `retry_attempts`: Number of retry attempts for failed requests (default: 3)

## Troubleshooting

### Common Issues

1. **404 Errors**: Some feeds may return 404 errors. These are automatically handled and logged.
2. **Rate Limiting**: If you encounter rate limiting, increase the `request_delay`.
3. **Empty Results**: Some feeds may be temporarily unavailable. The scraper will log these cases.

### Logs

Logs are written to:
- Console output
- `test_el_pais_scraper.log`

## Maintenance

### Adding New Feeds

1. Verify the feed URL works in a browser
2. Add the URL to the appropriate section in `el_pais.py`
3. Test the scraper

### Updating Feeds

1. Check for new feed URLs on the El País website
2. Update the configuration file
3. Test the scraper

## Notes

- The scraper automatically handles duplicate articles
- Article data includes title, URL, publication date, authors, and section
- The export format is CSV with UTF-8 encoding
