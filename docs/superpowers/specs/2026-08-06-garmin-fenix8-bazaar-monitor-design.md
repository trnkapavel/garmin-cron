# Garmin Fenix 8 51mm — denní monitoring bazarových nabídek

## Cíl

Denně automaticky posbírat bazarové nabídky Garmin Fenix 8 51mm z Bazoše, Aukra
a Sbazaru, uložit je do CSV a u každé nabídky dopočítat procentuální slevu
vůči referenční nové ceně. Bez notifikací — uživatel si CSV prohlíží ručně.

## Zdroje dat

| Zdroj  | Metoda           | Poznámka                                                        |
|--------|-------------------|------------------------------------------------------------------|
| Bazoš  | RSS feed          | `mobil.bazos.cz` + `sport.bazos.cz`, oba prohledat zvlášť        |
| Aukro  | REST API          | Vyžaduje API klíč (registrace na aukro.cz/vyvojari), uložen jako GitHub Secret |
| Sbazar | HTML parsing      | Žádné RSS/API — parsuje se výpis výsledků hledání (requests + BeautifulSoup) |

Facebook Marketplace je záměrně vynechán (vyžaduje přihlášené session cookies,
je proti ToS, nestabilní vůči změnám stránky).

## Architektura

```
garmin-cron/
├── config.yaml                  # referenční cena, hledané výrazy
├── scrapers/
│   ├── bazos.py                  # parsování RSS
│   ├── aukro.py                  # volání Aukro API
│   └── sbazar.py                 # HTML parsing výpisu
├── main.py                       # orchestrace: fetch → normalize → dedup → zápis
├── data/listings.csv              # perzistentní úložiště, commitované zpět do repa
├── .github/workflows/daily.yml    # GitHub Actions cron, denní spuštění
├── tests/
│   ├── fixtures/                  # uložené ukázkové HTML/RSS soubory
│   └── test_scrapers.py
└── requirements.txt
```

## Data flow

1. GitHub Actions cron trigger spustí `main.py` (checkout repa přes `actions/checkout`).
2. Každý scraper (`bazos.py`, `aukro.py`, `sbazar.py`) vrátí seznam nabídek ve
   sjednoceném formátu: `{title, price_czk, url, source, scraped_at}`.
3. `main.py` sloučí výsledky ze všech zdrojů.
4. Dedup proti stávajícímu `data/listings.csv` podle `url` — nové řádky se
   přidají, existující se nemění (cena se nepřepisuje, i kdyby se v bazaru
   změnila — historie zůstává jako první zaznamenaná cena).
5. U nových řádků se dopočítá `discount_pct = (reference_price_czk - price_czk) / reference_price_czk * 100`.
6. Nové řádky se appendnou do `data/listings.csv`.
7. Workflow commitne a pushne aktualizovaný CSV zpět do repa (pokud přibyly řádky).

## Konfigurace (`config.yaml`)

```yaml
reference_price_czk: 25990   # nová cena Fenix 8 51mm base (Alza) — upravit ručně při změně ceníku
search_terms:
  bazos: "fenix 8"
  aukro: "garmin fenix 8"
  sbazar: "garmin fenix 8"
```

Jedna referenční cena platí pro všechny 51mm varianty (base/Solar/Pro) —
zjednodušení, uživatel si rozdíl mezi variantami vyhodnotí sám při pohledu
na název inzerátu v CSV.

## CSV formát (`data/listings.csv`)

```
url,title,price_czk,source,discount_pct,scraped_at
```

`url` slouží jako unikátní klíč pro dedup.

## Chybová odolnost

Každý scraper běží v `try/except` nezávisle na ostatních. Selhání jednoho
zdroje (timeout, změna HTML struktury, výpadek API) se zaloguje do výstupu
GitHub Actions, ale neshodí celý workflow — ostatní zdroje proběhnou dál.
Pokud všechny zdroje vrátí nula výsledků, workflow doběhne bez commitu (žádné
nové řádky k zapsání).

## Testování

- Unit testy parsovacích funkcí (`tests/test_scrapers.py`) na uložených
  ukázkových HTML/RSS fixture souborech — žádné živé síťové volání v testech.
- Jeden manuální smoke-test běhu `main.py` lokálně (proti živým zdrojům) před
  nasazením workflow do GitHub Actions.

## Závislosti / otevřené body

- **Aukro API klíč**: je potřeba zaregistrovat na aukro.cz/vyvojari a uložit
  jako GitHub Secret (`AUKRO_API_KEY`). Bez klíče nepůjde Aukro scraper
  spustit — lze nasadit nejdřív jen s Bazoš + Sbazar a Aukro doplnit později.
- **Referenční cena**: nastavena na 25 990 Kč (Alza, Fenix 8 51mm base) podle
  informace z konverzace — uživatel by měl ověřit/aktualizovat při změně
  ceníku.
