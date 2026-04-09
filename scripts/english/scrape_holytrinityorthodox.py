#!/usr/bin/env python3
"""
Scrape holytrinityorthodox.com — English Orthodox calendar source.

Per-day AJAX API returning HTML fragments with saints, readings, fasting, and
liturgical week/tone information.

Output: data/processed/en/saints.json, data/processed/en/readings.json
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from html import unescape

YEAR = 2026
BASE_URL = "https://www.holytrinityorthodox.com/htc/ocalendar/v2calendar.php"
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'en')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'en')


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    raw = urllib.request.urlopen(req, timeout=20).read()
    # Some pages use Windows-1252 encoding (en-dash, etc.)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def fetch_day(year: int, month: int, day: int) -> str:
    """Fetch or load cached daily calendar page."""
    cache_file = os.path.join(CACHE_DIR, f"htc_{year}_{month:02d}_{day:02d}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = (f"{BASE_URL}?month={month}&today={day}&year={year}"
           f"&dt=1&header=1&lives=1&scripture=1&trp=0")
    print(f"  Fetching {year}-{month:02d}-{day:02d}...", file=sys.stderr)
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


def strip_tags(html: str) -> str:
    """Remove all HTML tags from a string."""
    return re.sub(r'<[^>]+>', '', html)


# ─── Typicon / Importance Mapping ───

def typicon_to_importance(typicon_class: str, is_bold: bool, is_minor: bool) -> str:
    """Map typicon class + formatting to importance level.

    typicon-6 = Great Feast → "great"
    typicon-1/2/3/4 = ranked saints → "bold"
    typicon-0 = regular → "normal"
    typicon-o = minor → "normal"
    Bold tag on the saint line elevates to at least "bold".
    """
    if typicon_class == "6":
        return "great"
    if typicon_class in ("1", "2", "3", "4"):
        return "bold"
    if is_bold and not is_minor:
        return "bold"
    return "normal"


# ─── Saint Type Detection (English) ───

def detect_saint_type(name: str) -> str:
    """Detect saint type from English name prefixes/keywords."""
    name_lower = name.lower().strip()

    type_map = [
        # Order matters — check more specific before general
        (["equal-to-the-apostles", "equal to the apostles", "equal-to-apostles"], "equal_to_apostles"),
        (["apostle"], "apostle"),
        (["great-martyr", "great martyr", "greatmartyr"], "great_martyr"),
        (["hieromartyr", "new hieromartyr"], "hieromartyr"),
        (["hierarch", "holy hierarch"], "hierarch"),
        (["venerable martyr", "monk-martyr", "new monk-martyr"], "venerable_martyr"),
        (["venerable"], "venerable"),
        (["protomartyr"], "martyr"),
        (["martyr", "new martyr", "martyrs"], "martyr"),
        (["righteous"], "righteous"),
        (["blessed"], "blessed"),
        (["confessor"], "confessor"),
        (["right-believing", "noble"], "noble"),
        (["prophet", "prophetess"], "prophet"),
        (["synaxis", "assembly", "council", "synod"], "synaxis"),
        (["patriarch", "archbishop", "bishop", "metropolitan"], "hierarch"),
    ]

    for prefixes, stype in type_map:
        for prefix in prefixes:
            if prefix in name_lower:
                return stype

    # Check for feast keywords
    feast_keywords = [
        "nativity", "theophany", "baptism of", "meeting of",
        "presentation", "annunciation", "transfiguration", "dormition",
        "elevation of the cross", "exaltation", "entry of",
        "ascension", "pentecost", "pascha", "resurrection",
        "palm sunday", "entrance of the lord",
        "circumcision", "icon of",
    ]
    for kw in feast_keywords:
        if kw in name_lower:
            return "feast"

    return "saint"


# ─── Reading Classification (English) ───

GOSPEL_BOOKS = {
    "matthew", "mark", "luke", "john",
    "matt", "matt.", "mk", "mk.", "lk", "lk.", "jn", "jn.",
}

APOSTOL_BOOKS = {
    "acts", "romans", "1 corinthians", "2 corinthians",
    "galatians", "ephesians", "philippians", "colossians",
    "1 thessalonians", "2 thessalonians",
    "1 timothy", "2 timothy", "titus", "philemon",
    "hebrews", "james", "1 peter", "2 peter",
    "1 john", "2 john", "3 john", "jude", "revelation",
}

OT_BOOKS = {
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    "joshua", "judges", "ruth", "1 samuel", "2 samuel",
    "1 kings", "2 kings", "1 chronicles", "2 chronicles",
    "ezra", "nehemiah", "esther", "job", "psalms", "psalm",
    "proverbs", "ecclesiastes", "song of solomon", "song of songs",
    "isaiah", "jeremiah", "lamentations", "ezekiel", "daniel",
    "hosea", "joel", "amos", "obadiah", "jonah", "micah",
    "nahum", "habakkuk", "zephaniah", "haggai", "zechariah", "malachi",
    "wisdom", "sirach", "baruch", "tobit", "judith",
    "1 maccabees", "2 maccabees",
}


def classify_reading(title: str) -> str:
    """Classify a reading reference as 'gospel', 'apostol', 'ot', or 'other'."""
    title_lower = title.lower().strip()

    # Extract the book name (everything before chapter:verse)
    book_part = re.split(r'\s+\d', title_lower, maxsplit=1)[0].strip()

    if book_part in GOSPEL_BOOKS:
        return "gospel"
    for b in GOSPEL_BOOKS:
        if title_lower.startswith(b):
            return "gospel"

    if book_part in APOSTOL_BOOKS:
        return "apostol"
    for b in APOSTOL_BOOKS:
        if title_lower.startswith(b):
            return "apostol"

    if book_part in OT_BOOKS:
        return "ot"
    for b in OT_BOOKS:
        if title_lower.startswith(b):
            return "ot"

    # Fallback heuristics
    if "acts" in title_lower:
        return "apostol"

    return "other"


def extract_book_name(title: str) -> str:
    """Extract the book name from a reading reference like 'Hebrews 10:35-11:7'."""
    # Match pattern: Book (possibly with number prefix) followed by chapter number
    m = re.match(r'^(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\d', title)
    if m:
        return m.group(1).strip()
    # Fallback: return everything before the first digit
    m = re.match(r'^([A-Za-z\s]+)', title)
    if m:
        return m.group(1).strip()
    return title


# ─── HTML Parsing ───

def parse_week_label(html: str) -> str:
    """Extract liturgical week/tone from the header section."""
    # The headerheader span contains nested spans, so use greedy match up to </p>
    m = re.search(r'<span class="headerheader">(.*?)</span>\s*</span>\s*</p>', html, re.DOTALL)
    if not m:
        # Fallback: try to grab everything between headerheader and the next <p> or <span class="normaltext">
        m = re.search(r'<span class="headerheader">(.*?)(?=<span class="normaltext"|$)', html, re.DOTALL)
        if not m:
            return None

    header_html = m.group(1)
    # Remove the fasting sub-span and its content
    header_html = re.sub(r'<span class="header(?:no)?fast">.*?</span>', '', header_html, flags=re.DOTALL)
    # Remove all remaining tags
    text = strip_tags(header_html)
    text = clean_text(text)
    # Remove trailing period if present
    text = text.rstrip('.')
    # Clean up SUP artifacts (e.g. "30th" rendered as "30<SUP>th</SUP>")
    text = re.sub(r'(\d+)\s*(th|st|nd|rd)', r'\1\2', text)
    return text if text else None


def parse_fasting(html: str) -> str:
    """Extract fasting info from header section."""
    # Look for headerfast or headernofast class
    m = re.search(r'<span class="header(?:no)?fast">\s*(.*?)\s*</span>', html, re.DOTALL)
    if m:
        text = strip_tags(m.group(1)).strip()
        return text if text else None
    return None


def parse_saints(html: str) -> list:
    """Parse saints from the normaltext section before scripture readings.

    Each saint is on a <br>-separated line within <span class="normaltext">.
    Each line starts with <span class="typicon-{N}"> indicating importance.
    """
    # Isolate the saints normaltext block (the first one, before scripture)
    # The scripture section starts with <p class="pscriptureheader">
    scripture_pos = html.find('class="pscriptureheader"')
    if scripture_pos > 0:
        saints_html = html[:scripture_pos]
    else:
        saints_html = html

    # Find the normaltext span containing saints.
    # This span has nested spans (typicon-*, minortext), so we grab everything
    # from <span class="normaltext"> to the end of saints_html (already truncated
    # before the scripture section above). The closing </span> for normaltext is
    # the last one before the scripture <p>.
    m = re.search(r'<span class="normaltext">(.*)', saints_html, re.DOTALL)
    if not m:
        return []

    saints_block = m.group(1)
    # Strip the final closing </span> for the normaltext wrapper
    saints_block = re.sub(r'</span>\s*$', '', saints_block)

    # Split on <br> to get individual saint lines
    lines = re.split(r'<br\s*/?>\s*', saints_block)

    saints = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract typicon class
        typicon_m = re.search(r'class="typicon-([0-9o])"', line)
        typicon = typicon_m.group(1) if typicon_m else "0"

        # Check if the whole saint line is wrapped in <b>
        is_bold = bool(re.search(r'<b>', line))

        # Check if wrapped in minortext
        is_minor = 'class="minortext' in line

        # Clean up: remove typicon span, links, other markup
        # But preserve the text content
        text = line
        # Remove typicon spans (they contain just the number)
        text = re.sub(r'<span class="typicon-[0-9o]">[^<]*</span>', '', text)
        # Remove minortext span wrappers (keep content)
        text = re.sub(r'<span class="minortext\s*">', '', text)
        # Remove closing spans that were for minortext
        # (tricky — just strip all tags at this point)
        text = strip_tags(text)
        text = clean_text(text)

        if not text or len(text) < 3:
            continue

        # Remove trailing period
        text = text.rstrip('.')
        text = text.strip()

        if not text:
            continue

        importance = typicon_to_importance(typicon, is_bold, is_minor)
        saint_type = detect_saint_type(text)

        # Extract liturgical context (parenthetical at end, like "(movable holiday ...)")
        liturgical_context = None
        paren_m = re.search(r'\(([^)]*(?:movable|Celtic|British|Greek|Georgia|Arabic|Romanian|Slav)(?:[^)]*)?)\)\s*$', text, re.IGNORECASE)
        if paren_m:
            liturgical_context = paren_m.group(1).strip()
            text = text[:paren_m.start()].strip().rstrip(',').strip()

        saints.append({
            "name": text,
            "position": len(saints),
            "importance": importance,
            "type": saint_type,
            "displayRole": "tertiary",  # will be reassigned below
            "isSlava": False,
            "liturgicalContext": liturgical_context,
        })

    # Assign display roles:
    # First saint = primary; next bold/great = secondary; rest = tertiary
    if saints:
        saints[0]["displayRole"] = "primary"
        # If first saint was only "normal", promote to at least "bold"
        if saints[0]["importance"] == "normal":
            saints[0]["importance"] = "bold"

        secondary_assigned = False
        for s in saints[1:]:
            if not secondary_assigned and s["importance"] in ("great", "bold"):
                s["displayRole"] = "secondary"
                secondary_assigned = True
            else:
                s["displayRole"] = "tertiary"

        # If no secondary was assigned, give it to the second saint
        if not secondary_assigned and len(saints) > 1:
            saints[1]["displayRole"] = "secondary"

    return saints


def parse_readings(html: str) -> list:
    """Parse scripture readings from the normaltext section after scripture header.

    Readings are <a class="cal-main"> links with text like "Hebrews 10:35-11:7",
    optionally followed by a context note like "(8th Matins Gospel)" or "Sunday Before".
    """
    # Find the scripture section
    scripture_pos = html.find('class="pscriptureheader"')
    if scripture_pos < 0:
        return []

    scripture_html = html[scripture_pos:]

    # Find the normaltext span containing readings
    m = re.search(r'<span class="normaltext">(.*?)</span>', scripture_html, re.DOTALL)
    if not m:
        return []

    readings_block = m.group(1)

    # Extract each reading link + trailing context text
    readings = []
    # Pattern: <a ...href="URL"...>REFERENCE</a> optional trailing text until <br>
    for link_m in re.finditer(
        r'<a[^>]*class="cal-main"[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*(.*?)(?:<br|$)',
        readings_block, re.DOTALL
    ):
        reading_url = link_m.group(1).strip()
        ref_text = strip_tags(link_m.group(2)).strip()
        context = strip_tags(link_m.group(3)).strip()

        if not ref_text:
            continue

        ref_text = clean_text(ref_text)
        book = extract_book_name(ref_text)
        rtype = classify_reading(ref_text)

        entry = {
            "type": rtype,
            "book": book,
            "title": ref_text,
            "reference": ref_text,
        }

        if reading_url:
            entry["url"] = reading_url

        # Add context note if present
        if context:
            context = clean_text(context)
            if context:
                entry["note"] = context

        readings.append(entry)

    return readings


def fetch_reading_text(url: str) -> str:
    """Fetch full Bible text from a reading page URL.

    The reading page has verses in a table with class="ofd_los_body" paragraphs.
    Returns the concatenated verse text.
    """
    cache_key = re.sub(r'[^\w]', '_', url.split('/')[-1])
    cache_file = os.path.join(CACHE_DIR, f"reading_{cache_key}")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"    Error fetching reading {url}: {e}", file=sys.stderr)
        return ""

    # Extract verse text from ofd_los_body paragraphs in the second column
    verses = []
    # Each verse is in a table row: <td><p class="ofd_los_body" align="right"><sup>N</sup></p></td>
    # <td><p class="ofd_los_body">TEXT</p></td>
    for row_m in re.finditer(
        r'<sup>(\d+)</sup>.*?<p class="ofd_los_body">(.*?)</p>',
        html, re.DOTALL
    ):
        verse_num = row_m.group(1)
        verse_text = strip_tags(row_m.group(2)).strip()
        if verse_text:
            verses.append(f"{verse_num} {verse_text}")

    text = "\n".join(verses)

    # Cache it
    with open(cache_file, 'w') as f:
        f.write(text)

    time.sleep(0.5)
    return text


def parse_day(html: str) -> dict:
    """Parse a complete day's HTML fragment into structured data."""
    return {
        "weekLabel": parse_week_label(html),
        "fasting": parse_fasting(html),
        "saints": parse_saints(html),
        "readings": parse_readings(html),
    }


# ─── Main Pipeline ───

def run_pipeline():
    ensure_dirs()

    all_days = {}
    all_readings = {}

    print(f"=== English Pipeline: holytrinityorthodox.com {YEAR} ===", file=sys.stderr)

    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)
    day_count = 0
    readings_count = 0

    while current <= end:
        key = current.strftime("%m-%d")
        month = current.month
        day = current.day
        is_sunday = current.weekday() == 6  # Python: Monday=0, Sunday=6

        try:
            html = fetch_day(YEAR, month, day)
            parsed = parse_day(html)

            # Build saints entry
            all_days[key] = {
                "saints": parsed["saints"],
                "weekLabel": parsed["weekLabel"],
                "isSunday": is_sunday,
            }
            day_count += 1

            # Build readings entry
            if parsed["readings"]:
                all_readings[key] = parsed["readings"]
                readings_count += 1

        except Exception as e:
            print(f"  ERROR on {current}: {e}", file=sys.stderr)

        current += timedelta(days=1)

    print(f"\n  Total days parsed: {day_count}", file=sys.stderr)
    print(f"  Total days with readings: {readings_count}", file=sys.stderr)

    # Step 2: Fetch full Bible text for each reading
    print(f"\n=== Fetching reading texts ===", file=sys.stderr)
    text_count = 0
    total_readings = sum(len(r) for r in all_readings.values())
    for key, readings in all_readings.items():
        for reading in readings:
            url = reading.pop("url", None)
            if not url:
                continue
            text = fetch_reading_text(url)
            if text:
                reading["text"] = text
                text_count += 1
    print(f"  Fetched {text_count}/{total_readings} reading texts", file=sys.stderr)

    # Save saints.json
    saints_file = os.path.join(OUTPUT_DIR, "saints.json")
    with open(saints_file, 'w') as f:
        json.dump(
            {"year": YEAR, "source": "holytrinityorthodox.com", "days": all_days},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nSaved {saints_file} ({len(all_days)} days)", file=sys.stderr)

    # Save readings.json
    readings_file = os.path.join(OUTPUT_DIR, "readings.json")
    with open(readings_file, 'w') as f:
        json.dump(
            {"year": YEAR, "source": "holytrinityorthodox.com", "days": all_readings},
            f, ensure_ascii=False, indent=2,
        )
    print(f"Saved {readings_file} ({len(all_readings)} days with readings)", file=sys.stderr)


if __name__ == "__main__":
    run_pipeline()
