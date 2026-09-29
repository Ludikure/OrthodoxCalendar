#!/usr/bin/env python3
"""
Reference fasting levels for the Russian and English calendars, read from the
source each locale follows — the counterpart of scripts/serbian/pravoslavno_levels.py.

  ru     days.pravoslavie.ru, the Russian Church's calendar (Sretensky Monastery)
  en     holytrinityorthodox.com (ROCOR), the source of the English Old Calendar's saints
  en_nc  orthocal.info, the OCA's calendar, on the Revised Julian calendar

  python3 scripts/shared/reference_fasting.py fetch ru 2024 2026   refill a raw cache
  python3 scripts/shared/reference_fasting.py fixtures             write the committed fixtures

The raw caches under data/raw/ are gitignored; the fixtures they produce
(data/processed/ru/pravoslavie_fasting.json, data/processed/en/htc_fasting.json,
data/processed/en/orthocal_fasting.json) are committed, so CI can check the
engine against them without scraping anything.
"""
import glob, json, os, re, sys, time, urllib.request
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, HERE)
import fasting_engine as fe  # noqa: E402

RAW = {"ru": os.path.join(ROOT, "data", "raw", "ru"), "en": os.path.join(ROOT, "data", "raw", "en"),
       "en_nc": os.path.join(ROOT, "data", "raw", "en", "orthocal")}
FIXTURE = {"ru": os.path.join(ROOT, "data", "processed", "ru", "pravoslavie_fasting.json"),
           "en": os.path.join(ROOT, "data", "processed", "en", "htc_fasting.json"),
           "en_nc": os.path.join(ROOT, "data", "processed", "en", "orthocal_fasting.json")}
SOURCE = {"ru": "days.pravoslavie.ru", "en": "holytrinityorthodox.com", "en_nc": "orthocal.info (gregorian)"}


# ── Levels ──

def _ru(entry):
    # The site writes "cухоядение" with a Latin c on some days.
    t = (entry.get("description") or "").lower().replace("c", "с")
    if re.search(r"воздержание от пищи|без пищи|полное воздержание", t): return fe.TOTAL_ABSTINENCE
    if "сухоядение" in t: return fe.DRY_EATING
    if "без масла" in t: return fe.HOT_NO_OIL
    if "икра" in t: return fe.FISH_ROE
    if "рыб" in t: return fe.FISH
    if "масл" in t: return fe.HOT_WITH_OIL
    if not t.strip():
        return None       # no diet line: only ever on Great Saturday, which is no free day
    if re.search(r"поста нет|пост отменяется|сплошная|нет поста|всякая пища", t): return fe.FREE
    if "мяс" in t: return fe.FISH     # Cheese Week: meat excluded; the engine's nearest level
    return None


_HTC = [("Full abstention from food", fe.TOTAL_ABSTINENCE), ("Strict Fast", fe.DRY_EATING),
        ("Food without Oil", fe.HOT_NO_OIL), ("Food with Oil", fe.HOT_WITH_OIL),
        ("Caviar Allowed", fe.FISH_ROE), ("Fish Allowed", fe.FISH), ("Meat is excluded", fe.FISH),
        ("Fast-free", fe.FREE)]


def _en(entry):
    f = (entry.get("fast") or "").strip()
    if not f:
        return fe.FREE            # no fasting line: an ordinary day
    return next((lvl for text, lvl in _HTC if text in f), None)   # "Eve of the … Fast." notes: unknown


def _en_nc(entry):
    # The OCA marks a strict day without saying whether food is cooked, so "strict"
    # is hot food without oil here and counts as agreeing with anything stricter.
    ex = (entry.get("exception") or "").lower()
    if entry.get("fast") == "No Fast" or "fast free" in ex: return fe.FREE
    if "roe" in ex: return fe.FISH_ROE
    if "fish" in ex or "dairy" in ex or "meat fast" in ex: return fe.FISH
    if "oil" in ex and "strict" not in ex: return fe.HOT_WITH_OIL
    if "wine" in ex and "strict" not in ex: return fe.HOT_NO_OIL
    return fe.HOT_NO_OIL


LEVEL = {"ru": _ru, "en": _en, "en_nc": _en_nc}


def level(locale, entry):
    return LEVEL[locale](entry)


def agrees(locale, want, got):
    """Whether the engine's level matches the reference's."""
    if got == want:
        return True
    return locale == "en_nc" and want == fe.HOT_NO_OIL and got in (fe.DRY_EATING, fe.TOTAL_ABSTINENCE)


def load(locale):
    with open(FIXTURE[locale], encoding="utf-8") as f:
        return json.load(f)["days"]


# ── Fixtures from the raw caches ──

def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def _ru_days():
    out = {}
    for p in sorted(glob.glob(os.path.join(RAW["ru"], "pravoslavie_fast_*.html"))):
        d = re.search(r"(\d{4}-\d\d-\d\d)", p).group(1)
        html = open(p, encoding="utf-8").read()
        desc = re.search(r"DD_TPTXT[^>]*>(.*?)</SPAN>", html)
        per = re.search(r"DD_POST[^>]*>(.*?)</SPAN>", html)
        out[d] = {"description": _text(desc.group(1)) if desc else "", "period": _text(per.group(1)) if per else ""}
    return out


def _en_days():
    sys.path.insert(0, os.path.join(ROOT, "scripts", "english"))
    import scrape_holytrinityorthodox as h
    by_year = {}
    for p in glob.glob(os.path.join(RAW["en"], "htc_*.html")):
        y, m, d = re.search(r"htc_(\d{4})_(\d\d)_(\d\d)", p).groups()
        by_year.setdefault(y, {})[f"{y}-{m}-{d}"] = {"fast": (h.parse_fasting(open(p, errors="replace").read()) or "").strip()}
    out = {}
    for y, days in by_year.items():
        if len(days) >= 365:      # whole years only; the window fetches for the synaxes are not
            out.update(days)
    return out


def _en_nc_days():
    out = {}
    for p in glob.glob(os.path.join(RAW["en_nc"], "gregorian_*.json")):
        for e in json.load(open(p)):
            d = date.fromordinal(e["julian_day_number"] - 1721425)
            out[d.isoformat()] = {"fast": e.get("fast_level_desc") or "", "exception": e.get("fast_exception_desc") or ""}
    return out


def fixtures():
    for locale, days in (("ru", _ru_days()), ("en", _en_days()), ("en_nc", _en_nc_days())):
        unknown = sum(1 for e in days.values() if level(locale, e) is None)
        years = sorted({k[:4] for k in days})
        with open(FIXTURE[locale], "w", encoding="utf-8") as f:
            json.dump({"source": SOURCE[locale], "days": dict(sorted(days.items()))}, f,
                      ensure_ascii=False, indent=0, separators=(",", ":"))
        print(f"{locale}: {len(days)} days, {years[0]}-{years[-1]}, {unknown} without a level -> {FIXTURE[locale]}")


# ── Fetching ──

def fetch(locale, first, last):
    if locale == "ru":
        sys.path.insert(0, os.path.join(ROOT, "scripts", "russian"))
        import scrape_azbyka as s
        d = date(first, 1, 1)
        while d.year <= last:
            s.fetch_pravoslavie_fasting(d); d += timedelta(1)
    elif locale == "en":
        sys.path.insert(0, os.path.join(ROOT, "scripts", "english"))
        import scrape_holytrinityorthodox as h
        d = date(first, 1, 1)
        while d.year <= last:
            h.fetch_day(d.year, d.month, d.day); d += timedelta(1)
    else:
        os.makedirs(RAW["en_nc"], exist_ok=True)
        for y in range(first, last + 1):
            for m in range(1, 13):
                p = os.path.join(RAW["en_nc"], f"gregorian_{y}_{m:02d}.json")
                if os.path.exists(p):
                    continue
                req = urllib.request.Request(f"https://orthocal.info/api/gregorian/{y}/{m}/",
                                             headers={"User-Agent": "OrthodoxCalendar-data"})
                data = urllib.request.urlopen(req, timeout=30).read()
                json.loads(data)
                open(p, "wb").write(data)
                time.sleep(0.3)


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1:2] == ["fixtures"]:
        fixtures()
    else:
        print(__doc__)
