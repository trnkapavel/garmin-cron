import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.sbazar.cz"
SEARCH_URL = BASE_URL + "/hledej/{query}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

PRICE_RE = re.compile(r"([\d\s\xa0]+)\s*Kč")


def _extract_price(text):
    match = PRICE_RE.search(text)
    if not match:
        return None
    digits = match.group(1).replace(" ", "").replace("\xa0", "")
    if not digits.isdigit():
        return None
    return int(digits)


def _parse_listings(html):
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    for li in soup.select('ul[data-test="offer-list"] > li[data-offer-id]'):
        link = li.select_one('a[href^="/inzerat/"]')
        if link is None:
            continue
        title_el = link.select_one("div.line-clamp-2")
        price_el = link.select_one("b")
        if title_el is None or price_el is None:
            continue
        price = _extract_price(price_el.get_text())
        if price is None:
            continue
        listings.append({
            "title": title_el.get_text(strip=True),
            "price_czk": price,
            "url": BASE_URL + link["href"],
            "source": "sbazar",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    return listings


def fetch_sbazar(query):
    url = SEARCH_URL.format(query=query.replace(" ", "%20"))
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return _parse_listings(response.text)
