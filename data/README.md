# data/

| Directory | In git | What it is |
|---|---|---|
| `raw/` | no | Scraped source pages: crkvenikalendar day pages (sr), azbyka day + saint pages (ru), holytrinityorthodox day + life pages and orthocal day JSON (en). ~573 MB. |
| `processed/` | **yes** | Pipeline **input**: `saints.json`, `readings.json`, `saint_bios.json` per locale, plus `shared/feast_descriptions.json` and the `.sql` lectionaries. Because `raw/` is not in git, this is the only committed record of the scrape — do not delete it. |
| `output/` | no | Pipeline **output**: `calendar_{locale}_{year}.json`. Regenerate with `python3 scripts/shared/build_database.py`. |
| `archive_v2/` | no | Scratch space for the full 2024–2099 archive and the pools of the currently released app (`shipped_pools/`), used by `upload_r2_v2.py`. |

## Restoring `raw/`

It is not in git and is not hosted anywhere. Refill it with:

```bash
python3 scripts/shared/fetch_bio_sources.py          # orthocal JSON + azbyka saint pages
python3 scripts/english/build_saint_bios.py --fetch  # holytrinityorthodox life pages
```

The Serbian crkvenikalendar pages under `raw/sr/crkvenikalendar/` have no
fetcher in-repo; keep a copy. `scripts/serbian/audit_saint_bios.py` verifies
every stored Serbian bio still matches that cache and exits non-zero otherwise,
so a lost cache is detectable but not recoverable from here.
