import requests
import scraper

HTML = """<article class="product_pod"><p class="star-rating Four"></p>
<h3><a href="a-book_1/index.html" title="A Book">A Bo...</a></h3>
<p class="price_color">£12.50</p><p class="availability"> In stock </p></article>
<article class="product_pod"><p class="star-rating Two"></p>
<h3><a href="b-book_2/index.html" title="B Book">B Bo...</a></h3>
<p class="price_color">£7.50</p><p class="availability"> Out of stock </p></article>
<article class="product_pod"><h3></h3></article>"""


def test_parse_books_skips_malformed():
    books = scraper.parse_books(HTML, "https://books.toscrape.com/catalogue/page-1.html")
    assert len(books) == 2
    assert books[0] == {"title": "A Book", "price_gbp": 12.5, "rating": 4, "in_stock": True,
                        "url": "https://books.toscrape.com/catalogue/a-book_1/index.html"}
    assert books[1]["in_stock"] is False


def test_report_and_csv(tmp_path):
    books = scraper.parse_books(HTML, "https://x.com/c/p.html")
    report = scraper.build_report(books)
    assert "Total books scraped : 2" in report and "£10.00" in report
    scraper.save_csv(books, tmp_path / "b.csv")
    assert (tmp_path / "b.csv").read_text().startswith("title,price_gbp")


def test_fetch_retries(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class S:
        def get(self, url, timeout):
            calls["n"] += 1
            raise requests.ConnectionError("boom")

    assert scraper.fetch(S(), "http://x", retries=3) is None
    assert calls["n"] == 3
