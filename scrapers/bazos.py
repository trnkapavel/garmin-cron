import re
from datetime import datetime, timezone

import feedparser
import requests

BAZOS_RSS_URLS = {
    "bazos-mobil": "https://mobil.bazos.cz/rss.php?hledej={query}",
    "bazos-sport": "https://sport.bazos.cz/rss.php?hledej={query}",
}

PRICE_RE = re.compile(r"(\d[\d\s]{2,})\s*Kč", re.IGNORECASE)


def _extract_price(text):
    match = PRICE_RE.search(text)
    if not match:
        return None
    digits = match.group(1).replace(" ", "")
    return int(digits)


def _parse_entries(entries, source):
    listings = []
    for entry in entries:
        price = _extract_price(entry.title) or _extract_price(entry.get("description", ""))
        if price is None:
            continue
        listings.append({
            "title": entry.title,
            "price_czk": price,
            "url": entry.link,
            "source": source,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    return listings


def fetch_bazos(query):
    listings = []
    for source, url_template in BAZOS_RSS_URLS.items():
        url = url_template.format(query=query.replace(" ", "+"))
        response = requests.get(url, timeout=15)
        feed = feedparser.parse(response.content)
        listings.extend(_parse_entries(feed.entries, source))
    return listings
