"""Automated ETL web scraper: books.toscrape.com -> CSV/JSON + summary report."""
import argparse
import csv
import json
import logging
import statistics
import time
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RabTechScraper/1.0; student project)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
FIELDS = ["title", "price_gbp", "rating", "in_stock", "url"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scraper")


# ---------- EXTRACT ----------
def fetch(session, url, retries=3, delay=1.5, timeout=10):
    """GET with rate limiting, custom headers and exponential-backoff retries."""
    for attempt in range(1, retries + 1):
        try:
            time.sleep(delay)  # rate limit: polite pause before every request
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 404:
                return None  # no more pages
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:
            wait = 2 ** attempt
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt == retries:
                log.error("Giving up on %s", url)
                return None
            time.sleep(wait)


# ---------- TRANSFORM ----------
def parse_books(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for card in soup.select("article.product_pod"):
        try:
            link = card.h3.a
            price = float(card.select_one("p.price_color").text.replace("£", "").replace("Â", "").strip())
            rating_word = card.select_one("p.star-rating")["class"][1]
            books.append({
                "title": link["title"],
                "price_gbp": price,
                "rating": RATINGS.get(rating_word, 0),
                "in_stock": "in stock" in card.select_one("p.availability").text.lower(),
                "url": urljoin(page_url, link["href"]),
            })
        except (AttributeError, KeyError, ValueError, IndexError) as exc:
            log.warning("Skipping malformed product: %s", exc)
    return books


# ---------- LOAD ----------
def save_csv(books, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(books)


def save_json(books, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)


# ---------- REPORT ----------
def build_report(books):
    if not books:
        return "No data scraped."
    prices = [b["price_gbp"] for b in books]
    ratings = Counter(b["rating"] for b in books)
    in_stock = sum(b["in_stock"] for b in books)
    cheapest = min(books, key=lambda b: b["price_gbp"])
    priciest = max(books, key=lambda b: b["price_gbp"])
    lines = [
        "=== SCRAPING SUMMARY REPORT ===",
        f"Total books scraped : {len(books)}",
        f"In stock            : {in_stock} ({in_stock / len(books):.0%})",
        f"Average price       : £{statistics.mean(prices):.2f}",
        f"Median price        : £{statistics.median(prices):.2f}",
        f"Cheapest            : £{cheapest['price_gbp']:.2f} - {cheapest['title']}",
        f"Most expensive      : £{priciest['price_gbp']:.2f} - {priciest['title']}",
        "Rating distribution :",
    ]
    lines += [f"  {s} star : {ratings.get(s, 0)}" for s in range(5, 0, -1)]
    return "\n".join(lines)


def run(pages, delay):
    session = requests.Session()
    session.headers.update(HEADERS)
    all_books = []
    for n in range(1, pages + 1):
        url = BASE_URL.format(n)
        log.info("Scraping page %d: %s", n, url)
        html = fetch(session, url, delay=delay)
        if html is None:
            break
        all_books.extend(parse_books(html, url))
    return all_books


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=5, help="pages to scrape (20 books/page, max 50)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    args = ap.parse_args()

    books = run(args.pages, args.delay)
    save_csv(books, "books.csv")
    save_json(books, "books.json")
    report = build_report(books)
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
