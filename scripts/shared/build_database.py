#!/usr/bin/env python3
"""
Merge Pipeline — Combines all scraped data into final calendar JSONs.

Inputs:
  - data/processed/sr/saints.json, readings.json
  - data/processed/ru/saints.json, readings.json, reflections.json, fasting.json
  - Paschalion (computed)
  - Fasting Engine (computed)

Outputs:
  - data/output/calendar_sr_2026.json
  - data/output/calendar_ru_2026.json
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion
from fasting_engine import compute_fasting, get_fasting_info, FASTING_ABBREV, FASTING_ICONS
from generate_readings import generate_all_readings

YEAR = 2026
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
JULIAN_OFFSET = 13


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, using empty dict", file=sys.stderr)
        return {"days": {}}
    with open(path) as f:
        return json.load(f)


def to_julian_key(greg_date: date) -> str:
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return f"{julian.month:02d}-{julian.day:02d}"


def build_calendar(locale: str, year: int):
    """Build the final calendar JSON for a locale."""
    pasch = Paschalion(year)
    proc_dir = os.path.join(DATA_DIR, 'processed', locale)

    # Load scraped data
    saints_data = load_json(os.path.join(proc_dir, 'saints.json')).get('days', {})

    # Use the lectionary engine + scraped text for readings
    print(f"  Generating engine-based readings for {locale} {year}...", file=sys.stderr)
    engine_readings = generate_all_readings(year, locale)

    # Fall back: load raw scraped readings for days the engine has no data
    readings_data = load_json(os.path.join(proc_dir, 'readings.json')).get('days', {})

    # Russian-specific
    reflections_data = {}
    fasting_descriptions = {}
    if locale == 'ru':
        reflections_data = load_json(os.path.join(proc_dir, 'reflections.json')).get('days', {})
        fasting_descriptions = load_json(os.path.join(proc_dir, 'fasting.json')).get('days', {})

    calendar = {}
    current = date(year, 1, 1)
    end = date(year, 12, 31)

    while current <= end:
        key = current.strftime("%m-%d")
        julian_key = to_julian_key(current)

        # Determine feast rank for fasting upgrade
        great_feast = pasch.is_great_feast(current)
        feast_rank = "great" if great_feast else None

        # Compute algorithmic fasting
        fasting_level = compute_fasting(current, pasch, feast_rank)
        fasting_info = get_fasting_info(fasting_level, locale)

        # Get scraped fasting description (supplements algorithmic)
        scraped_fasting = fasting_descriptions.get(key, {})

        # Build day entry
        day = {
            "gregorianDate": current.isoformat(),
            "julianDate": julian_key,
            "dayOfWeek": current.weekday(),  # 0=Mon..6=Sun
            "paschaDistance": pasch.pascha_distance(current),

            # Feasts/Saints
            "feasts": saints_data.get(key, {}).get("saints", []),
            "liturgicalPeriod": saints_data.get(key, {}).get("liturgicalPeriod"),
            "weekLabel": saints_data.get(key, {}).get("weekLabel"),

            # Great feast override
            "greatFeast": great_feast,

            # Fasting (algorithmic + scraped description)
            "fasting": {
                "type": fasting_level,
                "label": fasting_info["label"],
                "explanation": scraped_fasting.get("description") or fasting_info["explanation"],
                "abbrev": fasting_info["abbrev"],
                "icon": fasting_info["icon"],
            },

            # Readings: prefer engine-generated, fall back to raw scraped
            "readings": engine_readings.get(key) or readings_data.get(key, []),

            # Reflection
            "reflection": reflections_data.get(key),

            # Fasting period context
            "fastingPeriod": pasch.get_fasting_period(current),
            "isFastFreeWeek": pasch.is_fast_free_week(current),
        }

        # Add liturgical note from pravoslavie.ru
        if scraped_fasting.get("liturgicalNote"):
            day["liturgicalNote"] = scraped_fasting["liturgicalNote"]

        calendar[key] = day
        current += timedelta(days=1)

    return calendar


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for locale in ['sr', 'ru']:
        print(f"\n=== Building calendar_{locale}_{YEAR}.json ===", file=sys.stderr)
        calendar = build_calendar(locale, YEAR)

        output_file = os.path.join(OUTPUT_DIR, f"calendar_{locale}_{YEAR}.json")
        with open(output_file, 'w') as f:
            json.dump({
                "year": YEAR,
                "locale": locale,
                "generatedBy": "build_database.py",
                "days": calendar,
            }, f, ensure_ascii=False, indent=2)

        # Stats
        days_with_saints = sum(1 for d in calendar.values() if d["feasts"])
        days_with_readings = sum(1 for d in calendar.values() if d["readings"])
        days_with_reflection = sum(1 for d in calendar.values() if d.get("reflection"))
        great_feasts = sum(1 for d in calendar.values() if d["greatFeast"])

        print(f"  Days: {len(calendar)}", file=sys.stderr)
        print(f"  With saints: {days_with_saints}", file=sys.stderr)
        print(f"  With readings: {days_with_readings}", file=sys.stderr)
        print(f"  With reflection: {days_with_reflection}", file=sys.stderr)
        print(f"  Great feasts: {great_feasts}", file=sys.stderr)
        print(f"  Saved: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
