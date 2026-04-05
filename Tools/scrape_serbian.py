#!/usr/bin/env python3
"""
Scrape crkvenikalendar.rs for Serbian Orthodox calendar data.
Outputs a JSON file keyed by "MM-DD" (Gregorian) with Serbian descriptions,
fasting info, and week separator notes.
"""

import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

MONTHS = [
    ("januar", 1),
    ("februar", 2),
    ("mart", 3),
    ("april", 4),
    ("maj", 5),
    ("jun", 6),
    ("jul", 7),
    ("avgust", 8),
    ("septembar", 9),
    ("oktobar", 10),
    ("novembar", 11),
    ("decembar", 12),
]

YEAR = 2026
BASE_URL = "https://crkvenikalendar.rs"


def fetch_month(month_name: str) -> str:
    url = f"{BASE_URL}/{month_name}-{YEAR}/"
    print(f"  Fetching {url}...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def strip_html(text: str) -> str:
    """Remove HTML tags but preserve text."""
    text = re.sub(r'<br\s*/?>', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&')
    text = text.replace('&#8211;', '–')
    text = text.replace('&#8212;', '—')
    text = text.replace('&#8217;', "'")
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_description_parts(html_content: str) -> dict:
    """Extract structured parts from the description cell HTML."""
    result = {
        "text": "",
        "has_slava": False,
        "is_red": False,  # feast day (red text)
        "is_bold": False,
    }

    # Check for СЛАВА badge
    if "СЛАВА" in html_content:
        result["has_slava"] = True

    # Check for red color (feast day)
    if 'color: #ff0000' in html_content or 'color:#ff0000' in html_content:
        result["is_red"] = True

    # Check for bold
    if '<strong>' in html_content or '<b>' in html_content:
        result["is_bold"] = True

    # Strip to plain text, removing СЛАВА badge text
    text = re.sub(r'<a[^>]*>.*?СЛАВА.*?</a>', '', html_content)
    text = re.sub(r'<span[^>]*>СЛАВА</span>', '', text)
    text = strip_html(text)

    result["text"] = text
    return result


def parse_month(html: str, month_num: int) -> dict:
    """Parse a month page and return dict of day entries keyed by 'MM-DD'."""
    days = {}

    # Find all day rows: <tr id="NUMBER" ...>
    # Each row has 5 td cells: day-of-week, greg-day, julian-day, description, fasting
    day_rows = re.findall(
        r'<tr\s+id="\d+"[^>]*>([\s\S]*?)</tr>',
        html
    )

    # Also find note rows (week separators with readings)
    note_rows = re.findall(
        r'<td\s+class="note-row"[^>]*>([\s\S]*?)</td>',
        html
    )

    for row_html in day_rows:
        cells = re.findall(r'<td[^>]*>([\s\S]*?)</td>', row_html)
        if len(cells) < 5:
            continue

        # Extract Gregorian day number from cell 2 (index 1)
        greg_day_text = strip_html(cells[1])
        try:
            greg_day = int(greg_day_text)
        except ValueError:
            continue

        # Description is cell 4 (index 3)
        desc = extract_description_parts(cells[3])

        # Fasting is cell 5 (index 4)
        fasting = strip_html(cells[4])

        # Julian day from cell 3 (index 2)
        julian_day = strip_html(cells[2])

        # Day of week from cell 1 (index 0)
        day_of_week = strip_html(cells[0])

        key = f"{month_num:02d}-{greg_day:02d}"
        days[key] = {
            "dayOfWeek": day_of_week,
            "gregorianDay": greg_day,
            "julianDay": julian_day,
            "description": desc["text"],
            "fasting": fasting,
            "isRed": desc["is_red"],
            "isBold": desc["is_bold"],
            "hasSlava": desc["has_slava"],
        }

    return days


def main():
    all_days = {}

    for month_name, month_num in MONTHS:
        html = fetch_month(month_name)
        month_days = parse_month(html, month_num)
        all_days.update(month_days)
        print(f"  -> {month_name}: {len(month_days)} days", file=sys.stderr)
        time.sleep(0.5)  # Be polite

    # Sort by date
    sorted_days = dict(sorted(all_days.items()))

    print(f"\nTotal: {len(sorted_days)} days scraped", file=sys.stderr)

    # Output JSON
    output = {
        "year": YEAR,
        "source": "crkvenikalendar.rs",
        "days": sorted_days,
    }

    json_str = json.dumps(output, ensure_ascii=False, indent=2)
    print(json_str)


if __name__ == "__main__":
    main()
