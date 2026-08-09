import csv
import html
import sys
from pathlib import Path

import yaml

from scrapers.bazos import fetch_bazos
from scrapers.sbazar import fetch_sbazar

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
CSV_PATH = ROOT / "data" / "listings.csv"
HTML_PATH = ROOT / "docs" / "index.html"
CSV_FIELDS = ["url", "title", "price_czk", "source", "discount_pct", "scraped_at"]

HTML_TEMPLATE = """<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<title>Garmin Fenix 8 51mm — bazarové nabídky</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>Garmin Fenix 8 51mm — bazarové nabídky</h1>
<table>
<tr><th>Název</th><th>Cena (Kč)</th><th>Sleva</th><th>Zdroj</th><th>Nalezeno</th></tr>
{rows}
</table>
</body>
</html>
"""


def generate_html():
    if not CSV_PATH.exists():
        return
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["scraped_at"], reverse=True)

    row_html = "\n".join(
        "<tr><td><a href=\"{url}\">{title}</a></td><td>{price}</td>"
        "<td>{discount}%</td><td>{source}</td><td>{scraped_at}</td></tr>".format(
            url=html.escape(r["url"]),
            title=html.escape(r["title"]),
            price=html.escape(r["price_czk"]),
            discount=html.escape(r["discount_pct"]),
            source=html.escape(r["source"]),
            scraped_at=html.escape(r["scraped_at"]),
        )
        for r in rows
    )

    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.format(rows=row_html))


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

    generate_html()

    print(f"Collected {len(listings)} listings, {len(new_rows)} new.")


if __name__ == "__main__":
    main()
