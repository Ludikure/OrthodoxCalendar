#!/usr/bin/env python3
"""
Scrape azbyka.ru/days for concise Russian saint names.
Fasting info kept from days.pravoslavie.ru (more detailed).
URL pattern: azbyka.ru/days/YYYY-MM-DD (Gregorian)
"""

import json
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date, timedelta
from html import unescape

YEAR = 2026


def fetch(greg_date: date) -> str:
    url = f"https://azbyka.ru/days/{greg_date.isoformat()}"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        return urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR {greg_date}: {e}", file=sys.stderr)
        return ""


def strip_accents(text: str) -> str:
    """Remove combining accent marks (ударения) from text."""
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def clean(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<span[^>]*class=['\"]?secondary-content[^>]*>.*?</span>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = strip_accents(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse(html: str) -> dict:
    if not html:
        return {}

    # Extract saints from <li class="ideograph-N"> items
    saints = []
    is_major = False

    for match in re.finditer(r'<li class="ideograph-(\d+)">(.*?)</li>', html, re.DOTALL):
        level = int(match.group(1))
        li_html = match.group(2)

        # Extract from <a> tag
        a_match = re.search(r"<a[^>]*>(.*?)</a>", li_html, re.DOTALL)
        if a_match:
            text = clean(a_match.group(1))
        else:
            text = clean(li_html)

        if text:
            if level <= 2:  # Major feast
                is_major = True
            saints.append(text)

    description = "; ".join(saints)
    return {
        "description": description,
        "saints": saints,
        "isMajorFeast": is_major,
    }


def main():
    all_days = {}
    current = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)

    while current <= end:
        if current.day == 1:
            print(f"  Fetching {current.strftime('%B %Y')}...", file=sys.stderr)

        html = fetch(current)
        parsed = parse(html)
        if parsed and parsed["description"]:
            key = current.strftime("%m-%d")
            all_days[key] = parsed

        current += timedelta(days=1)
        time.sleep(0.3)

    print(f"\nTotal: {len(all_days)} days scraped", file=sys.stderr)

    output = {
        "year": YEAR,
        "source": "azbyka.ru",
        "days": all_days,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
