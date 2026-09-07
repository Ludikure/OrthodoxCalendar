#!/usr/bin/env python3
"""Build data/processed/sr/saint_bios.json from cached crkvenikalendar.com day pages.

Each cached page (data/raw/sr/crkvenikalendar/2026-MM-DD.html) lists every saint
of the day as an <h1> title followed by a <span class="tekst_opis"> with the
Ohrid Prologue entry. This script takes the title straight from the h1 and the
text straight from the span, so the two are never split heuristically.

Bios are keyed by Gregorian MM-DD and are year-independent (fixed-date saints
recur on the same Gregorian date for the whole 1900-2099 Julian offset).

On great moveable feasts the site shows only the feast, not the day's fixed
saints, so the 2026 pages for those dates yield nothing. For any date left
empty, a cached page for the same MM-DD from another year (e.g. 2027-04-12.html,
fetched from https://www.crkvenikalendar.com/datum-2027-04-12) is used instead.

Usage: python3 scripts/serbian/extract_crkvenikalendar_bios.py
"""
import glob
import json
import os
import re
import sys
from html import unescape

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'sr', 'crkvenikalendar')
OUTPUT = os.path.join(BASE_DIR, 'data', 'processed', 'sr', 'saint_bios.json')

# Non-greedy h1 that cannot run into the next h1 (feast headers without a body
# would otherwise swallow the following saint's title).
H1_RE = re.compile(r'<h1>((?:(?!<h1>).)*?)</h1>', re.DOTALL)
# First bio span after the title; the "Детаљније" button is also a tekst_opis
# span but starts with <a>, so it is excluded.
TEXT_RE = re.compile(r'<span class="tekst_opis">(?!\s*<a)(.*?)</span>', re.DOTALL)
# The "Детаљније" link carries pok=1 ("pokretni", moveable) on Holy Week,
# Zadušnice, Poklade and similar notes. Those are pinned to their 2026 dates and
# are injected algorithmically by build_database.py, so they are skipped here.
MOVEABLE_RE = re.compile(r'zitije\.php\?pok=1&')
# OCR line-break artifact in the source: "Антони- на" -> "Антонина".
HYPHEN_RE = re.compile(r'(?<=[Ѐ-ӿ])- (?=[а-џ])')


def clean(fragment: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', fragment)
    text = re.sub(r'</p>\s*<p[^>]*>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'[ \t ]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = HYPHEN_RE.sub('', text)
    return text.strip()


def parse_page(html: str) -> list:
    bios = []
    seen = set()
    heads = list(H1_RE.finditer(html))
    for i, m in enumerate(heads):
        title = clean(m.group(1)).lstrip('+ ').strip()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(html)
        if MOVEABLE_RE.search(html, m.end(), end):
            continue
        tm = TEXT_RE.search(html, m.end(), end)
        text = clean(tm.group(1)) if tm else ''
        if not title or not text or (title, text) in seen:
            continue
        seen.add((title, text))
        bios.append({'title': title, 'text': text})
    return bios


def load(path: str) -> list:
    # The site truncates its <meta keywords> mid-character now and then; the
    # damaged byte never sits inside a bio, so it is replaced rather than fatal.
    with open(path, encoding='utf-8', errors='replace') as f:
        return parse_page(f.read())


def build_days() -> tuple:
    """Return ({MM-DD: [bio, ...]}, {MM-DD: fallback page name})."""
    pages = sorted(glob.glob(os.path.join(RAW_DIR, '2026-*.html')))
    if len(pages) != 365:
        sys.exit(f'expected 365 cached pages in {RAW_DIR}, found {len(pages)}')
    days = {}
    filled_from = {}
    for path in pages:
        key = os.path.basename(path)[5:10]
        bios = load(path)
        if not bios:
            for alt in sorted(glob.glob(os.path.join(RAW_DIR, f'*-{key}.html'))):
                if alt != path and (bios := load(alt)):
                    filled_from[key] = os.path.basename(alt)
                    break
        if bios:
            days[key] = bios
    return days, filled_from


def main() -> None:
    days, filled_from = build_days()
    for key, name in sorted(filled_from.items()):
        print(f'  {key}: no fixed saints on the 2026 page, used {name}', file=sys.stderr)
    result = {'source': 'crkvenikalendar.com', 'year': 2026, 'days': days}
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    total = sum(len(v) for v in days.values())
    print(f'wrote {OUTPUT}: {len(days)} days, {total} bios', file=sys.stderr)


if __name__ == '__main__':
    main()
