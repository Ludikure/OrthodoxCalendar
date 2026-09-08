#!/usr/bin/env python3
"""Build data/processed/ru/saint_bios.json from cached azbyka.ru pages.

Day pages (data/raw/ru/azbyka_YYYY-MM-DD.html) list the saints of the day as
<li class="ideograph-N"> entries linking to saint pages
(data/raw/ru/saint_<slug>.html). On a saint page the life sits in
<div class="block saint-description"> (saints-group-description for group pages,
holiday-description for feast pages): a <p class="short-description"> summary
followed by <div class="brif"> with the full text. Everything else on the page
(remembrance dates, services, troparia, canons, sidebars) is ignored.

The bio title is the entry's text as shown on the day page. The text is the
"Краткое житие" section when the page has both a short and a full life,
otherwise the whole life, or the short summary when the page has no life.
Lives longer than MAX_CHARS are cut at a paragraph boundary near CUT_CHARS and
end with an ellipsis (some full lives on azbyka run to half a million
characters). Bios are keyed by Gregorian MM-DD of the scraped year and are
year-independent.

Usage: python3 scripts/russian/extract_azbyka_bios.py [--year 2026] [--out FILE]
"""
import argparse
import functools
import glob
import json
import os
import re
import sys
from html import unescape

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shared'))
from htmltext import to_text

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'ru')
OUTPUT = os.path.join(BASE_DIR, 'data', 'processed', 'ru', 'saint_bios.json')

LI_RE = re.compile(r'<li\s+class="ideograph-\d+">(.*?)</li>', re.DOTALL)
LINK_RE = re.compile(r'<a\s+href=[\'"]?(https?://azbyka\.ru/days/(?:sv|svv|prazdnik)-[^\'"\s>]+)[\'"]?[^>]*>(.*?)</a>', re.DOTALL)
BLOCK_RE = re.compile(r'<div\s+class="block (?:saint-description|saints-group-description|holiday-description)">(.*?)(?=<div\s+(?:id="[^"]*"\s+)?class="block[ "]|<div\s+id="left-bar")', re.DOTALL)
SHORT_RE = re.compile(r'<p\s+class="short-description">(.*?)</p>', re.DOTALL)
BRIF_RE = re.compile(r'<div\s+class="brif[^"]*">(.*)', re.DOTALL)
READ_MORE_RE = re.compile(r'<div\s+class="read-more">.*?</div>', re.DOTALL)


def clean(fragment: str) -> str:
    return to_text(fragment, drop=(READ_MORE_RE,), accents=False)


def entries(day_html: str) -> list:
    """(title, url) for each saint entry of a day page; multi-saint entries keep the first link."""
    out = []
    for m in LI_RE.finditer(day_html):
        li = m.group(1)
        link = LINK_RE.search(li)
        if not link:
            continue
        li = re.sub(r'<span[^>]*class=[\'"]?secondary-content[^>]*>.*?</span>', '', li, flags=re.DOTALL)
        title = re.sub(r'\s+', ' ', clean(li)).strip(' ,;')
        title = re.sub(r'\s+([,;:)])', r'\1', title)
        if title:
            out.append((title, link.group(1)))
    return out


MAX_CHARS = 15000   # longer lives are cut ...
CUT_CHARS = 12000   # ... at the last paragraph boundary before this
H3_RE = re.compile(r'<h3[^>]*>(.*?)</h3>', re.DOTALL)
SHORT_HEAD_RE = re.compile(r'<h3[^>]*>\s*Краткое житие', re.IGNORECASE)
FULL_HEAD_RE = re.compile(r'<h3[^>]*>\s*Полное житие', re.IGNORECASE)
LIFE_HEAD_RE = re.compile(r'^\s*(краткое |полное |краткие |полные )?(жити[ея]|жизнеописани[ея]|страдани[ея])', re.IGNORECASE)


def _drop_life_headings(html: str) -> str:
    """Remove "Житие ..." / "Краткое житие ..." headings; keep other subheadings as lines."""
    def repl(m):
        heading = re.sub(r'<[^>]+>', '', m.group(1))
        return '\n' if LIFE_HEAD_RE.match(unescape(heading)) else m.group(0)
    return H3_RE.sub(repl, html)


def truncate(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    cut = text.rfind('\n', 0, CUT_CHARS)
    if cut < CUT_CHARS // 2:
        cut = max(text.rfind('. ', 0, CUT_CHARS), CUT_CHARS // 2)
    return text[:cut].rstrip(' .,;:') + '…'


def life(saint_html: str) -> str:
    block = BLOCK_RE.search(saint_html)
    if not block:
        return ''
    body = block.group(1)
    short = SHORT_RE.search(body)
    brif = BRIF_RE.search(body)
    if not brif:
        return clean(short.group(1)) if short else ''
    html = brif.group(1)
    full = FULL_HEAD_RE.search(html)
    if full and SHORT_HEAD_RE.search(html[:full.start()]):
        html = html[:full.start()]
    text = clean(_drop_life_headings(html))
    if len(text) < 80 and short:
        text = clean(short.group(1))
    return truncate(text)


@functools.lru_cache(maxsize=None)
def life_for_slug(slug: str):
    """Life text of a cached saint page, or None when the page is missing.

    Saints commemorated on several days link the same page, and full lives on
    azbyka run to hundreds of kilobytes — parse each page once.
    """
    path = os.path.join(RAW_DIR, f'saint_{slug}.html')
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8', errors='replace') as f:
        return life(f.read())


def build(year: int) -> tuple:
    days, missing_pages, empty = {}, [], []
    for path in sorted(glob.glob(os.path.join(RAW_DIR, f'azbyka_{year}-*.html'))):
        key = os.path.basename(path)[12:17]
        with open(path, encoding='utf-8', errors='replace') as f:
            day_html = f.read()
        bios = []
        seen = set()
        for title, url in entries(day_html):
            slug = url.rstrip('/').split('/')[-1]
            text = life_for_slug(slug)
            if text is None:
                missing_pages.append((key, slug))
                continue
            if not text:
                empty.append((key, title))
                continue
            if (title, text) in seen:
                continue
            seen.add((title, text))
            bios.append({'title': title, 'text': text})
        if bios:
            days[key] = bios
    return days, missing_pages, empty


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, default=2026)
    ap.add_argument('--out', default=OUTPUT)
    args = ap.parse_args()
    days, missing, empty = build(args.year)
    total = sum(len(v) for v in days.values())
    print(f'{len(days)} days, {total} bios; {len(missing)} entries without a cached page, '
          f'{len(empty)} pages without a life', file=sys.stderr)
    for x in missing[:10]:
        print('  missing page:', x, file=sys.stderr)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump({'source': 'azbyka.ru', 'year': args.year, 'days': days}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'wrote {args.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
