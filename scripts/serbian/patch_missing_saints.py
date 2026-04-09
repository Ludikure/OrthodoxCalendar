#!/usr/bin/env python3
"""
Patch missing fixed saints in saints.json.

Some dates in the 2026 scrape only had moveable feast entries (Holy Week, etc.)
and no fixed saints. This script scrapes those specific dates from other years
where they are regular days, extracts the fixed saints, and patches saints.json.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from html import unescape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from paschalion import Paschalion
from saint_parser import parse_saints_text

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'sr')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'sr')
BASE_URL = "https://www.pravoslavno.rs/index.php"
JULIAN_OFFSET = 13

MOVEABLE_PDISTS = set([-70,-63,-56,-49,-48,-8,-7,-6,-5,-4,-3,-2,-1,
                        0,1,2,3,4,5,6,7,14,24,39,49,50,56])


def fetch_month_page(year: int, month: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"pravoslavno_{year}_{month:02d}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"{BASE_URL}?q=kalendar&godina={year}&mesec={month:02d}"
    print(f"  Fetching {url}...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    with open(cache_file, 'w') as f:
        f.write(html)
    time.sleep(1.5)
    return html


def clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_month_saints(html: str, year: int, month: int) -> dict:
    """Parse monthly page, return {day_number: saints_entry}."""
    # Import the same parsing logic from scrape_pravoslavno
    from scrape_pravoslavno import parse_month, parse_saints_text as _unused

    days = parse_month(html, year, month)
    result = {}
    for day_entry in days:
        greg_day = day_entry["gregorianDay"]
        julian_date = date(year, month, greg_day) - timedelta(days=JULIAN_OFFSET)
        julian_key = f"{julian_date.month:02d}-{julian_date.day:02d}"

        saints = parse_saints_text(
            day_entry["rawText"],
            julian_key=julian_key,
            html_bold=day_entry.get("boldNames", []),
            html_red=day_entry.get("redNames", []),
            html_italic=day_entry.get("italicNames", []),
        )

        if day_entry.get("hasSlava") and saints:
            saints[0]["isSlava"] = True

        key = f"{month:02d}-{greg_day:02d}"
        result[key] = {
            "saints": saints,
            "weekLabel": day_entry.get("weekLabel"),
            "isSunday": day_entry.get("isSunday", False),
            "isSaturday": day_entry.get("isSaturday", False),
            "scrapedFasting": day_entry.get("scrapedFasting"),
        }

    return result


def find_missing_dates() -> list:
    """Find dates in saints.json that have no fixed saints (only moveable feasts from 2026)."""
    saints_file = os.path.join(OUTPUT_DIR, "saints.json")
    with open(saints_file) as f:
        saints_data = json.load(f)

    # Import the moveable feast detection from build_database
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

    pascha_2026 = date(2026, 4, 12)
    missing = []

    for key in sorted(saints_data.get("days", {}).keys()):
        m, d = int(key[:2]), int(key[3:])
        try:
            greg = date(2026, m, d)
        except ValueError:
            continue
        pdist = (greg - pascha_2026).days
        if pdist in MOVEABLE_PDISTS:
            missing.append(key)

    return missing


def find_source_year(month: int, day: int) -> int:
    """Find a year where the given date is NOT a moveable feast."""
    paschas = {
        2023: date(2023, 4, 16),
        2024: date(2024, 5, 5),
        2025: date(2025, 4, 20),
        2027: date(2027, 5, 2),
        2028: date(2028, 4, 16),
        2029: date(2029, 4, 8),
    }
    for yr, p in sorted(paschas.items()):
        greg = date(yr, month, day)
        pdist = (greg - p).days
        if pdist not in MOVEABLE_PDISTS:
            return yr
    return 2024  # fallback


def main():
    missing = find_missing_dates()
    print(f"Missing dates: {len(missing)}", file=sys.stderr)

    # Group by (year, month) to minimize fetches
    fetch_plan = {}  # (year, month) -> [MM-DD keys]
    for key in missing:
        m, d = int(key[:2]), int(key[3:])
        yr = find_source_year(m, d)
        fetch_plan.setdefault((yr, m), []).append(key)

    print(f"Fetch plan:", file=sys.stderr)
    for (yr, m), keys in sorted(fetch_plan.items()):
        print(f"  {yr}/{m:02d}: {keys}", file=sys.stderr)

    # Fetch and parse
    patched = {}
    for (yr, month), keys in sorted(fetch_plan.items()):
        html = fetch_month_page(yr, month)
        month_saints = parse_month_saints(html, yr, month)
        for key in keys:
            if key in month_saints and month_saints[key]["saints"]:
                patched[key] = month_saints[key]
                print(f"  {key}: {month_saints[key]['saints'][0]['name'][:60]}", file=sys.stderr)
            else:
                print(f"  {key}: NOT FOUND in {yr}/{month:02d}", file=sys.stderr)

    # Patch saints.json
    saints_file = os.path.join(OUTPUT_DIR, "saints.json")
    with open(saints_file) as f:
        saints_data = json.load(f)

    for key, entry in patched.items():
        saints_data["days"][key] = entry

    with open(saints_file, 'w') as f:
        json.dump(saints_data, f, ensure_ascii=False, indent=2)

    print(f"\nPatched {len(patched)} dates in saints.json", file=sys.stderr)


if __name__ == "__main__":
    main()
