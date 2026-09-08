#!/usr/bin/env python3
"""Download the source pages the saint-bio builders read out of data/raw/.

  en   orthocal.info day JSON      -> data/raw/en/orthocal_YYYY-MM-DD.json
  ru   azbyka.ru day pages         -> data/raw/ru/azbyka_YYYY-MM-DD.html
       plus the saint pages they link -> data/raw/ru/saint_<slug>.html

Nothing is parsed or written to data/processed/ here — the pools are built by
english/build_saint_bios.py and russian/extract_azbyka_bios.py from this cache,
and each owns its own output file. (The Serbian pool comes from the
crkvenikalendar.com pages under data/raw/sr/crkvenikalendar/, and the
holytrinityorthodox lives from `build_saint_bios.py --fetch`.)

Already-cached files are left alone, so a re-run only fills gaps.

Usage:
    python3 scripts/shared/fetch_bio_sources.py [--locale en|ru] [--year 2026]
"""
import argparse
import importlib.util
import os
import sys
import time
import urllib.request
from datetime import date, timedelta

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
HEADERS = {"User-Agent": "OrthodoxCalendarApp/1.0"}
DELAY = 1.0   # be gentle with the sources


def fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def cache(url: str, path: str) -> str:
    """Contents of a cached page, downloading it the first time."""
    if os.path.exists(path):
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    print(f"  fetching {url}", file=sys.stderr)
    text = fetch_url(url)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    time.sleep(DELAY)
    return text


def days(year: int):
    cur = date(year, 1, 1)
    while cur.year == year:
        yield cur
        cur += timedelta(days=1)


def fetch_orthocal(year: int) -> None:
    """Day JSON from orthocal.info, keyed by church (Julian) date in the file."""
    raw = os.path.join(BASE_DIR, 'data', 'raw', 'en')
    print(f"=== English: orthocal.info ({year}) ===", file=sys.stderr)
    for cur in days(year):
        url = f"https://orthocal.info/api/gregorian/{cur.year}/{cur.month}/{cur.day}/"
        path = os.path.join(raw, f"orthocal_{cur:%Y-%m-%d}.json")
        try:
            cache(url, path)
        except Exception as e:
            print(f"  ERROR {cur:%m-%d}: {e}", file=sys.stderr)


def fetch_azbyka(year: int) -> None:
    """Day pages from azbyka.ru and every saint page they link."""
    raw = os.path.join(BASE_DIR, 'data', 'raw', 'ru')
    spec = importlib.util.spec_from_file_location(
        'azbyka', os.path.join(BASE_DIR, 'scripts', 'russian', 'extract_azbyka_bios.py'))
    azbyka = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(azbyka)

    print(f"=== Russian: azbyka.ru ({year}) ===", file=sys.stderr)
    for cur in days(year):
        try:
            day_html = cache(f"https://azbyka.ru/days/{cur:%Y-%m-%d}",
                             os.path.join(raw, f"azbyka_{cur:%Y-%m-%d}.html"))
        except Exception as e:
            print(f"  ERROR day {cur:%m-%d}: {e}", file=sys.stderr)
            continue
        # The builder reads exactly these entries, so fetch exactly their pages.
        for title, url in azbyka.entries(day_html):
            slug = url.rstrip('/').split('/')[-1]
            try:
                cache(url, os.path.join(raw, f"saint_{slug}.html"))
            except Exception as e:
                print(f"  ERROR {title[:50]}: {e}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument("--locale", choices=["en", "ru"], help="default: both")
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()
    for locale in ([args.locale] if args.locale else ["en", "ru"]):
        (fetch_orthocal if locale == "en" else fetch_azbyka)(args.year)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
