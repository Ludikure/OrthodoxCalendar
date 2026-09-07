#!/usr/bin/env python3
"""Build data/processed/en/saint_bios.json from holytrinityorthodox.com lives
plus orthocal.info stories.

holytrinityorthodox.com (the source of the English saints list) links a
"Lives of the Saints" page from the saint line itself, so those bios attach to
the exact feast entry. Day pages are cached as data/raw/en/htc_YYYY_MM_DD.html
(same cache as scrape_holytrinityorthodox.py), life pages under
data/raw/en/los/<Month>/<DD-NN>.htm.

orthocal.info stories (data/raw/en/orthocal_YYYY-MM-DD.json, keyed by church
date, i.e. Julian date for the Old Calendar day shown) fill in saints that have
no holytrinityorthodox life. Stories that only say "For his life see May 6" are
replaced by the story they point to.

Bios are keyed by Gregorian MM-DD of the scraped year and are year-independent.

Usage:
    python3 scripts/english/build_saint_bios.py --fetch   # download missing pages first
    python3 scripts/english/build_saint_bios.py
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(HERE, '..', '..')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'en')
LOS_DIR = os.path.join(RAW_DIR, 'los')
OUTPUT = os.path.join(BASE_DIR, 'data', 'processed', 'en', 'saint_bios.json')
YEAR = 2026
JULIAN_OFFSET = 13


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


htc = _load(os.path.join(HERE, 'scrape_holytrinityorthodox.py'), 'htc')
matcher = _load(os.path.join(BASE_DIR, 'scripts', 'shared', 'simulate_bio_matching.py'), 'bio_matcher')

LOS_LINK_RE = re.compile(r'href="(https?://www\.holytrinityorthodox\.com/htc/ocalendar/los/([A-Za-z]+)/([0-9]{2}-[0-9]{2})\.htm)"')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']
DATE_REF_RE = re.compile(r'\b(' + '|'.join(MONTHS) + r'|Dec)\.? (\d{1,2})\b')


# ─── holytrinityorthodox: saint lines with life links ────────────────────────

def saint_lines(day_html: str) -> list:
    """(name, [life urls]) per saint line, split exactly like parse_saints()."""
    scripture_pos = day_html.find('class="pscriptureheader"')
    saints_html = day_html[:scripture_pos] if scripture_pos > 0 else day_html
    m = re.search(r'<span class="normaltext">(.*)', saints_html, re.DOTALL)
    if not m:
        return []
    block = re.sub(r'</span>\s*$', '', m.group(1))
    out = []
    for line in re.split(r'<br\s*/?>\s*', block):
        line = line.strip()
        if not line:
            continue
        links = [(url, month, dd) for url, month, dd in LOS_LINK_RE.findall(line)]
        text = re.sub(r'<span class="typicon-[0-9o]">[^<]*</span>', '', line)
        text = htc.clean_text(htc.strip_tags(text)).rstrip('.').strip()
        if len(text) < 3:
            continue
        paren = re.search(r'\(([^)]*(?:movable|Celtic|British|Greek|Georgia|Arabic|Romanian|Slav)(?:[^)]*)?)\)\s*$', text, re.IGNORECASE)
        if paren:
            text = text[:paren.start()].strip().rstrip(',').strip()
        out.append((text, links))
    return out


def life_cache_path(month: str, dd: str) -> str:
    return os.path.join(LOS_DIR, month, f'{dd}.htm')


def life_text(html: str) -> str:
    paras = []
    for p in re.findall(r'<p class="ofd_los_body"[^>]*>(.*?)</p>', html, re.DOTALL):
        if '<img' in p or 'Commemorated on' in p or '©' in p:
            continue
        p = re.sub(r'\s+', ' ', p)                # the source wraps lines at ~80 chars
        p = re.sub(r'\s*<br\s*/?>\s*', '\n', p)  # <br> separates paragraphs
        p = unescape(re.sub(r'<[^>]+>', '', p))
        lines = [re.sub(r'[ \t\xa0\r]+', ' ', l).strip() for l in p.split('\n')]
        lines = [l for l in lines if l]
        if lines:
            paras.append('\n'.join(lines))
    text = '\n'.join(paras).strip()
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return text


# ─── orthocal ────────────────────────────────────────────────────────────────

def orthocal_stories(church_key: str) -> list:
    path = os.path.join(RAW_DIR, f'orthocal_{YEAR}-{church_key}.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for s in data.get('stories', []):
        title = s.get('title', '').strip()
        text = htc_strip(s.get('story', ''))
        if title and text:
            out.append({'title': title, 'text': text})
    return out


def htc_strip(story_html: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', story_html)
    text = re.sub(r'</(p|div|h[1-6]|li)>', '\n', text, flags=re.IGNORECASE)
    text = unescape(re.sub(r'<[^>]+>', '', text))
    lines = [re.sub(r'[ \t\xa0]+', ' ', l).strip() for l in text.split('\n')]
    return '\n'.join(l for l in lines if l).strip()


def resolve_stub(story: dict) -> dict:
    """'For his life see May 6.' -> the May 6 story about the same saint."""
    text = story['text']
    if len(text) > 250 or not re.search(r'\b(see|commemorat)', text, re.IGNORECASE):
        return story
    ref = DATE_REF_RE.search(text)
    if not ref:
        return story
    month = MONTHS.index(ref.group(1)) + 1 if ref.group(1) != 'Dec' else 12
    key = f'{month:02d}-{int(ref.group(2)):02d}'
    want = matcher.significant(story['title'], 'en')
    best, best_score = None, 0
    for cand in orthocal_stories(key):
        if len(cand['text']) <= 250:
            continue
        s = matcher.score(want, matcher.significant(cand['title'], 'en'))
        if s > best_score:
            best, best_score = cand, s
    if best and best_score >= 2:
        return {'title': story['title'], 'text': best['text']}
    return story


# ─── build ───────────────────────────────────────────────────────────────────

def church_key(greg: date) -> str:
    j = greg - timedelta(days=JULIAN_OFFSET)
    return f'{j.month:02d}-{j.day:02d}'


def fetch_missing(year: int) -> None:
    os.makedirs(LOS_DIR, exist_ok=True)
    needed = {}
    cur = date(year, 1, 1)
    while cur.year == year:
        for _, links in saint_lines(htc.fetch_day(cur.year, cur.month, cur.day)):
            for url, month, dd in links:
                needed[(month, dd)] = url
        cur += timedelta(days=1)
    todo = [(k, u) for k, u in sorted(needed.items()) if not os.path.exists(life_cache_path(*k))]
    print(f'{len(needed)} life pages referenced, {len(todo)} to fetch', file=sys.stderr)
    for i, ((month, dd), url) in enumerate(todo, 1):
        os.makedirs(os.path.join(LOS_DIR, month), exist_ok=True)
        try:
            html = htc.fetch_url(url)
        except Exception as e:  # keep going; the build reports what is missing
            print(f'  ERROR {url}: {e}', file=sys.stderr)
            time.sleep(3)
            continue
        with open(life_cache_path(month, dd), 'w', encoding='utf-8') as f:
            f.write(html)
        if i % 100 == 0:
            print(f'  {i}/{len(todo)}', file=sys.stderr)
        time.sleep(0.8)


def build(year: int) -> dict:
    days = {}
    stats = {'lines': 0, 'htc': 0, 'missing_pages': 0, 'empty_pages': 0,
             'orthocal_added': 0, 'orthocal_dropped': 0, 'stubs_resolved': 0}
    cur = date(year, 1, 1)
    while cur.year == year:
        key = f'{cur.month:02d}-{cur.day:02d}'
        lines = saint_lines(htc.fetch_day(cur.year, cur.month, cur.day))
        stats['lines'] += len(lines)
        bios, covered = [], set()
        for idx, (name, links) in enumerate(lines):
            texts = []
            for url, month, dd in links:
                path = life_cache_path(month, dd)
                if not os.path.exists(path):
                    stats['missing_pages'] += 1
                    continue
                with open(path, encoding='utf-8', errors='replace') as f:
                    t = life_text(f.read())
                if t:
                    texts.append(t)
                else:
                    stats['empty_pages'] += 1
            if texts:
                bios.append({'title': name, 'text': '\n\n'.join(texts)})
                covered.add(idx)
                stats['htc'] += 1
        # orthocal stories for saints that have no holytrinityorthodox life
        feasts = [{'name': n, 'moveable': False} for n, _ in lines]
        stories = []
        for s in orthocal_stories(church_key(cur)):
            r = resolve_stub(s)
            if r is not s:
                stats['stubs_resolved'] += 1
            stories.append(r)
        if stories:
            open_feasts = [f if i not in covered else {'name': '', 'moveable': True} for i, f in enumerate(feasts)]
            # no single-bio fallback: a lone story must match a feast by name to be kept
            assigned = matcher.new_assign(open_feasts, stories, 'en', single_fallback=False)
            keep = set(assigned.values())
            for j, s in enumerate(stories):
                if j in keep:
                    bios.append(s)
                    stats['orthocal_added'] += 1
                else:
                    stats['orthocal_dropped'] += 1
        if bios:
            days[key] = bios
        cur += timedelta(days=1)
    print(', '.join(f'{k} {v}' for k, v in stats.items()), file=sys.stderr)
    return days


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='download missing life pages first')
    ap.add_argument('--out', default=OUTPUT)
    args = ap.parse_args()
    htc.ensure_dirs()
    if args.fetch:
        fetch_missing(YEAR)
    days = build(YEAR)
    total = sum(len(v) for v in days.values())
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump({'source': 'holytrinityorthodox.com + orthocal.info', 'year': YEAR, 'days': days},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'wrote {args.out}: {len(days)} days, {total} bios', file=sys.stderr)


if __name__ == '__main__':
    main()
