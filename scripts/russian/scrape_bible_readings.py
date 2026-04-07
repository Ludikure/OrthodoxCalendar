#!/usr/bin/env python3
"""
Scrape Russian Bible readings from azbyka.ru.

1. Parse cached azbyka day pages for bibref links + context
2. Fetch Bible text from azbyka.ru/biblia/?Book.Chapter:Verses
3. Build lectionary mapped by pascha distance + Julian date

Output: data/processed/ru/lectionary_complete.json
"""

import json, os, re, sys, time, urllib.request
from datetime import date, timedelta
from html import unescape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from paschalion import Paschalion

YEAR = 2026
JULIAN_OFFSET = 13
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'ru')
BIBLE_CACHE = os.path.join(CACHE_DIR, 'bible')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'ru')

os.makedirs(BIBLE_CACHE, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_bible_page(book_code, chapter):
    """Fetch and cache a Bible chapter page."""
    cache_file = os.path.join(BIBLE_CACHE, f"{book_code}_{chapter}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"https://azbyka.ru/biblia/?{book_code}.{chapter}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        with open(cache_file, 'w') as f:
            f.write(html)
        time.sleep(1.5)
        return html
    except Exception as e:
        print(f"    Bible fetch error {book_code}.{chapter}: {e}", file=sys.stderr)
        return ""


def extract_verses(html, chapter, start_verse, end_verse, extra_verses=None):
    """Extract verse text for a range from a Bible chapter page."""
    # Find ALL verse divs — the actual text is in the second set
    # First set has cross-references, second has actual text
    all_verses = re.findall(
        r'<div[^>]*data-lang="r"[^>]*data-chapter="(\d+)"[^>]*data-line="(\d+)"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )

    # Group by (chapter, verse) — take the LAST occurrence (actual text, not cross-refs)
    verse_map = {}
    for ch, v, text in all_verses:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        clean = re.sub(r'^\[Зач\.\s*\d+\.\]\s*', '', clean)  # Remove зачало markers
        clean = re.sub(r'^\]\s*', '', clean)
        clean = re.sub(r'\s+', ' ', unescape(clean)).strip()
        if clean and len(clean) > 3 and not re.match(r'^\d+:\d+', clean):
            verse_map[(int(ch), int(v))] = clean

    # Extract requested range
    result = []
    for v in range(start_verse, end_verse + 1):
        text = verse_map.get((chapter, v))
        if text:
            result.append(f"{v}. {text}")

    # Extra individual verses (e.g., verse 56 in "39-49,56")
    if extra_verses:
        for v in extra_verses:
            text = verse_map.get((chapter, v))
            if text:
                result.append(f"{v}. {text}")

    return "\n".join(result)


def parse_bibref_url(url):
    """Parse azbyka bibref URL into book code, chapter, verse range."""
    # URL format: https://azbyka.ru/biblia/?Lk.1:39-49,56
    match = re.search(r'\?(\w+)\.(\d+):(.+)$', url)
    if not match:
        return None
    book = match.group(1)
    chapter = int(match.group(2))
    verse_str = match.group(3)

    # Parse verse range: "39-49,56" or "11-18" or "1-12"
    parts = verse_str.split(',')
    start_verse = None
    end_verse = None
    extra_verses = []

    for part in parts:
        part = part.strip()
        if '-' in part:
            # Check for cross-chapter range (24:36-26:2)
            range_match = re.match(r'(\d+)(?::(\d+))?-(\d+)(?::(\d+))?', part)
            if range_match:
                s = int(range_match.group(1))
                if range_match.group(2):
                    # Cross-chapter: just use first chapter for now
                    start_verse = int(range_match.group(2)) if range_match.group(2) else s
                    end_chapter = int(range_match.group(3)) if range_match.group(3) else chapter
                    end_verse = int(range_match.group(4)) if range_match.group(4) else int(range_match.group(3))
                else:
                    start_verse = s
                    end_verse = int(range_match.group(3))
        else:
            if part.isdigit():
                if start_verse is None:
                    start_verse = int(part)
                    end_verse = int(part)
                else:
                    extra_verses.append(int(part))

    if start_verse is None:
        return None

    return {
        "book": book,
        "chapter": chapter,
        "start": start_verse,
        "end": end_verse or start_verse,
        "extra": extra_verses,
    }


def parse_day_readings(html):
    """Extract readings from an azbyka day page."""
    readings_div = re.search(r'class="readings-text"[^>]*>(.*?)</div>', html, re.DOTALL)
    if not readings_div:
        return []

    content = readings_div.group(1)

    # Find all bibref links with surrounding context
    readings = []

    # Get the full text to parse service labels
    full_text = re.sub(r'<[^>]+>', ' ', content)
    full_text = re.sub(r'\s+', ' ', unescape(full_text)).strip()

    for m in re.finditer(r'<a[^>]*class="bibref"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', content, re.DOTALL):
        href = m.group(1)
        display = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        display = unescape(display).replace('\u2013', '–')

        # Find service context before this link
        before = content[:m.start()]
        service = None
        for svc in ["Утр", "Лит", "На 6-м часе", "Веч", "На 1-м часе", "На 3-м часе", "На 9-м часе"]:
            if svc in re.sub(r'<[^>]+>', '', before[-80:]):
                service = svc

        # Find зачало
        zachalo = None
        zach_match = re.search(r'зач\.\s*(\d+)', re.sub(r'<[^>]+>', '', content[m.end():m.end()+30]))
        if zach_match:
            zachalo = int(zach_match.group(1))

        # Classify
        rtype = "gospel"
        gospel_books = ["Mt", "Mk", "Lk", "Jn"]
        parsed = parse_bibref_url(href)
        if parsed:
            if parsed["book"] not in gospel_books:
                if any(b in parsed["book"] for b in ["Gen", "Ex", "Lev", "Num", "Deut", "Is", "Jer", "Ez", "Dan", "Ps", "Prov", "Job", "Wis"]):
                    rtype = "ot"
                else:
                    rtype = "apostol"

        readings.append({
            "display": display,
            "href": href,
            "type": rtype,
            "service": service,
            "zachalo": zachalo,
            "parsed": parsed,
        })

    return readings


def main():
    pasch = Paschalion(YEAR)
    by_pdist = {}
    by_julian = {}
    total_days = 0
    total_with_text = 0

    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)

    # Collect all unique Bible pages needed
    all_bibrefs = {}  # href -> parsed info
    day_readings_map = {}  # "MM-DD" -> list of reading infos

    print("Phase 1: Parsing day pages for reading references...", file=sys.stderr)
    while current <= end:
        if current.day == 1:
            print(f"  {current.strftime('%B')}...", file=sys.stderr)

        ds = current.strftime("%Y-%m-%d")
        cache_file = os.path.join(CACHE_DIR, f"azbyka_{ds}.html")
        if not os.path.exists(cache_file):
            current += timedelta(days=1)
            continue

        with open(cache_file) as f:
            html = f.read()

        readings = parse_day_readings(html)
        if readings:
            key = current.strftime("%m-%d")
            day_readings_map[key] = readings
            total_days += 1
            for r in readings:
                if r["href"] not in all_bibrefs and r["parsed"]:
                    all_bibrefs[r["href"]] = r["parsed"]

        current += timedelta(days=1)

    print(f"  {total_days} days with readings, {len(all_bibrefs)} unique Bible refs", file=sys.stderr)

    # Phase 2: Fetch Bible pages and extract text
    print(f"\nPhase 2: Fetching {len(all_bibrefs)} Bible passages...", file=sys.stderr)
    bible_texts = {}  # href -> extracted text
    fetched = 0

    for href, parsed in all_bibrefs.items():
        html = fetch_bible_page(parsed["book"], parsed["chapter"])
        if html:
            text = extract_verses(html, parsed["chapter"], parsed["start"], parsed["end"], parsed.get("extra"))
            if text:
                bible_texts[href] = text
                fetched += 1
        if fetched % 20 == 0 and fetched > 0:
            print(f"  {fetched}/{len(all_bibrefs)}...", file=sys.stderr)

    print(f"  Extracted text for {len(bible_texts)}/{len(all_bibrefs)} refs", file=sys.stderr)

    # Phase 3: Build lectionary
    print("\nPhase 3: Building lectionary...", file=sys.stderr)
    current = date(YEAR, 1, 1)

    while current <= end:
        key = current.strftime("%m-%d")
        if key not in day_readings_map:
            current += timedelta(days=1)
            continue

        pdist = pasch.pascha_distance(current)
        julian = current - timedelta(days=JULIAN_OFFSET)
        jkey = f"{julian.month:02d}-{julian.day:02d}"

        day_readings = []
        has_text = False

        for r in day_readings_map[key]:
            reading = {
                "title": r["display"],
                "type": r["type"],
            }
            if r["service"]:
                reading["service"] = r["service"]
            if r["zachalo"]:
                reading["zachalo"] = r["zachalo"]

            text = bible_texts.get(r["href"])
            if text:
                reading["text"] = text
                has_text = True

            day_readings.append(reading)

        if day_readings:
            by_pdist[str(pdist)] = day_readings
            by_julian[jkey] = day_readings
            if has_text:
                total_with_text += 1

        current += timedelta(days=1)

    lectionary = {
        "source": "azbyka.ru + azbyka.ru/biblia",
        "byPaschaDistance": by_pdist,
        "byJulianDate": by_julian,
    }

    output_file = os.path.join(OUTPUT_DIR, "lectionary_complete.json")
    with open(output_file, 'w') as f:
        json.dump(lectionary, f, ensure_ascii=False, indent=2)

    print(f"\nDone:", file=sys.stderr)
    print(f"  Days with readings: {total_days}", file=sys.stderr)
    print(f"  Days with full text: {total_with_text}", file=sys.stderr)
    print(f"  By pascha distance: {len(by_pdist)}", file=sys.stderr)
    print(f"  By Julian date: {len(by_julian)}", file=sys.stderr)
    print(f"  Saved: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
