#!/usr/bin/env python3
"""
Enhanced scraper for azbyka.ru/days — Russian Orthodox calendar.

Extracts with full HTML structure preservation:
- Saints with hierarchy (liturgika icon → great, bold → secondary, plain → tertiary)
- Scripture readings with service labels and зачало numbers
- St. Theophan's daily reflection
- Liturgical period labels
- Feast importance from HTML structure

Output: data/processed/ru/saints.json, data/processed/ru/readings.json, data/processed/ru/reflections.json
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date, timedelta
from html import unescape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from saint_parser import parse_azbyka_saints
from paschalion import Paschalion

YEAR = 2026
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'ru')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'ru')


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_day_page(greg_date: date) -> str:
    """Fetch or load cached azbyka.ru day page."""
    date_str = greg_date.strftime('%Y-%m-%d')
    cache_file = os.path.join(CACHE_DIR, f"azbyka_{date_str}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"https://azbyka.ru/days/{date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    with open(cache_file, 'w') as f:
        f.write(html)
    time.sleep(1.0)
    return html


def strip_accents(text: str) -> str:
    """Remove combining accent marks from text."""
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def clean(text: str) -> str:
    text = unescape(text)
    text = strip_accents(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ─── Page Parsing ───

def parse_day(html: str) -> dict:
    """Parse an azbyka.ru day page with full structure."""
    result = {
        "saints": [],
        "readings": [],
        "reflection": None,
        "liturgicalPeriod": None,
        "fasting": None,
    }

    # ── Saints with hierarchy ──
    saint_items = []
    for match in re.finditer(r'<li class="ideograph-(\d+)">(.*?)</li>', html, re.DOTALL):
        level = int(match.group(1))
        li_html = match.group(2)

        # Check for liturgika icon (great feast)
        has_liturgika = bool(re.search(r'img/liturgika/', li_html))

        # Check for bold
        is_bold = bool(re.search(r'<b>', li_html))

        # Extract name from <a> tag — find the <a> with real text, not just an icon image
        a_matches = re.findall(r'<a[^>]*>(.*?)</a>', li_html, re.DOTALL)
        name = ""
        for a_inner in a_matches:
            # Remove secondary-content spans (dates in parentheses)
            a_clean = re.sub(r'<span[^>]*class=[\'"]?secondary-content[^>]*>.*?</span>', '', a_inner, flags=re.DOTALL)
            candidate = clean(re.sub(r'<[^>]+>', '', a_clean))
            if candidate:
                name = candidate
                break
        if not name:
            name = clean(re.sub(r'<[^>]+>', '', li_html))

        if name:
            saint_items.append({
                "name": name,
                "level": level,
                "is_bold": is_bold,
                "has_liturgika_icon": has_liturgika,
            })

    result["saints"] = parse_azbyka_saints(saint_items)

    # ── Scripture Readings ──
    # Extract from the readings-text div which contains <a class="bibref"> elements
    # and service labels like "Утр.", "Лит.", "На 6-м часе:", "На веч.:"
    readings_div = re.search(r'<div\s+class="readings-text">(.*?)</div>', html, re.DOTALL)
    if readings_div:
        readings_html = readings_div.group(1)

        # Split the readings text into segments by service labels
        # First, flatten to semi-plain text preserving bibref links
        # Extract service context and bibref pairs
        # Walk through the HTML: track current service label, collect bibrefs with zachala

        # Get the plain text with bibref markers preserved
        # Replace bibref links with a marker we can parse
        def extract_readings_from_html(rhtml):
            """Extract readings from the readings-text HTML block."""
            readings = []
            # Find all bibref references with their surrounding context
            # We need to find service labels and associate them with bibrefs

            # First, strip to text but keep bibref content tagged
            # Replace <a class="bibref" ...>TEXT</a> with [[BIBREF:TEXT]]
            marked = re.sub(
                r'<a\s+class="bibref"[^>]*>(.*?)</a>',
                r'[[BIBREF:\1]]',
                rhtml,
                flags=re.DOTALL
            )
            # Strip remaining HTML tags
            marked = re.sub(r'<[^>]+>', ' ', marked)
            marked = unescape(marked)
            marked = re.sub(r'\s+', ' ', marked).strip()

            # Now parse: find service labels and bibrefs
            # Service patterns: "Утр." "Лит." "Лит." "На 6-м часе:" "На веч.:" etc.
            current_service = ""
            # Split around bibrefs
            parts = re.split(r'\[\[BIBREF:(.*?)\]\]', marked)
            # parts[0] = text before first bibref
            # parts[1] = first bibref content
            # parts[2] = text between first and second bibref
            # etc.

            for i in range(len(parts)):
                if i % 2 == 0:
                    # Text segment — look for service labels
                    text = parts[i]
                    svc = re.search(
                        r'(Утр|Лит|На\s+\d+-м\s+часе|На\s+веч|Веч)\s*[\.\:]*\s*[–\-]?\s*$',
                        text.strip()
                    )
                    if svc:
                        current_service = svc.group(1).strip()
                    # Also check for service label anywhere in the text
                    svc2 = re.search(
                        r'(Утр|Лит|На\s+\d+-м\s+часе|На\s+веч|Веч)\s*[\.\:]*\s*[–\-]?',
                        text
                    )
                    if svc2:
                        current_service = svc2.group(1).strip()
                else:
                    # Bibref content like "Мф.1:18–25" or "Гал.4:4–7"
                    ref_text = clean(parts[i])
                    if not ref_text:
                        continue

                    # Parse book and reference
                    ref_match = re.match(r'([А-Яа-яЁё]+)\.\s*(.*)', ref_text)
                    if ref_match:
                        book = ref_match.group(1)
                        reference = ref_text  # e.g. "Гал.4:4–7"
                    else:
                        book = ref_text
                        reference = ref_text

                    # Look for zachalo in following text
                    zachalo = None
                    if i + 1 < len(parts):
                        zach_match = re.search(r'зач\D*?(\d+)', parts[i + 1])
                        if zach_match:
                            zachalo = int(zach_match.group(1))

                    # Determine type
                    gospel_books = ["Мф", "Мк", "Лк", "Ин"]
                    rtype = "gospel" if book in gospel_books else "apostol"

                    reading = {
                        "type": rtype,
                        "service": current_service,
                        "book": book,
                        "reference": reference,
                    }
                    if zachalo:
                        reading["zachalo"] = zachalo
                    readings.append(reading)

            return readings

        result["readings"] = extract_readings_from_html(readings_html)

    # ── Reflection (St. Theophan) ──
    feofan_match = re.search(r'class="[^"]*day__feofan[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not feofan_match:
        feofan_match = re.search(r'DD_FEOFAN[^>]*>(.*?)</(?:div|DIV)>', html, re.DOTALL)
    if feofan_match:
        feofan_text = clean(re.sub(r'<[^>]+>', '', feofan_match.group(1)))
        if feofan_text and len(feofan_text) > 10:
            result["reflection"] = {
                "source": "Мысли на каждый день — Свт. Феофан Затворник",
                "text": feofan_text,
            }

    # ── Liturgical Period ──
    # Extract from the <div class="shadow"> element inside day__post-wp
    # Structure: <div class="shadow"><div class="lc">...</div> TEXT WITH <a> TAGS <div class="rc">...</div></div>
    shadow_match = re.search(
        r'<div\s+class="shadow">\s*<div\s+class="lc">[^<]*</div>(.*?)<div\s+class="rc">',
        html, re.DOTALL
    )
    if shadow_match:
        period_html = shadow_match.group(1)
        # Strip HTML tags to get clean text
        period_text = clean(re.sub(r'<[^>]+>', '', period_html))
        if period_text:
            result["liturgicalPeriod"] = period_text

    # ── Fasting (basic — just what azbyka shows) ──
    fast_match = re.search(r'day__post-wp[^>]*dayinfo_color\s+wp-(\w+)', html)
    if fast_match:
        result["fasting"] = fast_match.group(1)  # "white", "green", etc.

    return result


# ─── Fasting from pravoslavie.ru ───

def fetch_pravoslavie_fasting(greg_date: date) -> dict:
    """Fetch detailed fasting from days.pravoslavie.ru."""
    julian = greg_date - timedelta(days=13)
    jdate_str = julian.strftime("%Y%m%d")
    cache_file = os.path.join(CACHE_DIR, f"pravoslavie_fast_{greg_date.strftime('%Y-%m-%d')}.html")

    if os.path.exists(cache_file):
        with open(cache_file) as f:
            html = f.read()
    else:
        url = f"https://days.pravoslavie.ru/Days/{jdate_str}.html"
        req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
        try:
            html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
            with open(cache_file, 'w') as f:
                f.write(html)
            time.sleep(0.5)
        except Exception as e:
            return {}

    result = {}

    # Extract fasting description
    diet_match = re.search(r'DD_TPTXT[^>]*>(.*?)</SPAN>', html)
    if diet_match:
        result["description"] = clean(re.sub(r'<[^>]+>', '', diet_match.group(1)))

    # Extract fasting period
    post_match = re.search(r'DD_POST[^>]*>(.*?)</SPAN>', html)
    if post_match:
        result["period"] = clean(re.sub(r'<[^>]+>', '', post_match.group(1)))

    # Extract Feofan reflection (if not already from azbyka)
    feofan_match = re.search(r'DD_FEOFAN[^>]*>(.*?)</DIV>', html, re.DOTALL)
    if feofan_match:
        result["reflection"] = clean(re.sub(r'<[^>]+>', '', feofan_match.group(1)))

    # Extract liturgical notes
    prim_match = re.search(r'DD_PRIM[^>]*>(.*?)</SPAN>', html, re.DOTALL)
    if prim_match:
        result["liturgicalNote"] = clean(re.sub(r'<[^>]+>', '', prim_match.group(1)))

    return result


# ─── Main Pipeline ───

def run_pipeline():
    ensure_dirs()

    all_saints = {}
    all_readings = {}
    all_reflections = {}
    all_fasting = {}

    print(f"=== Russian Pipeline: azbyka.ru + pravoslavie.ru {YEAR} ===", file=sys.stderr)

    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)

    while current <= end:
        if current.day == 1:
            print(f"\n  {current.strftime('%B %Y')}...", file=sys.stderr)

        key = current.strftime("%m-%d")

        # Step 1: Parse azbyka.ru day page (saints, readings, reflection)
        try:
            html = fetch_day_page(current)
            day_data = parse_day(html)

            if day_data["saints"]:
                all_saints[key] = {
                    "saints": day_data["saints"],
                    "liturgicalPeriod": day_data.get("liturgicalPeriod"),
                }

            if day_data["readings"]:
                all_readings[key] = day_data["readings"]

            if day_data["reflection"]:
                all_reflections[key] = day_data["reflection"]

        except Exception as e:
            print(f"    Error parsing azbyka {current}: {e}", file=sys.stderr)

        # Step 2: Fetch detailed fasting from pravoslavie.ru
        try:
            fasting = fetch_pravoslavie_fasting(current)
            if fasting:
                all_fasting[key] = fasting
        except Exception as e:
            print(f"    Error fetching fasting {current}: {e}", file=sys.stderr)

        current += timedelta(days=1)

    # Save outputs
    for name, data, desc in [
        ("saints.json", {"year": YEAR, "source": "azbyka.ru", "days": all_saints}, "saints"),
        ("readings.json", {"year": YEAR, "source": "azbyka.ru", "days": all_readings}, "readings"),
        ("reflections.json", {"year": YEAR, "source": "azbyka.ru", "days": all_reflections}, "reflections"),
        ("fasting.json", {"year": YEAR, "source": "days.pravoslavie.ru", "days": all_fasting}, "fasting"),
    ]:
        filepath = os.path.join(OUTPUT_DIR, name)
        with open(filepath, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {filepath} ({len(data['days'])} {desc})", file=sys.stderr)


if __name__ == "__main__":
    run_pipeline()
