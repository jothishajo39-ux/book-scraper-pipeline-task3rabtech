# Book Scraper Pipeline (ETL)

Scrapes book data from https://books.toscrape.com (a sandbox site built for scraping practice)
using Requests + BeautifulSoup.

**Features:** rate limiting, custom headers, retry with exponential backoff,
HTML -> structured CSV/JSON, automatic summary statistics report.

## Run
    pip install -r requirements.txt
    python scraper.py --pages 5 --delay 1.5

**Outputs:** `books.csv`, `books.json`, `report.txt`

## Test
    pip install pytest
    pytest
