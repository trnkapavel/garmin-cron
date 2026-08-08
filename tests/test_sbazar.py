from pathlib import Path

from scrapers.sbazar import HEADERS, _extract_price, _parse_listings, fetch_sbazar

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


def test_fetch_sbazar_requests_search_url_with_timeout(monkeypatch):
    captured = {}

    class FakeResponse:
        text = FIXTURE.read_text(encoding="utf-8")

        def raise_for_status(self):
            pass

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("scrapers.sbazar.requests.get", fake_get)

    listings = fetch_sbazar("fenix 8")

    assert captured["url"] == "https://www.sbazar.cz/hledej/fenix%208"
    assert captured["headers"] == HEADERS
    assert captured["timeout"] == 15
    assert len(listings) == 2
