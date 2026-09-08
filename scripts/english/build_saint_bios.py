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
import functools
import importlib.util
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from html import unescape

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shared'))
from htmltext import to_text

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
ABBREVS = [m[:3] for m in MONTHS]
# "see May 6", "see Dec. 21" — but not "Dec 11-17", a range of days rather than
# one day to look up.
DATE_REF_RE = re.compile(r'\b(' + '|'.join(ABBREVS) + r')[a-z]*\.?\s+(\d{1,2})\b(?![-–\d])')


# ─── holytrinityorthodox: saint lines with life links ────────────────────────

def saint_lines(day_html: str) -> list:
    """(name, [life urls]) per saint line.

    The names have to be the ones parse_saints() puts in the calendar — a bio
    keyed to a line is shown on that feast — so both come from htc.saint_lines.
    """
    return [(htc.split_context(text)[0], LOS_LINK_RE.findall(line))
            for line, text in htc.saint_lines(day_html)]


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

@functools.lru_cache(maxsize=None)
def orthocal_stories(church_key: str) -> tuple:
    """The day's stories, parsed once — resolve_stub() reads other days too."""
    path = os.path.join(RAW_DIR, f'orthocal_{YEAR}-{church_key}.json')
    if not os.path.exists(path):
        return ()
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for s in data.get('stories', []):
        title = s.get('title', '').strip()
        text = to_text(s.get('story', ''))
        if title and text:
            out.append({'title': title, 'text': text})
    return tuple(out)


POINTER_RE = re.compile(r'\b(see|commemorat)', re.IGNORECASE)
SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')
# "Theodore the Branded, brother of St Theophanes the Hymnographer" points at
# Theodore's life; the clause names somebody else.
KIN_RE = re.compile(r'[,;]?\s+(?:and\s+)?(?:his|her|their)?\s*'
                    r'(?:brother|sister|companion|disciple|mother|father|son|daughter|'
                    r'child|children|wife|husband|nephew|niece|friend|teacher|pupil)s?\s+of\s+',
                    re.IGNORECASE)


def is_stub(text: str) -> bool:
    """True when the story is only a pointer to another day, not a life.

    Sentences that carry the pointer are struck out; a story with anything of
    substance left is a real (if short) biography and keeps its own text — "His
    'Holy Trinity' icon ... is sometimes called the most perfectly executed of
    all icons. See January 29." tells Rublev's story, it does not defer it.
    """
    if len(text) > 250:
        return False
    rest = ' '.join(s for s in SENTENCE_RE.split(text) if s.strip() and not POINTER_RE.search(s))
    return len(rest) < 60


def stub_names(title: str) -> tuple:
    """(the saint the story is about, the other person the title names)."""
    m = KIN_RE.search(title)
    return (title, '') if not m else (title[:m.start()], title[m.end():])


def resolve_stub(story: dict) -> dict:
    """'For his life see May 6.' -> the May 6 story about the same saint."""
    if not is_stub(story['text']):
        return story
    ref = DATE_REF_RE.search(story['text'])
    if not ref:
        return story
    key = f'{ABBREVS.index(ref.group(1)) + 1:02d}-{int(ref.group(2)):02d}'
    own, other = stub_names(story['title'])
    want, want_other = matcher.significant(own, 'en'), matcher.significant(other, 'en')
    best, best_score = None, 0
    for cand in orthocal_stories(key):
        if len(cand['text']) <= 250:
            continue
        title = matcher.significant(cand['title'], 'en')
        s = matcher.score(want, title)
        # The referenced day tells the companion's life, not the saint's:
        # leave the pointer alone rather than file it under the wrong name.
        if s > best_score and s > matcher.score(want_other, title):
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
            # Run the app's matcher over the whole day, the stories competing
            # with the lives already collected (whose titles are the feast
            # names). A story is kept only where it landed on the one feast it
            # fits better than every other: a story about a saint who already
            # has a life fits that saint's feast best and is a duplicate, and a
            # story that fits several feasts equally well ("Basil the Great"
            # next to "Basil of Ancyra") names none of them. Hiding the covered
            # feasts instead — which is what this used to do — leaves those
            # stories looking for a home and ships St Basil's life under an
            # unrelated New Hieromartyr.
            # No single-bio fallback: a lone story must match a feast by name.
            candidates = bios + stories
            assigned = matcher.new_assign(feasts, candidates, 'en', single_fallback=False)
            sc = matcher.pair_scores(feasts, candidates, 'en')
            keep = set()
            for i, j in assigned.items():
                if j < len(bios):
                    continue
                best = sorted((sc[(f, j)] for f in range(len(feasts))), reverse=True)
                if sc[(i, j)] == best[0] and (len(best) < 2 or best[1] < best[0]):
                    keep.add(j - len(bios))
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
