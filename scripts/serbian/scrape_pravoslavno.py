#!/usr/bin/env python3
"""
Scrape pravoslavno.rs — Primary Serbian calendar source.

Monthly calendar pages + daily ЧИТАЊЕ (readings) links.
Preserves HTML formatting (bold, italic, red, СЛАВА) for saint hierarchy.

Output: data/processed/sr/saints.json, data/processed/sr/readings.json
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from html import unescape

# Add shared scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from saint_parser import parse_saints_text
from paschalion import Paschalion

YEAR = 2026
BASE_URL = "https://www.pravoslavno.rs/index.php"
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'sr')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'sr')


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8")


def fetch_month_page(year: int, month: int) -> str:
    """Fetch or load cached monthly calendar page."""
    cache_file = os.path.join(CACHE_DIR, f"pravoslavno_{year}_{month:02d}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"{BASE_URL}?q=kalendar&godina={year}&mesec={month:02d}"
    print(f"  Fetching {url}...", file=sys.stderr)
    html = fetch_url(url)
    with open(cache_file, 'w') as f:
        f.write(html)
    time.sleep(1.5)
    return html


def fetch_readings_page(date_str: str) -> str:
    """Fetch or load cached readings page."""
    cache_file = os.path.join(CACHE_DIR, f"readings_{date_str}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"{BASE_URL}?q=citanja&datum={date_str}"
    print(f"    Reading: {url}", file=sys.stderr)
    html = fetch_url(url)
    with open(cache_file, 'w') as f:
        f.write(html)
    time.sleep(1.0)
    return html


def clean_text(text: str) -> str:
    """Clean HTML entities and normalize whitespace."""
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ─── Calendar Page Parsing ───

def parse_month(html: str, year: int, month: int) -> list:
    """Parse a monthly calendar page into day entries."""
    days = []

    # Find the main calendar table (id="tabelakal")
    table_match = re.search(r'<table id="tabelakal"[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        print(f"  WARNING: Calendar table not found for {year}/{month}", file=sys.stderr)
        return days

    table_html = table_match.group(1)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(cells) < 5:
            continue

        # Parse cells
        # Cell structure varies, but typically:
        # [weekday, new_date, old_date, fasting?, feast_text, readings?]

        # Extract new-style date from cells
        date_match = None
        for cell in cells[:3]:
            clean = re.sub(r'<[^>]+>', '', cell).strip()
            if clean.isdigit() and 1 <= int(clean) <= 31:
                if date_match is None:
                    date_match = int(clean)

        if date_match is None:
            continue

        greg_day = date_match

        # Find the feast text cell (the widest one with saints)
        feast_cell_html = ""
        for cell in cells:
            if '<a href="index.php?q=kalen' in cell or 'СЛАВА' in cell or '<b>' in cell:
                feast_cell_html = cell
                break

        if not feast_cell_html:
            # Fallback: use the largest cell
            feast_cell_html = max(cells, key=len)

        # Parse the feast cell
        day_entry = parse_feast_cell(feast_cell_html, year, month, greg_day)
        day_entry["gregorianDay"] = greg_day
        day_entry["gregorianMonth"] = month

        # Extract weekday from row class or first cell
        if 'class="nedelja"' in row_html or 'class="nedelja"' in cells[0] if cells else '':
            day_entry["isSunday"] = True
        if 'class="subota"' in row_html:
            day_entry["isSaturday"] = True

        # Check for fasting cell
        for cell in cells:
            fasting = parse_fasting_cell(cell)
            if fasting:
                day_entry["scrapedFasting"] = fasting
                break

        # Check for readings link
        for cell in cells:
            readings_url = extract_readings_url(cell)
            if readings_url:
                day_entry["readingsUrl"] = readings_url
                break

        days.append(day_entry)

    return days


def parse_feast_cell(cell_html: str, year: int, month: int, day: int) -> dict:
    """Parse a feast text cell, preserving HTML formatting signals."""
    entry = {
        "hasSlava": False,
        "boldNames": [],
        "redNames": [],
        "italicNames": [],
        "weekLabel": None,
        "rawText": "",
    }

    # Check for СЛАВА
    if 'class="slava"' in cell_html or "СЛАВА" in cell_html:
        entry["hasSlava"] = True

    # Extract week/Sunday label (Недеља XX. по Духовима)
    week_match = re.search(r'описnеделје=(.*?)"', cell_html)
    if not week_match:
        week_match = re.search(r'<font color=#ff0000>(Недеља.*?)</font>', cell_html)
    if week_match:
        entry["weekLabel"] = clean_text(re.sub(r'<[^>]+>', '', week_match.group(1)))

    # Extract bold names
    for bold_match in re.finditer(r'<b>(.*?)</b>', cell_html, re.DOTALL):
        name = clean_text(re.sub(r'<[^>]+>', '', bold_match.group(1)))
        if name and name != "СЛАВА" and len(name) > 2:
            entry["boldNames"].append(name)

    # Extract red names
    for red_match in re.finditer(r'<font color=#ff0000>(.*?)</font>', cell_html, re.DOTALL):
        name = clean_text(re.sub(r'<[^>]+>', '', red_match.group(1)))
        if name and not name.startswith("Недеља") and len(name) > 2:
            entry["redNames"].append(name)

    # Extract italic names (Serbian saints)
    for em_match in re.finditer(r'<em>(.*?)</em>', cell_html, re.DOTALL):
        name = clean_text(re.sub(r'<[^>]+>', '', em_match.group(1)))
        if name and len(name) > 2:
            entry["italicNames"].append(name)

    # Build raw text (strip all HTML, clean up)
    raw = re.sub(r'<br\s*/?>', '; ', cell_html)
    raw = re.sub(r'<[^>]+>', '', raw)
    raw = re.sub(r'СЛАВА\s*', '', raw)
    raw = clean_text(raw)

    # Remove week labels from raw text
    if entry["weekLabel"]:
        raw = raw.replace(entry["weekLabel"], "").strip("; ")

    entry["rawText"] = raw

    return entry


def parse_fasting_cell(cell_html: str) -> dict:
    """Extract fasting info from a cell."""
    # Look for fasting-related links or images
    if 'post' in cell_html.lower() or 'постн' in cell_html.lower():
        clean = clean_text(re.sub(r'<[^>]+>', '', cell_html))
        if clean:
            return {"raw": clean}
    # Look for fasting images
    img_match = re.search(r'<img[^>]*src="[^"]*post[^"]*"', cell_html)
    if img_match:
        return {"hasImage": True}
    return None


def extract_readings_url(cell_html: str) -> str:
    """Extract ЧИТАЊЕ link from a cell."""
    match = re.search(r'href="(index\.php\?q=citanja[^"]*)"', cell_html)
    if match:
        return match.group(1)
    return ""


# ─── Readings Page Parsing ───

def _classify_reading(title: str) -> str:
    """Classify a reading title as 'gospel', 'apostol', 'ot' (Old Testament), or 'other'."""
    gospel_kw = ["Јеванђеље", "Матеј", "Марко", "Лука", "Јован"]
    apostol_kw = ["Посланица", "Апостол", "Дела апостолска", "Дела светих апостола",
                  "Коринћанима", "Галатима", "Ефесцима", "Филипљанима", "Колошанима",
                  "Солунцима", "Тимотеју", "Титу", "Филимону", "Јеврејима",
                  "Римљанима", "Петрова", "Јованова", "Јаковљева", "Јудина"]
    ot_kw = ["Мојсијев", "књига", "Књига", "Приче Соломонове", "пророка",
             "Битија", "Излазак", "Левитска", "Бројеви", "Поновљени закон",
             "Псалам", "Псалми", "Премудрости", "Јова", "Исаије", "Јеремије",
             "Језекиља", "Данила", "Осије", "Јоила", "Амоса", "Авдије",
             "Јоне", "Михеја", "Наума", "Авакума", "Софоније", "Агеја",
             "Захарије", "Малахије", "Плач", "Судије", "Рута", "Самуилова",
             "Царства", "Дневника", "Јездра", "Немија", "Јестира",
             "Песма над песмама", "Сирахова", "Варуха", "Макавеја",
             "Товит", "Јудита"]
    for kw in gospel_kw:
        if kw in title:
            return "gospel"
    for kw in apostol_kw:
        if kw in title:
            return "apostol"
    for kw in ot_kw:
        if kw in title:
            return "ot"
    return "other"


def parse_readings(html: str) -> list:
    """Parse a readings page to extract scripture reading references.

    Extracts reading titles from three HTML patterns used by pravoslavno.rs:
      1. <b>TITLE</b>  (inside padding-top divs)
      2. <div class="telo17 crvena_tamna">TITLE</div>
      3. <span class="telo17 crvena_tamna">TITLE</span>
    All within the id="glavnitekst" container.
    """
    readings = []

    # First, isolate the main text container
    main_match = re.search(r'id="glavnitekst"[^>]*>(.*?)(?:<a\s+name=teofan|$)', html, re.DOTALL)
    if not main_match:
        return readings

    main_html = main_match.group(1)

    # Extract all reading titles from the three container types
    titles = []

    # Pattern 1: <b>TITLE</b> inside padding-top divs
    for m in re.finditer(r'<b>(.*?)</b>', main_html, re.DOTALL):
        text = clean_text(re.sub(r'<[^>]+>', '', m.group(1)))
        if text and len(text) > 5:
            titles.append(text)

    # Pattern 2: <div class="telo17 crvena_tamna">TITLE</div>
    for m in re.finditer(r'<div\s+class="telo17 crvena_tamna">(.*?)</div>', main_html, re.DOTALL):
        text = clean_text(re.sub(r'<[^>]+>', '', m.group(1)))
        if text and len(text) > 5:
            titles.append(text)

    # Pattern 3: <span class="telo17 crvena_tamna">TITLE</span> — only the title part before <br>
    for m in re.finditer(r'<span\s+class="telo17 crvena_tamna">(.*?)</span>', main_html, re.DOTALL):
        inner = m.group(1)
        # The title is the text before the first <br> (the rest is verse content)
        br_split = re.split(r'<br\s*/?>', inner, maxsplit=1)
        text = clean_text(re.sub(r'<[^>]+>', '', br_split[0]))
        if text and len(text) > 5:
            titles.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique_titles = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            unique_titles.append(t)

    # Parse each title into a structured reading
    for title in unique_titles:
        rtype = _classify_reading(title)

        # Try to extract зачало number
        zachalo = None
        zach_match = re.search(r'зачало\s*(\d+)', title)
        if zach_match:
            zachalo = int(zach_match.group(1))

        # Try to extract parenthetical reference like (4,4-7) or (1,18-25)
        ref_match = re.search(r'\(([^)]+)\)\s*$', title)
        reference_detail = ref_match.group(1) if ref_match else None

        # Build a short book name from the title
        book = title
        # Remove "Свето Јеванђеље од " prefix
        book = re.sub(r'^Свето\s+Јеванђеље\s+од\s+', '', book)
        # Remove "Посланица Светог Апостола Павла " prefix
        book = re.sub(r'^Посланица\s+Светог\s+Апостола\s+Павла\s+', '', book)
        # Remove "Прва/Друга/Трећа Посланица Светог Апостола Павла " prefix
        book = re.sub(r'^(Прва|Друга|Трећа)\s+Посланица\s+Светог\s+Апостола\s+Павла\s+', r'\1 ', book)
        # Remove "Посланица Светог Апостола " (non-Pauline)
        book = re.sub(r'^(Прва|Друга|Трећа|Саборна)?\s*Посланица\s+Светог\s+Апостола\s+', r'\1 ', book)
        # Remove "Дела светих апостола" -> "Дап"
        if re.match(r'Дела\s+светих\s+апостола', book):
            book = "Дап"
        elif re.match(r'Дела\s+апостолска', book):
            book = "Дап"
        # Trim зачало and reference from book name
        book = re.sub(r',?\s*зачало\s*\d+.*', '', book).strip()
        book = re.sub(r'\s*\([^)]+\)\s*$', '', book).strip()
        book = book.strip(' ,')

        entry = {
            "type": rtype,
            "book": book,
            "title": title,
        }
        if zachalo is not None:
            entry["zachalo"] = zachalo
        if reference_detail:
            entry["reference"] = f"{book} {reference_detail}" if book else reference_detail

        readings.append(entry)

    return readings


# ─── Main Pipeline ───

def run_pipeline():
    ensure_dirs()
    pasch = Paschalion(YEAR)
    all_days = {}
    all_readings = {}

    print(f"=== Serbian Pipeline: pravoslavno.rs {YEAR} ===", file=sys.stderr)

    # Step 1: Fetch and parse all 12 monthly pages
    for month in range(1, 13):
        print(f"\nMonth {month}:", file=sys.stderr)
        html = fetch_month_page(YEAR, month)
        month_days = parse_month(html, YEAR, month)
        print(f"  Parsed {len(month_days)} days", file=sys.stderr)

        for day_entry in month_days:
            greg_day = day_entry["gregorianDay"]
            key = f"{month:02d}-{greg_day:02d}"

            # Run saint parser on the raw text
            julian_date = date(YEAR, month, greg_day) - timedelta(days=13)
            julian_key = f"{julian_date.month:02d}-{julian_date.day:02d}"

            saints = parse_saints_text(
                day_entry["rawText"],
                julian_key=julian_key,
                html_bold=day_entry.get("boldNames", []),
                html_red=day_entry.get("redNames", []),
                html_italic=day_entry.get("italicNames", []),
            )

            # Mark slava
            if day_entry.get("hasSlava") and saints:
                saints[0]["isSlava"] = True

            all_days[key] = {
                "saints": saints,
                "weekLabel": day_entry.get("weekLabel"),
                "isSunday": day_entry.get("isSunday", False),
                "isSaturday": day_entry.get("isSaturday", False),
                "scrapedFasting": day_entry.get("scrapedFasting"),
            }

    # Step 2: Fetch readings for each day
    print(f"\n=== Fetching readings (365 pages) ===", file=sys.stderr)
    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)
    readings_count = 0

    while current <= end:
        key = current.strftime("%m-%d")
        date_str = current.strftime("%Y-%m-%d")

        try:
            html = fetch_readings_page(date_str)
            readings = parse_readings(html)
            if readings:
                all_readings[key] = readings
                readings_count += 1
        except Exception as e:
            print(f"    Error fetching readings for {date_str}: {e}", file=sys.stderr)

        current += timedelta(days=1)

    print(f"\n  Total readings scraped: {readings_count} days", file=sys.stderr)

    # Save outputs
    saints_file = os.path.join(OUTPUT_DIR, "saints.json")
    with open(saints_file, 'w') as f:
        json.dump({"year": YEAR, "source": "pravoslavno.rs", "days": all_days},
                  f, ensure_ascii=False, indent=2)
    print(f"\nSaved {saints_file} ({len(all_days)} days)", file=sys.stderr)

    readings_file = os.path.join(OUTPUT_DIR, "readings.json")
    with open(readings_file, 'w') as f:
        json.dump({"year": YEAR, "source": "pravoslavno.rs", "days": all_readings},
                  f, ensure_ascii=False, indent=2)
    print(f"Saved {readings_file} ({len(all_readings)} days with readings)", file=sys.stderr)


if __name__ == "__main__":
    run_pipeline()
