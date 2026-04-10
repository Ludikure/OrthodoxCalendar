#!/usr/bin/env python3
"""
Scrape saint biographies from three sources:

1. orthocal.info API (English) — JSON API with stories array
2. pravoslavno.rs (Serbian) — saint detail pages linked from monthly calendars
3. azbyka.ru (Russian) — individual saint pages linked from daily pages

Output: data/processed/{locale}/saint_bios.json

Usage:
    python3 scripts/shared/scrape_saint_bios.py [--locale en|sr|ru] [--year 2026]
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, timedelta
from html import unescape

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
HEADERS = {"User-Agent": "OrthodoxCalendarApp/1.0"}


# ─── Utilities ───────────────────────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch a URL with custom User-Agent."""
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def strip_html(html_text: str) -> str:
    """Strip HTML tags and decode entities, returning plain text."""
    # Remove <script> and <style> blocks entirely
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br> variants with newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Replace block elements with newlines
    text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = unescape(text)
    # Normalize whitespace within lines, preserve paragraph breaks
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = re.sub(r'[ \t]+', ' ', line).strip()
        if line:
            cleaned.append(line)
    text = '\n'.join(cleaned)
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def strip_accents(text: str) -> str:
    """Remove combining accent marks (used in Russian liturgical text)."""
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def save_json(data: dict, filepath: str):
    """Save dict as pretty-printed JSON."""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {filepath} ({len(data.get('days', {}))} days)", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ENGLISH — orthocal.info API
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_orthocal(year: int):
    """Scrape saint biographies from orthocal.info JSON API."""
    cache_dir = os.path.join(BASE_DIR, 'data', 'raw', 'en')
    output_dir = os.path.join(BASE_DIR, 'data', 'processed', 'en')
    ensure_dir(cache_dir)
    ensure_dir(output_dir)

    result = {"source": "orthocal.info", "year": year, "days": {}}

    current = date(year, 1, 1)
    end = date(year, 12, 31)

    print(f"=== English: orthocal.info API ({year}) ===", file=sys.stderr)

    while current <= end:
        key = current.strftime("%m-%d")
        cache_file = os.path.join(cache_dir, f"orthocal_{current.strftime('%Y-%m-%d')}.json")

        # Fetch or load from cache
        if os.path.exists(cache_file):
            with open(cache_file, encoding='utf-8') as f:
                data = json.load(f)
        else:
            url = f"https://orthocal.info/api/gregorian/{current.year}/{current.month}/{current.day}/"
            print(f"  Fetching {key} ...", file=sys.stderr)
            try:
                raw = fetch_url(url)
                data = json.loads(raw)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(raw)
                time.sleep(1)
            except Exception as e:
                print(f"  ERROR {key}: {e}", file=sys.stderr)
                current += timedelta(days=1)
                continue

        # Extract stories
        stories = data.get("stories", [])
        if stories:
            bios = []
            for story in stories:
                title = story.get("title", "").strip()
                story_html = story.get("story", "")
                text = strip_html(story_html)
                if title and text:
                    bios.append({"title": title, "text": text})
            if bios:
                result["days"][key] = bios

        if current.day == 1:
            print(f"  {current.strftime('%B')}... ({len(result['days'])} days so far)", file=sys.stderr)

        current += timedelta(days=1)

    output_file = os.path.join(output_dir, "saint_bios.json")
    save_json(result, output_file)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SERBIAN — pravoslavno.rs saint detail pages
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_saint_links_from_calendar(html: str, year: int) -> list:
    """Extract saint detail page links from a monthly calendar HTML page.

    Returns list of (mm_dd, saint_name, url) tuples.
    """
    links = []
    # Pattern: index.php?q=kalenedar&godina=YYYY&danceo=MM-DD&opis=SaintName
    for m in re.finditer(
        r'href="index\.php\?q=kalen(?:e?)dar&godina=\d+&danceo=(\d{2}-\d{2})&opis=([^"]+)"',
        html
    ):
        mm_dd = m.group(1)
        saint_name = urllib.parse.unquote(m.group(2))
        # Build properly encoded URL
        params = urllib.parse.urlencode({
            'q': 'kalenedar', 'godina': str(year),
            'danceo': mm_dd, 'opis': saint_name
        })
        full_url = f"https://www.pravoslavno.rs/index.php?{params}"
        links.append((mm_dd, saint_name, full_url))
    return links


def _clean_sr_bio(text: str) -> str:
    """Clean Serbian biography text: remove footer junk and tracking code."""
    # Remove Google Analytics / tracking scripts and CSS
    text = re.sub(r'window\.dataLayer.*?(?=\n[А-Яа-яЂђЉљЊњЋћЏџ])', '', text, flags=re.DOTALL)
    text = re.sub(r"function gtag\(\).*?(?=\n[А-Яа-яЂђЉљЊњЋћЏџ])", '', text, flags=re.DOTALL)
    text = re.sub(r"gtag\('.*?\);", '', text)
    text = re.sub(r'@media\s+screen.*?}[\s}]*', '', text, flags=re.DOTALL)
    text = re.sub(r'\.[a-zA-Z]+\s*\{[^}]*\}', '', text)
    text = re.sub(r'#[a-zA-Z]+\s*\{[^}]*\}', '', text)
    text = re.sub(r'Православни подсетник', '', text)
    text = re.sub(r'Правосл\w+', '', text, count=1)  # Remove first "Православље" header
    # Remove Google Tag Manager and other inline scripts
    text = re.sub(r'\(function\(w,d,s,l,i\).*?(?=\n[А-Яа-яЂђЉљЊњЋћЏџ]|\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'var\s+\w+\s*=.*?;', '', text)
    # Remove stray navigation text
    text = re.sub(r'\bМК\b', '', text)
    text = re.sub(r'о\.г\.', '', text)
    text = re.sub(r'Задушнице\s+\w+', '', text)  # "Задушнице зимске" etc navigation
    # Remove any remaining lines that look like code or CSS
    lines = text.split('\n')
    lines = [l for l in lines if not re.match(r'^\s*[\{\}()\[\];]', l.strip()) and
             not re.match(r'^\s*(function|var |let |const |if\s*\(|for\s*\(|document\.|window\.)', l.strip()) and
             not re.match(r'^\s*\.[a-zA-Z]', l.strip()) and  # CSS class rules
             not re.match(r'^\s*#[a-zA-Z]', l.strip()) and   # CSS ID rules
             not re.match(r'^\s*display\s*:', l.strip()) and  # CSS properties
             not re.match(r'^\s*@media', l.strip())]
    text = '\n'.join(lines)
    # Remove "Охридски пролог" and everything after it (often a section marker)
    text = re.sub(r'Охридски пролог.*', '', text, flags=re.DOTALL)
    # Remove JavaScript junk
    text = re.sub(r'document\.addEventListener.*', '', text, flags=re.DOTALL)
    # Remove copyright
    text = re.sub(r'©\s*Микро књига.*', '', text, flags=re.DOTALL)
    # Remove common footer patterns
    text = re.sub(r'▲.*', '', text, flags=re.DOTALL)
    # Remove trailing whitespace
    text = text.strip()
    return text


def scrape_pravoslavno(year: int):
    """Scrape saint biographies from pravoslavno.rs detail pages."""
    cache_dir = os.path.join(BASE_DIR, 'data', 'raw', 'sr')
    output_dir = os.path.join(BASE_DIR, 'data', 'processed', 'sr')
    ensure_dir(cache_dir)
    ensure_dir(output_dir)

    result = {"source": "pravoslavno.rs", "year": year, "days": {}}

    print(f"=== Serbian: pravoslavno.rs ({year}) ===", file=sys.stderr)

    # Step 1: Collect all saint links from cached monthly calendar pages
    all_links = {}  # mm_dd -> [(saint_name, url), ...]
    for month in range(1, 13):
        cal_file = os.path.join(cache_dir, f"pravoslavno_{year}_{month:02d}.html")
        if not os.path.exists(cal_file):
            print(f"  WARNING: Calendar page missing: {cal_file}", file=sys.stderr)
            # Try fetching it
            url = f"https://www.pravoslavno.rs/index.php?q=kalendar&godina={year}&mesec={month:02d}"
            print(f"  Fetching calendar page: {url}", file=sys.stderr)
            try:
                html = fetch_url(url)
                with open(cal_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                time.sleep(1)
            except Exception as e:
                print(f"  ERROR fetching calendar: {e}", file=sys.stderr)
                continue

        with open(cal_file, encoding='utf-8') as f:
            html = f.read()

        links = _extract_saint_links_from_calendar(html, year)
        for mm_dd, saint_name, url in links:
            if mm_dd not in all_links:
                all_links[mm_dd] = []
            # Avoid duplicates
            if not any(name == saint_name for name, _ in all_links[mm_dd]):
                all_links[mm_dd].append((saint_name, url))

        print(f"  Month {month:02d}: {len(links)} saint links found", file=sys.stderr)

    total_links = sum(len(v) for v in all_links.values())
    print(f"  Total: {len(all_links)} days, {total_links} saint links", file=sys.stderr)

    # Step 2: Fetch one page per day (all saint links for same day point to same page)
    fetched = 0
    for mm_dd in sorted(all_links.keys()):
        saints_for_day = []
        # Just use the first link — all saints for a day share the same page
        saint_name, url = all_links[mm_dd][0]
        cache_file = os.path.join(cache_dir, f"saint_{mm_dd}_day.html")

        # Try to reuse any existing cached saint page for this day
        if not os.path.exists(cache_file):
            existing = [f for f in os.listdir(cache_dir) if f.startswith(f"saint_{mm_dd}_") and f.endswith('.html')]
            if existing:
                os.rename(os.path.join(cache_dir, existing[0]), cache_file)

        if os.path.exists(cache_file):
            with open(cache_file, encoding='utf-8') as f:
                html = f.read()
        else:
            print(f"  Fetching {mm_dd}...", file=sys.stderr)
            try:
                html = fetch_url(url)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                fetched += 1
                time.sleep(1)
            except Exception as e:
                print(f"  ERROR {mm_dd}: {e}", file=sys.stderr)
                continue

        # Extract biography: strip HTML, clean junk
        bio_text = strip_html(html)
        bio_text = _clean_sr_bio(bio_text)

        # Remove header/navigation before the saint entry
        date_header = re.search(r'\d{1,2}\.\s+\w+\s+о\.г\.', bio_text)
        if date_header:
            bio_text = bio_text[date_header.end():].strip()

        # Remove month title line (ЈАНУАР – ...)
        SR_MONTHS = ['ЈАНУАР', 'ФЕБРУАР', 'МАРТ', 'АПРИЛ', 'МАЈ', 'ЈУН',
                     'ЈУЛ', 'АВГУСТ', 'СЕПТЕМБАР', 'ОКТОБАР', 'НОВЕМБАР', 'ДЕЦЕМБАР']
        lines = bio_text.split('\n')
        start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and len(stripped) > 30 and not any(stripped.startswith(m) for m in SR_MONTHS):
                start = i
                break
        bio_text = '\n'.join(lines[start:]).strip()

        # Build title from all saint names for this day
        title = '; '.join(name for name, _ in all_links[mm_dd])

        if bio_text and len(bio_text) > 20:
            saints_for_day.append({
                "title": title,
                "text": bio_text,
            })

        if saints_for_day:
            result["days"][mm_dd] = saints_for_day

        # Progress
        if mm_dd.endswith("-01"):
            month_name = mm_dd[:2]
            print(f"  Month {month_name} done ({len(result['days'])} days so far, {fetched} fetched)", file=sys.stderr)

    output_file = os.path.join(output_dir, "saint_bios.json")
    save_json(result, output_file)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RUSSIAN — azbyka.ru saint pages
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_saint_links_from_azbyka(html: str) -> list:
    """Extract saint detail page links from an azbyka.ru daily page.

    Returns list of (saint_name, url) tuples.
    """
    saints = []

    # Saint links are inside <li class="ideograph-N"> elements
    # Format: <a href='https://azbyka.ru/days/sv-NAME'>Saint Name</a>
    for m in re.finditer(
        r'<li\s+class="ideograph-\d+">(.*?)</li>',
        html, re.DOTALL
    ):
        li_html = m.group(1)

        # Find saint links (azbyka.ru/days/sv-... or azbyka.ru/days/prazdnik-...)
        link_match = re.search(
            r'<a\s+href=[\'"]?(https?://azbyka\.ru/days/(?:sv|prazdnik|svv)-[^"\'>\s]+)[\'"]?[^>]*>(.*?)</a>',
            li_html, re.DOTALL
        )
        if link_match:
            url = link_match.group(1)
            name_html = link_match.group(2)
            # Clean name: remove secondary-content spans, images, strip HTML
            name_html = re.sub(r'<span[^>]*class=[\'"]?secondary-content[^>]*>.*?</span>', '', name_html, flags=re.DOTALL)
            name_html = re.sub(r'<img[^>]*>', '', name_html)
            name = strip_accents(strip_html(name_html)).strip()
            if name:
                saints.append((name, url))

    return saints


def _extract_azbyka_bio(html: str) -> str:
    """Extract biography text from an azbyka.ru saint detail page.

    The page has various sections. The biography is typically the main text
    content after the icon/image and "Дни памяти" section.
    """
    # Strategy 1: Look for the main content area with biography text
    # azbyka.ru saint pages typically have content in a main article/post div

    # Try to find content after "Жития" or biography heading
    bio_text = ""

    # Look for the main text content div
    # Common pattern: <div class="post_content"> or <div class="entry-content">
    content_match = re.search(
        r'<div\s+class="[^"]*(?:post_content|entry-content|content-body|text\s)[^"]*"[^>]*>(.*?)</div>\s*(?:</div>|<div\s+class="[^"]*(?:sidebar|footer|related))',
        html, re.DOTALL
    )

    if not content_match:
        # Try a broader approach: find text between "Дни памяти" and next major section
        # or just grab all paragraph text from the main area
        days_match = re.search(r'(?:Дни памяти|Дни пам[яь]ти)</h', html)
        if days_match:
            # Get everything after "Дни памяти" section
            after_days = html[days_match.end():]
            # Skip the dates section, find where biography text starts
            # Look for first <p> after the dates
            p_blocks = re.findall(r'<p[^>]*>(.*?)</p>', after_days, re.DOTALL)
            bio_parts = []
            for p in p_blocks:
                text = strip_accents(strip_html(p)).strip()
                # Skip very short paragraphs or navigation items
                if text and len(text) > 30:
                    bio_parts.append(text)
                # Stop if we hit footer-like content
                if any(marker in text for marker in ['Источник', 'Литература', 'Библиография', 'Примечани']):
                    break
            bio_text = '\n\n'.join(bio_parts)
        else:
            # Fallback: grab all substantial <p> content
            p_blocks = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            bio_parts = []
            in_bio = False
            for p in p_blocks:
                text = strip_accents(strip_html(p)).strip()
                # Start capturing when we see substantial text
                if not in_bio and text and len(text) > 100:
                    in_bio = True
                if in_bio and text and len(text) > 20:
                    bio_parts.append(text)
                    # Limit to reasonable length
                    if len('\n'.join(bio_parts)) > 10000:
                        break
                # Stop at footer markers
                if any(marker in text for marker in ['Источник', 'Литература', 'Библиография']):
                    break
            bio_text = '\n\n'.join(bio_parts)
    else:
        bio_text = strip_accents(strip_html(content_match.group(1)))

    return bio_text.strip()


def scrape_azbyka(year: int):
    """Scrape saint biographies from azbyka.ru saint detail pages."""
    cache_dir = os.path.join(BASE_DIR, 'data', 'raw', 'ru')
    output_dir = os.path.join(BASE_DIR, 'data', 'processed', 'ru')
    ensure_dir(cache_dir)
    ensure_dir(output_dir)

    result = {"source": "azbyka.ru", "year": year, "days": {}}

    print(f"=== Russian: azbyka.ru ({year}) ===", file=sys.stderr)

    current = date(year, 1, 1)
    end = date(year, 12, 31)

    while current <= end:
        key = current.strftime("%m-%d")
        date_str = current.strftime("%Y-%m-%d")

        # Step 1: Load/fetch the daily page to get saint links
        day_cache = os.path.join(cache_dir, f"azbyka_{date_str}.html")
        if os.path.exists(day_cache):
            with open(day_cache, encoding='utf-8') as f:
                day_html = f.read()
        else:
            url = f"https://azbyka.ru/days/{date_str}"
            print(f"  Fetching day page {key}...", file=sys.stderr)
            try:
                day_html = fetch_url(url)
                with open(day_cache, 'w', encoding='utf-8') as f:
                    f.write(day_html)
                time.sleep(1)
            except Exception as e:
                print(f"  ERROR fetching day page {key}: {e}", file=sys.stderr)
                current += timedelta(days=1)
                continue

        # Step 2: Extract saint links from daily page
        saint_links = _extract_saint_links_from_azbyka(day_html)

        # Step 3: Fetch each saint's detail page and extract biography
        bios_for_day = []
        for saint_name, saint_url in saint_links:
            # Cache file for saint page
            # Extract slug from URL
            slug = saint_url.rstrip('/').split('/')[-1]
            saint_cache = os.path.join(cache_dir, f"saint_{slug}.html")

            if os.path.exists(saint_cache):
                with open(saint_cache, encoding='utf-8') as f:
                    saint_html = f.read()
            else:
                print(f"    Fetching saint: {saint_name[:50]}...", file=sys.stderr)
                try:
                    saint_html = fetch_url(saint_url)
                    with open(saint_cache, 'w', encoding='utf-8') as f:
                        f.write(saint_html)
                    time.sleep(1)
                except Exception as e:
                    print(f"    ERROR {saint_name[:50]}: {e}", file=sys.stderr)
                    continue

            # Extract biography
            bio_text = _extract_azbyka_bio(saint_html)
            if bio_text and len(bio_text) > 50:
                bios_for_day.append({
                    "title": saint_name,
                    "text": bio_text,
                })

        if bios_for_day:
            result["days"][key] = bios_for_day

        # Progress
        if current.day == 1:
            print(f"  {current.strftime('%B')}... ({len(result['days'])} days so far)", file=sys.stderr)

        current += timedelta(days=1)

    output_file = os.path.join(output_dir, "saint_bios.json")
    save_json(result, output_file)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Scrape saint biographies from Orthodox calendar sources")
    parser.add_argument("--locale", choices=["en", "sr", "ru"],
                        help="Scrape a specific locale (default: all three)")
    parser.add_argument("--year", type=int, default=2026,
                        help="Year to scrape (default: 2026)")
    args = parser.parse_args()

    locales = [args.locale] if args.locale else ["en", "sr", "ru"]

    for locale in locales:
        if locale == "en":
            scrape_orthocal(args.year)
        elif locale == "sr":
            scrape_pravoslavno(args.year)
        elif locale == "ru":
            scrape_azbyka(args.year)

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
