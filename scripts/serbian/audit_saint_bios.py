#!/usr/bin/env python3
"""Audit stored Serbian saint bios against the cached crkvenikalendar.com day pages.

Re-parses the cached day pages in data/raw/sr/crkvenikalendar/ with the same
parser and fallback rules extract_crkvenikalendar_bios.py uses and compares the result with
data/processed/sr/saint_bios.json. Reports mangled titles (bio text swallowed
into the title), truncated texts, source bios never captured, and stored bios
with no source counterpart. Exit code 1 when anything but exact matches is found.

Usage: python3 scripts/serbian/audit_saint_bios.py [--dump parsed_source.json]
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_crkvenikalendar_bios import OUTPUT, build_days  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def main() -> int:
    stored = json.load(open(OUTPUT, encoding='utf-8'))['days']
    source, _ = build_days()
    if '--dump' in sys.argv:
        out = sys.argv[sys.argv.index('--dump') + 1]
        json.dump(source, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    n_src = sum(len(v) for v in source.values())
    n_sto = sum(len(v) for v in stored.values())
    print(f"source bios: {n_src} across {len(source)} days; stored bios: {n_sto} across {len(stored)} days\n")

    cats = collections.Counter()
    examples = collections.defaultdict(list)
    for key in sorted(set(source) | set(stored)):
        src = source.get(key, [])
        used = set()
        for sb in stored.get(key, []):
            st, sx = norm(sb['title']), norm(sb['text'])
            hit = None
            for i, b in enumerate(src):
                if i in used:
                    continue
                bt = norm(b['title'])
                if st == bt or norm(bt + ' ' + b['text']).startswith(st) or st.startswith(bt):
                    hit = i
                    break
            if hit is None:
                cats['stored_not_in_source'] += 1
                examples['stored_not_in_source'].append((key, st[:80], len(sx)))
                continue
            used.add(hit)
            b = src[hit]
            bt, bx = norm(b['title']), norm(b['text'])
            if st == bt and sx == bx:
                cats['exact'] += 1
            elif st == bt:
                cats['title_ok_text_differs'] += 1
                examples['title_ok_text_differs'].append((key, bt, len(sx), len(bx)))
            else:
                cats['title_mangled'] += 1
                examples['title_mangled'].append((key, st[:90], len(sx), len(bx)))
        for i, b in enumerate(src):
            if i not in used:
                cats['source_missing_from_stored'] += 1
                examples['source_missing_from_stored'].append((key, b['title'], len(b['text'])))

    print("=== categories ===")
    for k, v in cats.most_common():
        print(f"  {v:5d}  {k}")
    for cat in ('title_mangled', 'title_ok_text_differs', 'source_missing_from_stored', 'stored_not_in_source'):
        if examples[cat]:
            print(f"\n=== {cat} ({len(examples[cat])}, first 20) ===")
            for e in examples[cat][:20]:
                print("  ", e)

    lens = sorted(len(b['text']) for v in source.values() for b in v)
    buckets = collections.Counter()
    for l in lens:
        buckets['<100' if l < 100 else '100-200' if l < 200 else '200-500' if l < 500
                else '500-1000' if l < 1000 else '1000+'] += 1
    print("\n=== source text length distribution (the site itself) ===")
    for k in ('<100', '100-200', '200-500', '500-1000', '1000+'):
        print(f"  {k:>9}: {buckets[k]}")
    return 0 if set(cats) <= {'exact'} else 1


if __name__ == '__main__':
    sys.exit(main())
