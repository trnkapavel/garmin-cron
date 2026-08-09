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
    monkeypatch.setattr(main, "HTML_PATH", tmp_path / "index.html")
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


def test_generate_html_writes_clickable_links(tmp_path, monkeypatch):
    csv_file = tmp_path / "listings.csv"
    csv_file.write_text(
        "url,title,price_czk,source,discount_pct,scraped_at\n"
        'http://a,"Fenix 8 <great>",18700,bazos,28.0,2026-01-01T00:00:00+00:00\n',
        encoding="utf-8",
    )
    html_file = tmp_path / "index.html"
    monkeypatch.setattr(main, "CSV_PATH", csv_file)
    monkeypatch.setattr(main, "HTML_PATH", html_file)

    main.generate_html()

    content = html_file.read_text(encoding="utf-8")
    assert '<a href="http://a">Fenix 8 &lt;great&gt;</a>' in content
