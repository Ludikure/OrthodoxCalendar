#!/usr/bin/env python3
"""
Build the English Bible index used to fill readings the OCA day-scrape
(holytrinityorthodox.com, NKJV) doesn't provide — festal Vespers OT prophecies,
Hours readings, and the post-Pentecost weekday epistle cycle.

Sources (both public domain):
  - New Testament: King James Version (Byzantine/Textus Receptus — aligns with the
    Orthodox text tradition). data/raw/en/bible/kjv.json (getbible v2).
  - Old Testament + deuterocanon: Brenton's Septuagint (the Greek LXX the Orthodox
    lectionary is based on; correct versification + Wisdom/Baruch). USFX from
    eBible.org: data/raw/en/bible/eng-Brenton_usfx.xml.

Output: data/processed/en/bible.json — { engine_book_name: { chapter: { verse: text }}}
keyed by the lectionary engine's book names so generate_readings can assemble by
reference.
"""

import json
import os
import re
from html import unescape

RAW = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'en', 'bible')
OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'en', 'bible.json')

# Old Testament: engine book name -> Brenton USFX book id.
BRENTON_OT = {
    'Genesis': 'GEN', 'Exodus': 'EXO', 'Leviticus': 'LEV', 'Numbers': 'NUM',
    'Deuteronomy': 'DEU', 'Joshua': 'JOS', 'Judges': 'JDG', 'Ruth': 'RUT',
    '1 Samuel': '1SA', '2 Samuel': '2SA', '1 Kings': '1KI', '2 Kings': '2KI',
    '1 Chronicles': '1CH', '2 Chronicles': '2CH', 'Ezra': 'EZR', 'Nehemiah': 'NEH',
    'Job': 'JOB', 'Psalms': 'PSA', 'Proverbs': 'PRO', 'Ecclesiastes': 'ECC',
    'Song of Songs': 'SNG', 'Isaiah': 'ISA', 'Jeremiah': 'JER', 'Lamentations': 'LAM',
    'Ezekiel': 'EZK', 'Daniel': 'DAG', 'Hosea': 'HOS', 'Joel': 'JOL', 'Amos': 'AMO',
    'Obadiah': 'OBA', 'Jonah': 'JON', 'Micah': 'MIC', 'Nahum': 'NAM', 'Habakkuk': 'HAB',
    'Zephaniah': 'ZEP', 'Haggai': 'HAG', 'Zechariah': 'ZEC', 'Malachi': 'MAL',
    'Wisdom of Solomon': 'WIS', 'Sirach': 'SIR', 'Baruch': 'BAR', 'Tobit': 'TOB',
    'Judith': 'JDT',
}


def load_nt(filename):
    """New Testament (books 40-66) from a getbible-format file, keyed by book name."""
    data = json.load(open(os.path.join(RAW, filename)))
    out = {}
    for book in data['books']:
        if not 40 <= book['nr'] <= 66:  # NT only
            continue
        chapters = {}
        for ch in book['chapters']:
            chapters[str(ch['chapter'])] = {
                str(v['verse']): v['text'].strip() for v in ch['verses'] if v.get('text')
            }
        out[book['name']] = chapters
    return out


def load_brenton_ot():
    """Old Testament + deuterocanon from Brenton's Septuagint (USFX)."""
    xml = open(os.path.join(RAW, 'eng-Brenton_usfx.xml'), encoding='utf-8', errors='replace').read()
    # Collect verses keyed by USFX book id via the bcv="BOOK.C.V" attribute.
    by_code = {}
    for m in re.finditer(
        r'<v id="[^"]*" bcv="(\w+)\.(\d+)\.(\d+)"\s*/>(.*?)(?=<v id=|<ve|<c id=|</book>|<book )',
        xml, re.DOTALL,
    ):
        code, ch, v, raw = m.group(1), m.group(2), m.group(3), m.group(4)
        raw = re.sub(r'<f\b[^>]*>.*?</f>', '', raw, flags=re.DOTALL)   # footnotes
        raw = re.sub(r'<x\b[^>]*>.*?</x>', '', raw, flags=re.DOTALL)   # cross-refs
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', unescape(text)).strip()
        if text:
            by_code.setdefault(code, {}).setdefault(ch, {})[v] = text

    out = {}
    for name, code in BRENTON_OT.items():
        if code in by_code:
            out[name] = by_code[code]
    return out


def main():
    # Default text: KJV New Testament + Brenton Septuagint Old Testament.
    bible = {}
    bible.update(load_brenton_ot())
    bible.update(load_nt('kjv.json'))
    # Alternate New Testament: World English Bible (modern English). The OT stays
    # Brenton (LXX) for both, so only the NT is user-switchable.
    nt_web = load_nt('web.json')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump({
            "source": "KJV (NT) + Brenton Septuagint (OT); WEB alternate NT",
            "books": bible,
            "ntWeb": nt_web,
        }, f, ensure_ascii=False)
    total = sum(len(v) for b in bible.values() for v in b.values())
    print(f"Wrote {len(bible)} books + {len(nt_web)} WEB NT books, {total} verses -> {OUT}")


if __name__ == "__main__":
    main()
