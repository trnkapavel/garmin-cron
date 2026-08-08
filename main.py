import csv
import sys
from pathlib import Path

import yaml

from scrapers.bazos import fetch_bazos
from scrapers.sbazar import fetch_sbazar

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
CSV_PATH = ROOT / "data" / "listings.csv"
CSV_FIELDS = ["url", "title", "price_czk", "source", "discount_pct", "scraped_at"]


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_existing_urls():
    if not CSV_PATH.exists():
        return set()
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {row["url"] for row in reader}


def collect_listings(config):
    listings = []
    try:
        listings.extend(fetch_bazos(config["search_terms"]["bazos"]))
    except Exception as e:
        print(f"[bazos] scrape failed: {e}", file=sys.stderr)
    try:
        listings.extend(fetch_sbazar(config["search_terms"]["sbazar"]))
    except Exception as e:
        print(f"[sbazar] scrape failed: {e}", file=sys.stderr)
    return listings


def add_discount(listing, reference_price):
    listing["discount_pct"] = round(
        (reference_price - listing["price_czk"]) / reference_price * 100, 1
    )
    return listing


def main():
    config = load_config()
    existing_urls = load_existing_urls()
    listings = collect_listings(config)
    new_listings = [l for l in listings if l["url"] not in existing_urls]
    reference_price = config["reference_price_czk"]
    new_rows = [add_discount(l, reference_price) for l in new_listings]

    file_exists = CSV_PATH.exists()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)

    print(f"Collected {len(listings)} listings, {len(new_rows)} new.")


if __name__ == "__main__":
    main()
