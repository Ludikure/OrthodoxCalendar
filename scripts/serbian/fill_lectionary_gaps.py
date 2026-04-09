#!/usr/bin/env python3
"""
Fill gaps in the Serbian lectionary by scraping missing dates from pravoslavno.rs.

For each missing Julian date in lectionary_merged.json:
1. Compute the Gregorian equivalent for years 2024, 2023, 2022, 2021, 2020
2. Try fetching from pravoslavno.rs (stop when found)
3. Parse readings using the same approach as build_lectionary.py
4. Update lectionary_merged.json
5. Re-apply to calendar_sr_2026.json
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from html import unescape

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'sr')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'sr')
CALENDAR_FILE = os.path.join(BASE_DIR, 'OrthodoxCalendar', 'Localization', 'calendar_sr_2026.json')

LECTIONARY_FILE = os.path.join(PROCESSED_DIR, 'lectionary_merged.json')
JULIAN_OFFSET = 13
YEARS_TO_TRY = [2024, 2023, 2022, 2021, 2020]
DELAY = 3.0

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from paschalion import Paschalion

DOW_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


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


def parse_readings_full(html: str) -> list:
    """Parse readings with full scripture text.

    Handles three HTML patterns used by pravoslavno.rs:
      1. <b>TITLE</b> followed by text
      2. <div class="telo17 crvena_tamna">TITLE</div> followed by text
      3. <span class="telo17 crvena_tamna">TITLE</span> followed by text
    """
    main_match = re.search(r'id="glavnitekst"[^>]*>(.*?)(?:<a\s+name=teofan|<div\s+class="footer|$)', html, re.DOTALL)
    if not main_match:
        return []

    content = main_match.group(1)
    readings = []

    # Split by all three title container patterns
    title_pattern = (
        r'(<div\s+class="telo17 crvena_tamna">.*?</div>'
        r'|<span\s+class="telo17 crvena_tamna">.*?</span>'
        r'|<b>.*?</b>)'
    )
    parts = re.split(title_pattern, content, flags=re.DOTALL)
    service = None

    i = 0
    while i < len(parts):
        part = parts[i]
        clean_part = re.sub(r'<[^>]+>', '', part).strip()

        if clean_part in ["Јутрења", "Литургија", "Вечерња", "Часови", "На Литургији"]:
            service = clean_part
            i += 1
            continue

        is_title = bool(
            re.match(r'<div\s+class="telo17 crvena_tamna">', part) or
            re.match(r'<span\s+class="telo17 crvena_tamna">', part) or
            re.match(r'<b>', part)
        )

        if is_title:
            title = clean(re.sub(r'<[^>]+>', '', part))
            if not title or len(title) < 10:
                i += 1
                continue

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


def fetch_page(greg_date: date) -> str:
    """Fetch a readings page, using cache if available."""
    date_str = greg_date.strftime("%Y-%m-%d")
    cache_file = os.path.join(CACHE_DIR, f"readings_{date_str}.html")

    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 500:
        with open(cache_file) as f:
            content = f.read()
            if ('зачало' in content or 'Јеванђеље' in content or 'Мојсијев' in content
                    or 'Посланица' in content or 'crvena_tamna' in content
                    or 'glavnitekst' in content):
                return content

    url = f"https://www.pravoslavno.rs/index.php?q=citanja&datum={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        print(f"    Fetching {url}...", file=sys.stderr)
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        with open(cache_file, 'w') as f:
            f.write(html)
        time.sleep(DELAY)
        return html
    except Exception as e:
        print(f"    ERROR {date_str}: {e}", file=sys.stderr)
        return ""


def julian_to_gregorian_for_year(julian_mm_dd: str, year: int) -> date:
    """Given a Julian MM-DD and a year, return the Gregorian date."""
    jm, jd = int(julian_mm_dd[:2]), int(julian_mm_dd[3:])
    # Julian date + 13 = Gregorian date
    # But we need to handle month overflow
    import calendar
    greg_day = jd + JULIAN_OFFSET
    greg_month = jm
    greg_year = year
    dim = calendar.monthrange(greg_year, greg_month)[1]
    if greg_day > dim:
        greg_day -= dim
        greg_month += 1
        if greg_month > 12:
            greg_month = 1
            greg_year += 1
    return date(greg_year, greg_month, greg_day)


def find_missing_julian_dates(lectionary: dict) -> list:
    """Find Julian dates needed for 2026 that are missing from the lectionary."""
    existing = set(lectionary.get('byJulianDate', {}).keys())
    needed = set()
    current = date(2026, 1, 1)
    end = date(2026, 12, 31)
    while current <= end:
        julian = current - timedelta(days=JULIAN_OFFSET)
        key = f"{julian.month:02d}-{julian.day:02d}"
        needed.add(key)
        current += timedelta(days=1)

    missing = sorted(needed - existing)
    return missing


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Load existing lectionary
    with open(LECTIONARY_FILE) as f:
        lectionary = json.load(f)

    missing = find_missing_julian_dates(lectionary)
    print(f"Missing Julian dates: {len(missing)}", file=sys.stderr)

    filled = 0
    failed = []

    for julian_key in missing:
        print(f"\n  Processing Julian {julian_key}...", file=sys.stderr)
        found = False

        for year in YEARS_TO_TRY:
            greg_date = julian_to_gregorian_for_year(julian_key, year)
            html = fetch_page(greg_date)

            if not html:
                continue
            if 'доступна' in html.lower() and 'нису' in html.lower():
                continue

            readings = parse_readings_full(html)
            if readings:
                # Add to lectionary
                lectionary['byJulianDate'][julian_key] = readings

                # Also add pascha distance key for this year's Pascha
                pasch = Paschalion(year)
                pdist = pasch.pascha_distance(greg_date)
                pdist_key = str(pdist)
                if pdist_key not in lectionary.get('byPaschaDistance', {}):
                    lectionary['byPaschaDistance'][pdist_key] = readings

                # Also add week-after-pentecost key
                if pdist >= 57:
                    week_num = (pdist - 57) // 7 + 1
                    dow = DOW_NAMES[greg_date.weekday()]
                    week_key = f"week{week_num}_{dow}"
                    if week_key not in lectionary.get('byWeekAfterPentecost', {}):
                        lectionary['byWeekAfterPentecost'][week_key] = readings

                filled += 1
                print(f"    FOUND via {year} ({greg_date}): {len(readings)} readings", file=sys.stderr)
                found = True
                break

        if not found:
            failed.append(julian_key)
            print(f"    FAILED: no readings found for Julian {julian_key}", file=sys.stderr)

    # Save updated lectionary
    with open(LECTIONARY_FILE, 'w') as f:
        json.dump(lectionary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved lectionary: {LECTIONARY_FILE}", file=sys.stderr)
    print(f"Filled: {filled}/{len(missing)} gaps", file=sys.stderr)
    print(f"New byJulianDate count: {len(lectionary['byJulianDate'])}", file=sys.stderr)
    if failed:
        print(f"Still missing: {failed}", file=sys.stderr)

    # ─── Step 2: Update calendar_sr_2026.json ───
    print(f"\n=== Updating calendar_sr_2026.json ===", file=sys.stderr)

    with open(CALENDAR_FILE) as f:
        calendar = json.load(f)

    pasch_2026 = Paschalion(2026)
    updated = 0

    for greg_key, day in calendar['days'].items():
        if day.get('readings'):
            continue  # Already has readings

        julian_key = day.get('julianDate')
        pdist = day.get('paschaDistance')
        greg_date_obj = date(2026, int(greg_key[:2]), int(greg_key[3:]))

        readings = None

        # Priority 1: Pascha distance
        if pdist is not None:
            pdist_str = str(pdist)
            if pdist_str in lectionary.get('byPaschaDistance', {}):
                readings = lectionary['byPaschaDistance'][pdist_str]

        # Priority 2: Julian date
        if not readings and julian_key:
            if julian_key in lectionary.get('byJulianDate', {}):
                readings = lectionary['byJulianDate'][julian_key]

        # Priority 3: Week after Pentecost
        if not readings and pdist is not None and pdist >= 57:
            week_num = (pdist - 57) // 7 + 1
            dow = DOW_NAMES[greg_date_obj.weekday()]
            week_key = f"week{week_num}_{dow}"
            if week_key in lectionary.get('byWeekAfterPentecost', {}):
                readings = lectionary['byWeekAfterPentecost'][week_key]

        if readings:
            day['readings'] = readings
            updated += 1

    # Save updated calendar
    with open(CALENDAR_FILE, 'w') as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)

    total_with = sum(1 for d in calendar['days'].values() if d.get('readings'))
    total_without = sum(1 for d in calendar['days'].values() if not d.get('readings'))
    print(f"Updated {updated} days in calendar", file=sys.stderr)
    print(f"Final coverage: {total_with}/365 days with readings ({total_without} still missing)", file=sys.stderr)


if __name__ == "__main__":
    main()
