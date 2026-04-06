#!/usr/bin/env python3
"""
Extract St. Theophan (Feofan) daily reflections and liturgical notes
from cached days.pravoslavie.ru HTML files.

Reads: data/raw/ru/pravoslavie_fast_YYYY-MM-DD.html
Writes: data/processed/ru/reflections.json (Feofan reflections)
Updates: data/processed/ru/fasting.json (adds liturgicalNote field)
"""

import glob
import json
import os
import re
import sys

YEAR = 2026
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'ru')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'processed', 'ru')


def strip_html_tags(text: str) -> str:
    """Remove HTML tags, decode entities, normalize whitespace."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&laquo;', '\u00ab')
    text = text.replace('&raquo;', '\u00bb')
    text = text.replace('&mdash;', '\u2014')
    text = text.replace('&ndash;', '\u2013')
    text = text.replace('&hellip;', '\u2026')
    # Decode numeric entities
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
    # Normalize whitespace: collapse runs of spaces/tabs, preserve paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    return text


def extract_feofan(html: str) -> str | None:
    """Extract DD_FEOFAN section text from HTML."""
    # Match <DIV CLASS="DD_FEOFAN">...</DIV>
    # The div contains <P CLASS="DP_FEOF"> paragraphs
    match = re.search(
        r'<DIV\s+CLASS="DD_FEOFAN">(.*?)</DIV>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    if not match:
        return None
    content = match.group(1)
    text = strip_html_tags(content)
    if not text:
        return None
    return text


def extract_prim(html: str) -> str | None:
    """Extract DD_PRIM liturgical note from HTML."""
    match = re.search(
        r'<SPAN\s+CLASS="DD_PRIM">(.*?)</SPAN>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    if not match:
        return None
    text = strip_html_tags(match.group(1))
    if not text:
        return None
    return text


def date_key_from_filename(filename: str) -> str:
    """Extract MM-DD from pravoslavie_fast_YYYY-MM-DD.html."""
    m = re.search(r'pravoslavie_fast_\d{4}-(\d{2}-\d{2})\.html', filename)
    if m:
        return m.group(1)
    return ''


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pattern = os.path.join(RAW_DIR, f'pravoslavie_fast_{YEAR}-*.html')
    files = sorted(glob.glob(pattern))
    print(f"Found {len(files)} cached pravoslavie HTML files")

    reflections = {}
    liturgical_notes = {}
    feofan_count = 0
    prim_count = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        day_key = date_key_from_filename(filename)
        if not day_key:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()

        # Extract Feofan reflection
        feofan_text = extract_feofan(html)
        if feofan_text:
            reflections[day_key] = {
                "source": "Мысли на каждый день — Свт. Феофан Затворник",
                "text": feofan_text
            }
            feofan_count += 1

        # Extract liturgical note
        prim_text = extract_prim(html)
        if prim_text:
            liturgical_notes[day_key] = prim_text
            prim_count += 1

    # Write reflections.json
    reflections_data = {
        "year": YEAR,
        "source": "days.pravoslavie.ru",
        "days": dict(sorted(reflections.items()))
    }
    reflections_path = os.path.join(OUTPUT_DIR, 'reflections.json')
    with open(reflections_path, 'w', encoding='utf-8') as f:
        json.dump(reflections_data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {feofan_count} reflections to {reflections_path}")

    # Update fasting.json with liturgicalNote
    fasting_path = os.path.join(OUTPUT_DIR, 'fasting.json')
    if os.path.exists(fasting_path):
        with open(fasting_path, 'r', encoding='utf-8') as f:
            fasting_data = json.load(f)
    else:
        fasting_data = {"year": YEAR, "source": "days.pravoslavie.ru", "days": {}}

    added_notes = 0
    for day_key, note in liturgical_notes.items():
        if day_key in fasting_data.get("days", {}):
            fasting_data["days"][day_key]["liturgicalNote"] = note
            added_notes += 1

    with open(fasting_path, 'w', encoding='utf-8') as f:
        json.dump(fasting_data, f, ensure_ascii=False, indent=2)
    print(f"Added {added_notes} liturgical notes to {fasting_path}")
    print(f"(Total liturgical notes found: {prim_count})")


if __name__ == '__main__':
    main()
