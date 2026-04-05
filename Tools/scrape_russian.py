#!/usr/bin/env python3
"""
Scrape days.pravoslavie.ru for Russian Orthodox calendar data.
Outputs a JSON file keyed by "MM-DD" (Gregorian) with Russian descriptions
and fasting info.

URL pattern: days.pravoslavie.ru/Days/YYYYMMDD.html (Julian date in URL)
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date, timedelta

YEAR = 2026
JULIAN_OFFSET = 13  # Gregorian - Julian for 1900-2099


def julian_date_str(greg_date: date) -> str:
    """Convert Gregorian date to Julian date string YYYYMMDD for URL."""
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return julian.strftime("%Y%m%d")


def fetch_day(greg_date: date) -> str:
    jd = julian_date_str(greg_date)
    url = f"https://days.pravoslavie.ru/Days/{jd}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "OrthodoxCalendarApp/1.0"})
    try:
        data = urllib.request.urlopen(req, timeout=15).read()
        return data.decode("utf-8")
    except Exception as e:
        print(f"  ERROR fetching {greg_date}: {e}", file=sys.stderr)
        return ""


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&#171;", "«")
    text = text.replace("&#187;", "»")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_fasting_abbrev(diet_text: str, post_text: str) -> str:
    """Map Russian fasting description to abbreviation."""
    diet_lower = diet_text.lower()
    post_lower = post_text.lower()

    # No fast
    if "поста нет" in diet_lower or ("нет" in diet_lower and "пост" not in post_lower):
        return "б/п"

    # Complete abstinence
    if "полное воздержание" in diet_lower:
        return "*"

    # Dry eating (bread, water, raw food)
    if "сухоядение" in diet_lower:
        return "вода"

    # Hot food without oil
    if "горячая" in diet_lower and "без масла" in diet_lower:
        return "вода"

    # Fish allowed
    if "рыб" in diet_lower:
        return "рыба"

    # Oil allowed
    if "маслом" in diet_lower or "масл" in diet_lower or "елей" in diet_lower:
        return "елей"

    # Generic strict fast
    if "строг" in post_lower or "великий пост" in post_lower:
        return "вода"

    # If there's some post mentioned but no specific diet
    if post_text and not diet_text:
        return "вода"

    return ""


def parse_day(html: str) -> dict:
    """Parse a single day page."""
    if not html:
        return {}

    # Extract fasting info
    post_match = re.search(r'DD_POST[^>]*>(.*?)</SPAN>', html)
    diet_match = re.search(r'DD_TPTXT[^>]*>(.*?)</SPAN>', html)

    post_text = strip_html(post_match.group(1)) if post_match else ""
    diet_text = strip_html(diet_match.group(1)) if diet_match else ""

    # Extract saints/feasts — all P tags with DP_TEXT class
    entries = re.findall(r'<P CLASS="DP_TEXT[^"]*">(.*?)</P>', html, re.DOTALL)
    saints = []
    is_major_feast = False

    for entry in entries:
        # Check if it's a major feast (has data-prazdnik or large font)
        if "data-prazdnik" in entry or "font-size: 120%" in entry:
            is_major_feast = True

        clean = strip_html(entry)
        if clean:
            saints.append(clean)

    # Check for week info (Страстная, Светлая, etc.)
    week_match = re.search(r'DD_NED[^>]*>(.*?)</SPAN>', html)
    week_info = strip_html(week_match.group(1)) if week_match else ""

    # Extract Feofan prayer/spiritual reading
    feofan_match = re.search(r'DD_FEOFAN[^>]*>(.*?)</DIV>', html, re.DOTALL)
    feofan = ""
    if feofan_match:
        feofan = strip_html(feofan_match.group(1))

    # Extract liturgical notes (PRIM)
    prim_match = re.search(r'DD_PRIM[^>]*>(.*?)</SPAN>', html, re.DOTALL)
    prim = ""
    if prim_match:
        prim = strip_html(prim_match.group(1))

    # Build description: join all saints with "; " for compact display
    description = "; ".join(saints) if saints else ""

    # First entry is usually the main feast/commemoration
    main_text = saints[0] if saints else ""

    return {
        "description": description,
        "mainFeast": main_text,
        "saints": saints,
        "fasting": parse_fasting_abbrev(diet_text, post_text),
        "fastingFull": diet_text if diet_text else post_text,
        "weekInfo": week_info,
        "isMajorFeast": is_major_feast,
        "prayer": feofan,
        "liturgicalNote": prim,
    }


def main():
    all_days = {}
    start = date(YEAR, 1, 1)
    end = date(YEAR, 12, 31)

    current = start
    count = 0
    while current <= end:
        if current.day == 1:
            print(f"  Fetching {current.strftime('%B %Y')}...", file=sys.stderr)

        html = fetch_day(current)
        if html:
            parsed = parse_day(html)
            if parsed:
                key = current.strftime("%m-%d")
                all_days[key] = parsed
                count += 1

        current += timedelta(days=1)
        time.sleep(0.3)  # Be polite — 365 requests

    print(f"\nTotal: {count} days scraped", file=sys.stderr)

    output = {
        "year": YEAR,
        "source": "days.pravoslavie.ru",
        "days": all_days,
    }

    json_str = json.dumps(output, ensure_ascii=False, indent=2)
    print(json_str)


if __name__ == "__main__":
    main()
