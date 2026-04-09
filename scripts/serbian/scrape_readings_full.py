#!/usr/bin/env python3
"""
Scrape full scripture readings from pravoslavno.rs for a complete year.
Extracts title + full text for each reading, mapped by:
  1. Pascha distance (for moveable feast readings)
  2. Julian date (for fixed feast/regular readings)

Output: data/processed/sr/lectionary.json
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

YEAR = 2025  # Scrape past year (fully available)
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'sr')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'sr')
JULIAN_OFFSET = 13


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_readings_page(d: date) -> str:
    date_str = d.strftime("%Y-%m-%d")
    cache_file = os.path.join(CACHE_DIR, f"readings_{date_str}.html")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 500:
        with open(cache_file) as f:
            return f.read()

    url = f"https://www.pravoslavno.rs/index.php?q=citanja&datum={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        with open(cache_file, 'w') as f:
            f.write(html)
        time.sleep(1.0)
        return html
    except Exception as e:
        print(f"  ERROR fetching {date_str}: {e}", file=sys.stderr)
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
             "Премудрости", "Сирахова", "Јова"]
    for kw in gospel_kw:
        if kw in title: return "gospel"
    for kw in apostol_kw:
        if kw in title: return "apostol"
    for kw in ot_kw:
        if kw in title: return "ot"
    return "other"


def parse_readings_full(html: str) -> list:
    """Parse readings page extracting title + full scripture text."""
    main_match = re.search(r'id="glavnitekst"[^>]*>(.*?)(?:<a\s+name=teofan|<div\s+class="footer|$)', html, re.DOTALL)
    if not main_match:
        return []

    content = main_match.group(1)
    readings = []

    # Split by <b> tags to find title + text pairs
    parts = re.split(r'(<b>.*?</b>)', content)

    i = 0
    service = None  # Current service context (Јутрења, Литургија)
    while i < len(parts):
        part = parts[i]

        # Check for service labels
        clean_part = re.sub(r'<[^>]+>', '', part).strip()
        if clean_part in ["Јутрења", "Литургија", "Вечерња", "Часови"]:
            service = clean_part
            i += 1
            continue

        # Check if this is a title (<b>...</b>)
        if '<b>' in part:
            title = clean(re.sub(r'<[^>]+>', '', part))
            if not title or len(title) < 10:
                i += 1
                continue

            # Get the text that follows (next part, before next <b>)
            text = ""
            if i + 1 < len(parts):
                next_part = parts[i + 1]
                # Extract text, stopping at next service label or end
                text_html = re.sub(r'<div class="telo17[^"]*">.*?</div>', '', next_part)
                text = clean(re.sub(r'<[^>]+>', '', text_html))
                # Remove JavaScript artifacts
                text = re.sub(r'var showChar.*$', '', text)
                text = re.sub(r'\$\(.*$', '', text)
                text = text.strip(' ;')

            if title and (len(title) > 15 or text):
                # Extract зачало
                zachalo = None
                zach_match = re.search(r'зачало\s*(\d+)', title)
                if zach_match:
                    zachalo = int(zach_match.group(1))

                # Extract reference (e.g., "1,18-25")
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
    pasch = Paschalion(YEAR)

    lectionary = {
        "year": YEAR,
        "source": "pravoslavno.rs",
        "byPaschaDistance": {},  # Moveable feast readings
        "byJulianDate": {},     # Fixed feast + regular readings
    }

    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)
    total = 0
    with_text = 0

    while current <= end:
        if current.day == 1:
            print(f"  {current.strftime('%B %Y')}...", file=sys.stderr)

        html = fetch_readings_page(current)
        if not html:
            current += timedelta(days=1)
            continue

        readings = parse_readings_full(html)
        if not readings:
            current += timedelta(days=1)
            continue

        total += 1
        has_text = any(r.get("text") for r in readings)
        if has_text:
            with_text += 1

        # Store by pascha distance for moveable periods
        pdist = pasch.pascha_distance(current)
        # Moveable period: -70 to +56 (pre-Lent through All Saints)
        if -70 <= pdist <= 56:
            lectionary["byPaschaDistance"][str(pdist)] = readings

        # Also store by Julian date (for fixed feasts and regular days)
        julian = current - timedelta(days=JULIAN_OFFSET)
        julian_key = f"{julian.month:02d}-{julian.day:02d}"
        lectionary["byJulianDate"][julian_key] = readings

        current += timedelta(days=1)

    output_file = os.path.join(OUTPUT_DIR, "lectionary.json")
    with open(output_file, 'w') as f:
        json.dump(lectionary, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {total} days with readings", file=sys.stderr)
    print(f"With full text: {with_text} days", file=sys.stderr)
    print(f"By pascha distance: {len(lectionary['byPaschaDistance'])} entries", file=sys.stderr)
    print(f"By Julian date: {len(lectionary['byJulianDate'])} entries", file=sys.stderr)
    print(f"Saved: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
