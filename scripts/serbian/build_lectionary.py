#!/usr/bin/env python3
"""
Build complete Serbian lectionary from pravoslavno.rs.

Scrapes ALL 365 days from a past year (2024) with full scripture text,
then maps each reading by three keys:
  1. Pascha distance (for moveable feast readings)
  2. Julian date MM-DD (for fixed feast readings)
  3. Week-after-Pentecost + day-of-week (for regular readings)

This gives complete 365-day coverage for any year via Paschalion computation.

Output: data/processed/sr/lectionary_complete.json
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

SCRAPE_YEAR = 2024  # Full past year
JULIAN_OFFSET = 13
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'sr')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'sr')

DOW_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_readings_page(d: date) -> str:
    date_str = d.strftime("%Y-%m-%d")
    cache_file = os.path.join(CACHE_DIR, f"readings_{date_str}.html")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 500:
        with open(cache_file) as f:
            content = f.read()
            # Check it's not an "unavailable" page
            if 'зачало' in content or 'Јеванђеље' in content or 'Мојсијев' in content:
                return content

    url = f"https://www.pravoslavno.rs/index.php?q=citanja&datum={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        with open(cache_file, 'w') as f:
            f.write(html)
        time.sleep(1.0)
        return html
    except Exception as e:
        print(f"  ERROR {date_str}: {e}", file=sys.stderr)
        return ""


def clean(text: str) -> str:
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    # Remove footer junk from pravoslavno.rs pages
    text = re.sub(r'\s*Охридски пролог.*', '', text, flags=re.DOTALL)
    text = re.sub(r'\s*document\.addEventListener.*', '', text, flags=re.DOTALL)
    text = re.sub(r'\s*©\s*Микро књига.*', '', text, flags=re.DOTALL)
    return text.strip()


def classify_reading(title: str) -> str:
    gospel_kw = ["Јеванђеље", "Матеј", "Марко", "Лука", "Јован"]
    apostol_kw = ["Посланица", "Апостол", "Дела апостолска", "Дела светих апостола",
                  "Коринћанима", "Галатима", "Ефесцима", "Филипљанима", "Колошанима",
                  "Солунцима", "Тимотеју", "Титу", "Филимону", "Јеврејима",
                  "Римљанима", "Петрова", "Јованова", "Јаковљева", "Јудина"]
    ot_kw = ["Мојсијев", "књига", "Књига", "Приче Соломонове", "пророка",
             "Исаије", "Јеремије", "Језекиља", "Данила", "Псалам",
             "Премудрости", "Јова"]
    for kw in gospel_kw:
        if kw in title: return "gospel"
    for kw in apostol_kw:
        if kw in title: return "apostol"
    for kw in ot_kw:
        if kw in title: return "ot"
    return "other"


def parse_readings(html: str) -> list:
    """Parse readings with full scripture text."""
    main_match = re.search(r'id="glavnitekst"[^>]*>(.*?)(?:<a\s+name=teofan|<div\s+class="footer|$)', html, re.DOTALL)
    if not main_match:
        return []

    content = main_match.group(1)
    readings = []

    # Split by <b> tags
    parts = re.split(r'(<b>.*?</b>)', content)
    service = None

    i = 0
    while i < len(parts):
        part = parts[i]
        clean_part = re.sub(r'<[^>]+>', '', part).strip()

        # Check for service labels
        if clean_part in ["Јутрења", "Литургија", "Вечерња", "Часови", "На Литургији"]:
            service = clean_part
            i += 1
            continue

        if '<b>' in part:
            title = clean(re.sub(r'<[^>]+>', '', part))
            if not title or len(title) < 10:
                i += 1
                continue

            # Get following text
            text = ""
            if i + 1 < len(parts):
                next_part = parts[i + 1]
                text = clean(re.sub(r'<[^>]+>', '', next_part))
                text = re.sub(r'var showChar.*$', '', text)
                text = re.sub(r'\$\(.*$', '', text)
                text = re.sub(r'затвори\s*$', '', text)
                text = re.sub(r'даље\s*$', '', text)
                text = text.strip(' ;')

            if title and len(title) > 15:
                zachalo = None
                zach_match = re.search(r'зачало\s*(\d+)', title)
                if zach_match:
                    zachalo = int(zach_match.group(1))

                ref_match = re.search(r'\(([^)]+)\)\s*$', title)
                reference = ref_match.group(1) if ref_match else None

                reading = {
                    "title": title,
                    "type": classify_reading(title),
                    "text": text if text and len(text) > 10 else None,
                }
                if service:
                    reading["service"] = service
                if zachalo:
                    reading["zachalo"] = zachalo
                if reference:
                    reading["reference"] = reference
                readings.append(reading)
        i += 1

    return readings


def main():
    ensure_dirs()
    pasch = Paschalion(SCRAPE_YEAR)

    # Three mapping dictionaries
    by_pascha_dist = {}   # str(pdist) → readings
    by_julian_date = {}   # "MM-DD" → readings
    by_week_dow = {}      # "weekN_dow" → readings

    current = date(SCRAPE_YEAR, 1, 1)
    end = date(SCRAPE_YEAR, 12, 31)
    total = 0
    with_text = 0

    while current <= end:
        if current.day == 1:
            print(f"  {current.strftime('%B %Y')}...", file=sys.stderr)

        html = fetch_readings_page(current)
        if not html or ('доступна' in html.lower() and 'нису' in html.lower()):
            current += timedelta(days=1)
            continue

        readings = parse_readings(html)
        if not readings:
            current += timedelta(days=1)
            continue

        total += 1
        if any(r.get("text") for r in readings):
            with_text += 1

        pdist = pasch.pascha_distance(current)

        # Key 1: Pascha distance (moveable feasts, -70 to +56)
        by_pascha_dist[str(pdist)] = readings

        # Key 2: Julian date (fixed feasts + all days)
        julian = current - timedelta(days=JULIAN_OFFSET)
        julian_key = f"{julian.month:02d}-{julian.day:02d}"
        by_julian_date[julian_key] = readings

        # Key 3: Week after Pentecost + day of week (regular readings)
        # Week 1 starts the Monday after All Saints (pdist 57)
        if pdist >= 57:
            week_num = (pdist - 57) // 7 + 1
            dow = DOW_NAMES[current.weekday()]
            week_key = f"week{week_num}_{dow}"
            by_week_dow[week_key] = readings
        elif pdist < -70:
            # Before pre-Lent: use previous year's Pentecost week counting
            # These are the weeks at the END of the Pentecost cycle
            # Map by Julian date as primary key
            pass

        current += timedelta(days=1)

    # Save
    lectionary = {
        "scrapeYear": SCRAPE_YEAR,
        "source": "pravoslavno.rs",
        "byPaschaDistance": by_pascha_dist,
        "byJulianDate": by_julian_date,
        "byWeekAfterPentecost": by_week_dow,
        "stats": {
            "totalDays": total,
            "withText": with_text,
            "paschaDistEntries": len(by_pascha_dist),
            "julianDateEntries": len(by_julian_date),
            "weekDowEntries": len(by_week_dow),
        }
    }

    output_file = os.path.join(OUTPUT_DIR, "lectionary_complete.json")
    with open(output_file, 'w') as f:
        json.dump(lectionary, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {total} days scraped", file=sys.stderr)
    print(f"With full text: {with_text} days", file=sys.stderr)
    print(f"By pascha distance: {len(by_pascha_dist)} entries", file=sys.stderr)
    print(f"By Julian date: {len(by_julian_date)} entries", file=sys.stderr)
    print(f"By week/dow: {len(by_week_dow)} entries", file=sys.stderr)
    print(f"Saved: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
