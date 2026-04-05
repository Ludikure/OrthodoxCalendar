#!/usr/bin/env python3
"""
Build reusable saints mappings from 2026 scraped data.
Uses exact pascha_distance values for moveable feast classification
instead of fragile keyword matching.
"""

import json
import sys
from datetime import date, timedelta

YEAR = 2026
JULIAN_OFFSET = 13
PASCHA_2026 = date(2026, 4, 12)

# Exact pascha distances for moveable feasts
# These days have descriptions that change yearly based on Pascha
MOVEABLE_DISTANCES = {
    -70,  # Sunday of Publican & Pharisee
    -63,  # Sunday of Prodigal Son
    -56,  # Meatfare Sunday
    -49,  # Cheesefare Sunday
    -48,  # Clean Monday
    -8,   # Lazarus Saturday
    -7,   # Palm Sunday
    -6, -5, -4, -3, -2, -1,  # Holy Week
    0,    # Pascha
    1, 2, 3, 4, 5, 6,  # Bright Week
    7,    # Thomas Sunday
    14,   # Myrrhbearing Women
    24,   # Mid-Pentecost
    39,   # Ascension
    49,   # Pentecost
    50,   # Monday of Holy Spirit
    56,   # All Saints
}


def greg_to_julian_key(greg_date: date) -> str:
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return f"{julian.month:02d}-{julian.day:02d}"


def build_mapping(scraped_data: dict, lang: str):
    fixed = {}
    moveable = {}

    for greg_key, day in scraped_data.items():
        month, day_num = int(greg_key[:2]), int(greg_key[3:])
        greg_date = date(YEAR, month, day_num)
        pdist = (greg_date - PASCHA_2026).days
        julian_key = greg_to_julian_key(greg_date)
        desc = day['description']

        entry = {"description": desc, "fasting": day['fasting']}
        if lang == 'sr':
            entry["isRed"] = day.get('isRed', False)
            entry["isBold"] = day.get('isBold', False)
        else:
            entry["isMajorFeast"] = day.get('isMajorFeast', False)
            entry["fastingFull"] = day.get('fastingFull', '')
            entry["prayer"] = day.get('prayer', '')
            entry["liturgicalNote"] = day.get('liturgicalNote', '')

        if pdist in MOVEABLE_DISTANCES:
            moveable[str(pdist)] = entry
            # DON'T add to fixed — these dates change yearly
        else:
            fixed[julian_key] = entry

    return fixed, moveable


def main():
    import html as html_mod
    import re

    def clean(text):
        text = html_mod.unescape(text)
        # Strip month name prefixes
        text = re.sub(r'^(ЈАНУАР|ФЕБРУАР|МАРТ|АПРИЛ|МАЈ|ЈУН|ЈУЛ|АВГУСТ|СЕПТЕМБАР|ОКТОБАР|НОВЕМБАР|ДЕЦЕМБАР)\s*–\s*', '', text)
        return text.strip()

    # Serbian
    with open('OrthodoxCalendar/Localization/sr_calendar_2026.json') as f:
        sr_data = json.load(f)['days']

    sr_fixed, sr_moveable = build_mapping(sr_data, 'sr')
    # Clean all descriptions
    for entry in sr_fixed.values():
        entry['description'] = clean(entry['description'])
    for entry in sr_moveable.values():
        entry['description'] = clean(entry['description'])

    sr_output = {
        "source": "crkvenikalendar.rs",
        "fixedByJulianDate": sr_fixed,
        "moveableByPaschaDistance": sr_moveable,
    }
    with open('OrthodoxCalendar/Localization/sr_saints_map.json', 'w') as f:
        json.dump(sr_output, f, ensure_ascii=False, indent=2)
    print(f"Serbian: {len(sr_fixed)} fixed + {len(sr_moveable)} moveable", file=sys.stderr)

    # Russian
    with open('OrthodoxCalendar/Localization/ru_calendar_2026.json') as f:
        ru_data = json.load(f)['days']

    ru_fixed, ru_moveable = build_mapping(ru_data, 'ru')
    for entry in ru_fixed.values():
        entry['description'] = clean(entry['description'])
    for entry in ru_moveable.values():
        entry['description'] = clean(entry['description'])

    ru_output = {
        "source": "days.pravoslavie.ru",
        "fixedByJulianDate": ru_fixed,
        "moveableByPaschaDistance": ru_moveable,
    }
    with open('OrthodoxCalendar/Localization/ru_saints_map.json', 'w') as f:
        json.dump(ru_output, f, ensure_ascii=False, indent=2)
    print(f"Russian: {len(ru_fixed)} fixed + {len(ru_moveable)} moveable", file=sys.stderr)


if __name__ == "__main__":
    main()
