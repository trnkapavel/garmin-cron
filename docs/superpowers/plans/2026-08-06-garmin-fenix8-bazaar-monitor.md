# Garmin Fenix 8 51mm Bazaar Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that scrapes Bazoš (RSS) and Sbazar (HTML) daily for Garmin Fenix 8 51mm listings, computes discount vs. a reference retail price, and appends new listings to a CSV committed back to the repo via a GitHub Actions cron workflow.

**Architecture:** Two independent scraper modules (`scrapers/bazos.py`, `scrapers/sbazar.py`) each expose a `fetch_*(query)` function returning a list of normalized listing dicts. `main.py` orchestrates: load config → run scrapers (each isolated in try/except) → dedup against existing CSV by URL → compute discount → append new rows. A GitHub Actions workflow runs `main.py` daily and commits the updated CSV.

**Tech Stack:** Python 3.12, `feedparser` (Bazoš RSS), `requests` + `beautifulsoup4` (Sbazar HTML), `pyyaml` (config), `pytest` (tests), GitHub Actions (schedule trigger).

**Scope note:** Aukro is explicitly out of scope for this plan (no API key available yet). Adding it later is a follow-up plan — `main.py` is structured so a third `fetch_aukro` source can be added the same way as the other two without restructuring.

---

## Verified findings from live site inspection

- Bazoš RSS endpoint: `https://mobil.bazos.cz/rss.php?hledej=<query>` and `https://sport.bazos.cz/rss.php?hledej=<query>`, standard RSS 2.0 with `title`, `link`, `description`.
- Sbazar has no RSS/API. Confirmed via `https://www.sbazar.cz/opensearch.xml` that the real search URL template is `https://www.sbazar.cz/hledej/{searchTerms}` (path segment, not `?q=`) — verified by fetching `https://www.sbazar.cz/hledej/garmin fenix 8` and finding real listing links (`/inzerat/232306086-hodinky-garmin-fenix-8-47mm`, etc.).
- Sbazar listing cards in the returned HTML have this structure (verified from live fetch):
  ```html
  <ul data-test="offer-list">
    <li data-offer-id="232306086">
      <div class="relative @container group/card">
        <a href="/inzerat/232306086-hodinky-garmin-fenix-8-47mm">
          <div>
            <div class="... line-clamp-2 ...">Hodinky Garmin Fenix 8 47mm</div>
            <div class="line-clamp-1 ...">
              <b class="text-neutral-black flex-none">19 999 Kč</b>
              <span>v Brno, Žabovřesky </span>
            </div>
          </div>
        </a>
      </div>
    </li>
    ...
  </ul>
  ```
  Selector strategy: `ul[data-test="offer-list"] > li[data-offer-id]`, then within it `a[href^="/inzerat/"]`, title via `div.line-clamp-2`, price via the first `<b>` tag. These are Tailwind utility classes and may drift if Sbazar redesigns — the selectors live in one function (`_parse_listings`) so a future fix is a one-file change.

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.gitignore`
- Create: `scrapers/__init__.py`
- Create: `data/.gitkeep`

- [ ] **Step 1: Create `requirements.txt`**

```
feedparser==6.0.11
requests==2.32.3
beautifulsoup4==4.12.3
pyyaml==6.0.2
pytest==8.3.3
```

- [ ] **Step 2: Create `config.yaml`**

```yaml
reference_price_czk: 25990   # nová cena Fenix 8 51mm base (Alza) — upravit ručně při změně ceníku
search_terms:
  bazos: "fenix 8"
  sbazar: "garmin fenix 8"
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
```

- [ ] **Step 4: Create empty `scrapers/__init__.py`**

```python
```

- [ ] **Step 5: Create `data/.gitkeep`**

```
```

- [ ] **Step 6: Install dependencies locally**

Run: `pip install -r requirements.txt`
Expected: all packages install without error.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt config.yaml .gitignore scrapers/__init__.py data/.gitkeep
git commit -m "Scaffold project structure and config"
```

---

### Task 2: Bazoš RSS scraper

**Files:**
- Create: `scrapers/bazos.py`
- Test: `tests/fixtures/bazos_sample.xml`
- Test: `tests/test_bazos.py`

- [ ] **Step 1: Create the RSS test fixture**

Create `tests/fixtures/bazos_sample.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Bazos.cz</title>
<item>
<title>Garmin fenix 8 51mm Sapphire AMOLED - 18700 Kč</title>
<link>https://mobil.bazos.cz/inzerat/123456789/garmin-fenix-8-51mm.php</link>
<description>Prodam hodinky Garmin fenix 8 51mm, jako nove, plna vybava.</description>
<pubDate>Wed, 06 Aug 2026 10:00:00 +0200</pubDate>
</item>
<item>
<title>Reseni hledani bez ceny</title>
<link>https://mobil.bazos.cz/inzerat/999999999/jine.php</link>
<description>Napiste si o cenu</description>
<pubDate>Wed, 06 Aug 2026 09:00:00 +0200</pubDate>
</item>
</channel>
</rss>
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_bazos.py`:

```python
from pathlib import Path

import feedparser

from scrapers.bazos import _extract_price, _parse_entries

FIXTURE = Path(__file__).parent / "fixtures" / "bazos_sample.xml"


def test_extract_price_finds_kc_amount():
    assert _extract_price("Garmin fenix 8 51mm - 18700 Kč") == 18700


def test_extract_price_handles_spaced_thousands():
    assert _extract_price("Cena: 18 700 Kč") == 18700


def test_extract_price_returns_none_when_missing():
    assert _extract_price("Garmin fenix 8 51mm") is None


def test_parse_entries_extracts_listings_from_fixture():
    feed = feedparser.parse(str(FIXTURE))
    listings = _parse_entries(feed.entries, "bazos-mobil")

    assert len(listings) == 1
    assert listings[0]["title"] == "Garmin fenix 8 51mm Sapphire AMOLED - 18700 Kč"
    assert listings[0]["price_czk"] == 18700
    assert listings[0]["url"] == "https://mobil.bazos.cz/inzerat/123456789/garmin-fenix-8-51mm.php"
    assert listings[0]["source"] == "bazos-mobil"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_bazos.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.bazos'`

- [ ] **Step 4: Implement `scrapers/bazos.py`**

```python
import re
from datetime import datetime, timezone

import feedparser

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
        feed = feedparser.parse(url)
        listings.extend(_parse_entries(feed.entries, source))
    return listings
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_bazos.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add scrapers/bazos.py tests/test_bazos.py tests/fixtures/bazos_sample.xml
git commit -m "Add Bazos RSS scraper"
```

---

### Task 3: Sbazar HTML scraper

**Files:**
- Create: `scrapers/sbazar.py`
- Test: `tests/fixtures/sbazar_sample.html`
- Test: `tests/test_sbazar.py`

- [ ] **Step 1: Create the HTML test fixture**

Create `tests/fixtures/sbazar_sample.html`:

```html
<html>
<body>
<ul data-test="offer-list">
  <li data-offer-id="232306086">
    <div class="relative @container group/card">
      <a href="/inzerat/232306086-hodinky-garmin-fenix-8-47mm">
        <div>
          <div class="text-red line-clamp-2">Hodinky Garmin Fenix 8 47mm</div>
          <div class="line-clamp-1"><b class="text-neutral-black flex-none">19 999 Kč</b> <span>v Brno, Žabovřesky </span></div>
        </div>
      </a>
    </div>
  </li>
  <li data-offer-id="218253905">
    <div class="relative @container group/card">
      <a href="/inzerat/218253905-fenix-5x-6x-7x-8-tah-reminek-pasek-26mm">
        <div>
          <div class="text-red line-clamp-2">Tah řemínek pásek 26mm fenix 5x/6x/7x/8</div>
          <div class="line-clamp-1"><b class="text-neutral-black flex-none">299 Kč</b> <span>v Praha </span></div>
        </div>
      </a>
    </div>
  </li>
</ul>
</body>
</html>
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_sbazar.py`:

```python
from pathlib import Path

from scrapers.sbazar import _extract_price, _parse_listings

FIXTURE = Path(__file__).parent / "fixtures" / "sbazar_sample.html"


def test_extract_price_parses_spaced_amount():
    assert _extract_price("19 999 Kč") == 19999


def test_extract_price_returns_none_when_missing():
    assert _extract_price("Cena dohodou") is None


def test_parse_listings_extracts_cards_from_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    listings = _parse_listings(html)

    assert len(listings) == 2
    assert listings[0]["title"] == "Hodinky Garmin Fenix 8 47mm"
    assert listings[0]["price_czk"] == 19999
    assert listings[0]["url"] == "https://www.sbazar.cz/inzerat/232306086-hodinky-garmin-fenix-8-47mm"
    assert listings[0]["source"] == "sbazar"
    assert listings[1]["price_czk"] == 299
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_sbazar.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.sbazar'`

- [ ] **Step 4: Implement `scrapers/sbazar.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_sbazar.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add scrapers/sbazar.py tests/test_sbazar.py tests/fixtures/sbazar_sample.html
git commit -m "Add Sbazar HTML scraper"
```

---

### Task 4: Orchestration (`main.py`)

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main.py`:

```python
import csv

import main


def test_add_discount_computes_percentage():
    listing = {"price_czk": 18700}
    result = main.add_discount(listing, 25990)
    assert result["discount_pct"] == 28.0


def test_load_existing_urls_reads_csv(tmp_path, monkeypatch):
    csv_file = tmp_path / "listings.csv"
    csv_file.write_text(
        "url,title,price_czk,source,discount_pct,scraped_at\n"
        "http://a,Title,100,bazos-mobil,10,2026-01-01T00:00:00+00:00\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "CSV_PATH", csv_file)
    assert main.load_existing_urls() == {"http://a"}


def test_load_existing_urls_returns_empty_set_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CSV_PATH", tmp_path / "does_not_exist.csv")
    assert main.load_existing_urls() == set()


def test_collect_listings_merges_sources_and_survives_source_failure(monkeypatch):
    monkeypatch.setattr(main, "fetch_bazos", lambda q: [{"url": "http://bazos/1"}])

    def failing_sbazar(q):
        raise RuntimeError("network error")

    monkeypatch.setattr(main, "fetch_sbazar", failing_sbazar)

    config = {"search_terms": {"bazos": "fenix 8", "sbazar": "fenix 8"}}
    listings = main.collect_listings(config)

    assert listings == [{"url": "http://bazos/1"}]


def test_main_appends_only_new_listings_with_discount(tmp_path, monkeypatch):
    csv_file = tmp_path / "listings.csv"
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "reference_price_czk: 25990\n"
        "search_terms:\n"
        "  bazos: fenix 8\n"
        "  sbazar: fenix 8\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "CSV_PATH", csv_file)
    monkeypatch.setattr(main, "CONFIG_PATH", config_file)
    monkeypatch.setattr(
        main,
        "fetch_bazos",
        lambda q: [{
            "url": "http://bazos/1",
            "title": "Fenix 8",
            "price_czk": 18700,
            "source": "bazos-mobil",
            "scraped_at": "2026-01-01T00:00:00+00:00",
        }],
    )
    monkeypatch.setattr(main, "fetch_sbazar", lambda q: [])

    main.main()

    with open(csv_file, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["url"] == "http://bazos/1"
    assert rows[0]["discount_pct"] == "28.0"

    # Running again with the same listing should not duplicate the row.
    main.main()
    with open(csv_file, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement `main.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass (13 passed)

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "Add orchestration script with dedup and discount calculation"
```

---

### Task 5: GitHub Actions daily workflow

**Files:**
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/daily.yml`:

```yaml
name: Daily Garmin Fenix 8 scrape

on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest -v

      - name: Run scraper
        run: python main.py

      - name: Commit and push updated listings
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/listings.csv
          git diff --cached --quiet || git commit -m "Update listings $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "Add daily GitHub Actions scrape workflow"
```

---

### Task 6: Manual smoke test and remote push

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite one more time**

Run: `pytest -v`
Expected: all tests pass

- [ ] **Step 2: Run the real scraper once locally against live sites**

Run: `python main.py`
Expected: prints `Collected N listings, M new.` with N > 0, and `data/listings.csv` now contains real rows with plausible titles/prices/discount_pct values. Manually eyeball a few rows for sanity (e.g., no negative prices, discount_pct roughly in the -20%..80% range for genuine Fenix 8 listings).

- [ ] **Step 3: Commit the first real data snapshot**

```bash
git add data/listings.csv
git commit -m "Add initial listings snapshot from manual smoke test"
```

- [ ] **Step 4: Create the remote GitHub repo and push**

This step requires a GitHub account/remote decision from the user (repo name, public/private) — confirm before running:

```bash
gh repo create garmin-cron --source=. --private --push
```

Expected: repo created on GitHub, `main` branch pushed, and the "Daily Garmin Fenix 8 scrape" workflow visible under the Actions tab.

- [ ] **Step 5: Trigger one manual workflow run to verify it works end-to-end**

Run: `gh workflow run daily.yml`
Then check: `gh run watch`
Expected: workflow completes successfully (tests pass, scraper runs, commit pushed if new listings found).
