#!/usr/bin/env python3
"""
Scrape the full Serbian Bible (Свето писмо) from pravoslavno.rs.

Same site and translation already used for the daily readings (Daničić OT +
Holy Synod NT), so the text is identical in style to the scraped day-readings —
this exists to FILL gaps where the day-page scrape produced no usable text for a
reading the lectionary engine knows about (e.g. post-Pentecost weekday Apostle/
Gospel readings).

Source URL pattern:
    ?q=svetopismo&knjiga={book}&pog={chapter}

Book numbering (from the site index):
    1-39   Old Testament (Genesis … Malachi)
    40-66  New Testament (Matthew=40 … Acts=44 … Hebrews=58 … Revelation=66)
    71-84  Deuterocanon — mostly "у припреми" (skipped; covered by day scrape)

Output: data/processed/sr/bible.json
    { "books": { "<knjiga>": {"title": str, "chapters": {"<ch>": {"<v>": text}}}}}

Usage:
    python scrape_bible.py            # full Bible (books 1-66)
    python scrape_bible.py 40 66      # only a knjiga range (e.g. NT)
    python scrape_bible.py 45         # a single book (e.g. Romans) — for testing
"""

import json
import os
import re
import sys
import time
import urllib.request
from html import unescape

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'sr', 'bible')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'sr')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'bible.json')

BASE = "https://www.pravoslavno.rs/index.php?q=svetopismo&knjiga={k}&pog={p}"

# Protocanonical books only (1-66). Deuterocanon (71-84) is unpublished on the
# site and already covered by the day-readings scrape.
FIRST_BOOK, LAST_BOOK = 1, 66

# Standard chapter counts (long OT books only render a prev/next link, so the
# count can't be read from page nav). Order matches the site's knjiga numbering:
# OT 1-39, NT 40-66 (Matthew=40 … Hebrews=58, James=59 … Jude=65, Revelation=66).
CHAPTER_COUNTS = {
    1: 50, 2: 40, 3: 27, 4: 36, 5: 34, 6: 24, 7: 21, 8: 4, 9: 31, 10: 24,
    11: 22, 12: 25, 13: 29, 14: 36, 15: 10, 16: 13, 17: 10, 18: 42, 19: 150,
    20: 31, 21: 12, 22: 8, 23: 66, 24: 52, 25: 5, 26: 48, 27: 12, 28: 14,
    29: 3, 30: 9, 31: 1, 32: 4, 33: 7, 34: 3, 35: 3, 36: 3, 37: 2, 38: 14,
    39: 4,
    40: 28, 41: 16, 42: 24, 43: 21, 44: 28, 45: 16, 46: 16, 47: 13, 48: 6,
    49: 6, 50: 4, 51: 4, 52: 5, 53: 3, 54: 6, 55: 4, 56: 3, 57: 1, 58: 13,
    59: 5, 60: 5, 61: 3, 62: 5, 63: 1, 64: 1, 65: 1, 66: 22,
}


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch(k: int, p: int) -> str:
    cache = os.path.join(CACHE_DIR, f"{k}_{p}.html")
    if os.path.exists(cache) and os.path.getsize(cache) > 500:
        with open(cache, encoding='utf-8', errors='replace') as f:
            return f.read()
    url = BASE.format(k=k, p=p)
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
    except Exception as e:
        print(f"  ERROR fetching knjiga={k} pog={p}: {e}", file=sys.stderr)
        return ""
    with open(cache, 'w', encoding='utf-8') as f:
        f.write(html)
    time.sleep(0.8)  # be polite
    return html


def clean(text: str) -> str:
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)          # strip any nested tags
    text = re.sub(r'\(Зачало[^)]*\)\.?', '', text)  # drop zachalo markers
    text = re.sub(r'\s+', ' ', text)
    return text.strip(' .„""\'')


def parse_title(html: str) -> str:
    # Book title heading: red, size=+1 (chapter heading is red WITHOUT size=+1).
    m = re.search(r'<font color=#ff0000 size=\+1>(.*?)</font>', html, re.DOTALL)
    return clean(m.group(1)) if m else ""


def parse_chapter_count(html: str, k: int) -> int:
    # Page 1 lists every chapter as ?...&pog=N links; the max is the count.
    nums = [int(n) for n in re.findall(rf'knjiga={k}&pog=(\d+)', html)]
    return max(nums) if nums else 1


def parse_verses(html: str) -> dict:
    """Extract {verse_number: text} for a chapter page.

    Verses render as `N. text`, one per line (separated by newlines or <br>),
    starting after the red `Поглавље N.` heading and ending at the page footer /
    next-chapter navigation. Inline `(Зачало N).` markers are stripped. Some
    chapters wrap verse text in <b> (e.g. red-letter speech); tags are removed.
    """
    m = re.search(r'Поглавље\s*\d+\.\s*</font>', html)
    region = html[m.end():] if m else html
    for marker in ('Поглавље:', '© Микро', 'document.', 'иди на врх',
                   '<script', 'addEventListener'):
        idx = region.find(marker)
        if idx != -1:
            region = region[:idx]
    region = re.sub(r'<br\s*/?>', '\n', region, flags=re.IGNORECASE)
    region = re.sub(r'<[^>]+>', ' ', region)
    region = re.sub(r'\(Зачало[^)]*\)\.?', ' ', region)
    region = unescape(region)

    verses = {}
    for line in region.split('\n'):
        lm = re.match(r'\s*(\d+)\.\s+(.+)', line)
        if not lm:
            continue
        num = int(lm.group(1))
        text = re.sub(r'\s+', ' ', lm.group(2)).strip(' .„""\'')
        if text and num not in verses:
            verses[num] = text
    return verses


def scrape_book(k: int) -> dict:
    html1 = fetch(k, 1)
    if not html1:
        return {}
    title = parse_title(html1)
    if not title:
        print(f"  knjiga={k}: no title (skipped — likely unpublished)", file=sys.stderr)
        return {}
    n_chapters = CHAPTER_COUNTS.get(k) or parse_chapter_count(html1, k)
    chapters = {}
    for p in range(1, n_chapters + 1):
        html = html1 if p == 1 else fetch(k, p)
        verses = parse_verses(html)
        if not verses:
            break  # reached end of book (or unpublished) — stop early
        chapters[str(p)] = verses
    total_v = sum(len(v) for v in chapters.values())
    print(f"  knjiga={k:2} {title[:40]:40} — {len(chapters)} ch, {total_v} verses", file=sys.stderr)
    return {"title": title, "chapters": chapters}


def main():
    ensure_dirs()
    args = [int(a) for a in sys.argv[1:]]
    if len(args) == 2:
        lo, hi = args
    elif len(args) == 1:
        lo = hi = args[0]
    else:
        lo, hi = FIRST_BOOK, LAST_BOOK

    # Merge into existing output so partial/test runs accumulate.
    books = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding='utf-8') as f:
            books = json.load(f).get('books', {})

    for k in range(lo, hi + 1):
        book = scrape_book(k)
        if book:
            books[str(k)] = book

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"source": "pravoslavno.rs/svetopismo", "books": books}, f, ensure_ascii=False)

    total = sum(sum(len(v) for v in b['chapters'].values()) for b in books.values())
    print(f"\nWrote {len(books)} books, {total} verses -> {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
