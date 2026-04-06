#!/usr/bin/env python3
"""
Merge Russian calendar data from two sources:
- azbyka.ru: concise saint names (primary for descriptions)
- days.pravoslavie.ru: fasting details + prayers (primary for fasting/prayers)

Then build the saints mapping (fixed by Julian date + moveable by pascha distance).
"""

import json
import re
import sys
from datetime import date, timedelta
from html import unescape

YEAR = 2026
JULIAN_OFFSET = 13
PASCHA_2026 = date(2026, 4, 12)

MOVEABLE_DISTANCES = {
    -70, -63, -56, -49, -48, -28,
    -8, -7, -6, -5, -4, -3, -2, -1,
    0, 1, 2, 3, 4, 5, 6,
    7, 14, 24, 39, 49, 50, 56, 57,
}


def greg_to_julian_key(greg_date: date) -> str:
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return f"{julian.month:02d}-{julian.day:02d}"


def main():
    # Load both sources
    with open("/tmp/azbyka_2026.json") as f:
        azbyka = json.load(f)["days"]

    with open("OrthodoxCalendar/Localization/ru_calendar_2026.json") as f:
        pravoslavie = json.load(f)["days"]

    print(f"Azbyka: {len(azbyka)} days", file=sys.stderr)
    print(f"Pravoslavie: {len(pravoslavie)} days", file=sys.stderr)

    # Merge: azbyka saints + pravoslavie fasting/prayers
    fixed = {}
    moveable = {}

    for greg_key in sorted(set(list(azbyka.keys()) + list(pravoslavie.keys()))):
        month, day_num = int(greg_key[:2]), int(greg_key[3:])
        greg_date = date(YEAR, month, day_num)
        pdist = (greg_date - PASCHA_2026).days
        julian_key = greg_to_julian_key(greg_date)

        az = azbyka.get(greg_key, {})
        pr = pravoslavie.get(greg_key, {})

        # Use azbyka description when it has major feast info,
        # otherwise fall back to pravoslavie (which always includes feast names)
        az_desc = az.get("description", "")
        pr_desc = pr.get("description", "")
        az_major = az.get("isMajorFeast", False)
        pr_major = pr.get("isMajorFeast", False)

        if az_desc and (az_major or not pr_major):
            # Azbyka has the data and either it's complete or pravoslavie isn't major either
            description = az_desc
        else:
            # Pravoslavie has the major feast name that azbyka missed
            description = pr_desc
        is_major = az_major or pr_major

        # Use pravoslavie for fasting, prayers, liturgical notes
        fasting = pr.get("fasting", "")
        fasting_full = pr.get("fastingFull", "")
        prayer = pr.get("prayer", "")
        liturgical_note = pr.get("liturgicalNote", "")

        entry = {
            "description": description,
            "fasting": fasting,
            "isMajorFeast": is_major,
            "fastingFull": fasting_full,
            "prayer": prayer,
            "liturgicalNote": liturgical_note,
        }

        if pdist in MOVEABLE_DISTANCES:
            moveable[str(pdist)] = entry
        else:
            fixed[julian_key] = entry

    print(f"Fixed: {len(fixed)}, Moveable: {len(moveable)}", file=sys.stderr)

    output = {
        "source": "azbyka.ru + days.pravoslavie.ru",
        "fixedByJulianDate": fixed,
        "moveableByPaschaDistance": moveable,
    }

    with open("OrthodoxCalendar/Localization/ru_saints_map.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Saved ru_saints_map.json", file=sys.stderr)


if __name__ == "__main__":
    main()
