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
