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
FALLBACK_YEAR = 2025  # Year with full readings for pdist-based fallback
JULIAN_OFFSET = 13
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'ru')
BIBLE_CACHE = os.path.join(CACHE_DIR, 'bible')
FALLBACK_CACHE = os.path.join(CACHE_DIR, 'fallback_2025')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'ru')

os.makedirs(BIBLE_CACHE, exist_ok=True)
os.makedirs(FALLBACK_CACHE, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_fallback_day_page(greg_date_2025):
    """Fetch and cache an azbyka day page from the fallback year (2025)."""
    ds = greg_date_2025.strftime("%Y-%m-%d")
    cache_file = os.path.join(FALLBACK_CACHE, f"azbyka_{ds}.html")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    url = f"https://azbyka.ru/days/{ds}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        with open(cache_file, 'w') as f:
            f.write(html)
        time.sleep(1.5)
        return html
    except Exception as e:
        print(f"    Fallback fetch error {ds}: {e}", file=sys.stderr)
        return ""


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


def extract_chapter_verse_map(html):
    """Return {verse_number: text} for a single Bible chapter page."""
    all_verses = re.findall(
        r'<div[^>]*data-lang="r"[^>]*data-chapter="(\d+)"[^>]*data-line="(\d+)"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    verse_map = {}
    for ch, v, text in all_verses:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        clean = re.sub(r'^\[Зач\.\s*\d+\.\]\s*', '', clean)  # Remove зачало markers
        clean = re.sub(r'^\]\s*', '', clean)
        clean = re.sub(r'\s+', ' ', unescape(clean)).strip()
        if clean and len(clean) > 3 and not re.match(r'^\d+:\d+', clean):
            verse_map[int(v)] = clean  # data-line is the verse number
    return verse_map


def assemble_segments(parsed, get_chapter_map):
    """Assemble verse text for parsed segments, spanning chapters as needed.

    get_chapter_map(book, chapter) -> {verse: text}. Returns "N. text" lines.
    """
    result = []
    for ch, vstart, vend in parsed["segments"]:
        cmap = get_chapter_map(parsed["book"], ch)
        if not cmap:
            continue
        last = max(cmap) if cmap else vend
        for v in range(vstart, min(vend, last) + 1):
            text = cmap.get(v)
            if text:
                result.append(f"{v}. {text}")
    return "\n".join(result)


def parse_bibref_url(url):
    """Parse an azbyka bibref URL into a list of (chapter, start, end) segments.

    URL format: https://azbyka.ru/biblia/?Book.Chapter:Verses , where Verses is a
    comma list of ranges. A range may cross chapters, and a chapter stated with
    "N:" sets the context for the bare ranges that follow:
        "39-49,56"        -> [(C,39,49), (C,56,56)]            (C = leading chapter)
        "10:35-11:7"      -> [(10,35,END), (11,1,7)]           (cross-chapter)
        "6:8-15,7:1-5,47-60" -> [(6,8,15), (7,1,5), (7,47,60)] (chapter context)
    END (9999) is clamped to the chapter's real last verse at assembly time.
    """
    match = re.search(r'\?(\w+)\.(\d+):(.+)$', url)
    if not match:
        return None
    book = match.group(1)
    lead_chapter = int(match.group(2))

    segments = []
    cur_chapter = lead_chapter
    for part in match.group(3).split(','):
        part = part.strip()
        # forms: v | v-v | ch:v | ch:v-v | v-ch:v | ch:v-ch:v
        m = re.match(r'(?:(\d+):)?(\d+)(?:-(?:(\d+):)?(\d+))?$', part)
        if not m:
            continue
        sch = int(m.group(1)) if m.group(1) else cur_chapter
        sv = int(m.group(2))
        ech = int(m.group(3)) if m.group(3) else sch
        ev = int(m.group(4)) if m.group(4) else sv
        cur_chapter = ech  # bare ranges that follow use this chapter
        if sch == ech:
            segments.append((sch, sv, ev))
        else:
            segments.append((sch, sv, 9999))            # start chapter: to its end
            for c in range(sch + 1, ech):
                segments.append((c, 1, 9999))            # whole middle chapters
            segments.append((ech, 1, ev))                # end chapter: from verse 1

    if not segments:
        return None
    return {"book": book, "segments": segments}


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
    pasch_fallback = Paschalion(FALLBACK_YEAR)
    by_pdist = {}
    by_julian = {}
    total_days = 0
    total_with_text = 0

    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)

    # Collect all unique Bible pages needed
    all_bibrefs = {}  # href -> parsed info
    day_readings_map = {}  # "MM-DD" -> list of reading infos

    print("Phase 1: Parsing cached 2026 day pages for reading references...", file=sys.stderr)
    missing_dates = []  # dates without inline readings
    while current <= end:
        if current.day == 1:
            print(f"  {current.strftime('%B')}...", file=sys.stderr)

        ds = current.strftime("%Y-%m-%d")
        cache_file = os.path.join(CACHE_DIR, f"azbyka_{ds}.html")
        if not os.path.exists(cache_file):
            missing_dates.append(current)
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
        else:
            missing_dates.append(current)

        current += timedelta(days=1)

    print(f"  {total_days} days with readings from 2026 cache, {len(all_bibrefs)} unique Bible refs", file=sys.stderr)
    print(f"  {len(missing_dates)} dates without inline readings", file=sys.stderr)

    # Phase 1b: Fetch fallback pages from 2025 for missing dates
    if missing_dates:
        print(f"\nPhase 1b: Fetching {len(missing_dates)} fallback pages from {FALLBACK_YEAR}...", file=sys.stderr)
        fallback_found = 0
        still_missing = []
        for i, dt2026 in enumerate(missing_dates):
            pdist = pasch.pascha_distance(dt2026)
            # Find equivalent date in fallback year by pascha distance
            dt_fallback = pasch_fallback.pascha + timedelta(days=pdist)
            # Only use if the fallback date is in the same year
            if dt_fallback.year != FALLBACK_YEAR:
                still_missing.append(dt2026)
                continue

            html = fetch_fallback_day_page(dt_fallback)
            if not html:
                still_missing.append(dt2026)
                continue

            readings = parse_day_readings(html)
            if readings:
                key = dt2026.strftime("%m-%d")
                day_readings_map[key] = readings
                total_days += 1
                fallback_found += 1
                for r in readings:
                    if r["href"] not in all_bibrefs and r["parsed"]:
                        all_bibrefs[r["href"]] = r["parsed"]
            else:
                still_missing.append(dt2026)

            if (i + 1) % 30 == 0:
                print(f"  {i+1}/{len(missing_dates)} checked, {fallback_found} found...", file=sys.stderr)

        print(f"  Found {fallback_found} additional days from {FALLBACK_YEAR} pdist fallback", file=sys.stderr)

        # Phase 1c: For dates still missing (e.g. late Dec where pdist maps to next year),
        # try same Gregorian date in the fallback year (fixed-calendar readings)
        if still_missing:
            print(f"\nPhase 1c: Trying {len(still_missing)} dates by same Gregorian date in {FALLBACK_YEAR}...", file=sys.stderr)
            julian_found = 0
            for dt2026 in still_missing:
                # Use same month-day in the fallback year
                try:
                    dt_fallback = date(FALLBACK_YEAR, dt2026.month, dt2026.day)
                except ValueError:
                    continue  # e.g. Feb 29 in non-leap year

                html = fetch_fallback_day_page(dt_fallback)
                if not html:
                    continue

                readings = parse_day_readings(html)
                if readings:
                    key = dt2026.strftime("%m-%d")
                    day_readings_map[key] = readings
                    total_days += 1
                    julian_found += 1
                    for r in readings:
                        if r["href"] not in all_bibrefs and r["parsed"]:
                            all_bibrefs[r["href"]] = r["parsed"]

            print(f"  Found {julian_found} additional days from {FALLBACK_YEAR} same-date fallback", file=sys.stderr)

    print(f"  Total: {total_days} days with readings, {len(all_bibrefs)} unique Bible refs", file=sys.stderr)

    # Phase 2: Fetch Bible pages and extract text (one page per chapter, cached;
    # a reading may span several chapters).
    print(f"\nPhase 2: Fetching Bible passages for {len(all_bibrefs)} refs...", file=sys.stderr)
    chapter_cache = {}

    def get_chapter_map(book, chapter):
        ckey = (book, chapter)
        if ckey not in chapter_cache:
            html = fetch_bible_page(book, chapter)
            chapter_cache[ckey] = extract_chapter_verse_map(html) if html else {}
        return chapter_cache[ckey]

    bible_texts = {}  # href -> extracted text
    for i, (href, parsed) in enumerate(all_bibrefs.items()):
        text = assemble_segments(parsed, get_chapter_map)
        if text:
            bible_texts[href] = text
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(all_bibrefs)}...", file=sys.stderr)

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
