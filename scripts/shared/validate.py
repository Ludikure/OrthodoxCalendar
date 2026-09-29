#!/usr/bin/env python3
"""
Validation — Cross-check generated calendar data.

Checks:
1. Every day has at least one primary feast entry
2. Great feast days have importance "great" on primary entry
3. No day has more than one "great" importance entry (except Pascha coincidences)
4. Fasting levels make sense (no free days during Great Lent, etc.)
5. Readings exist for most days
6. Movable feasts are on correct dates
7. 12 Great Feasts present with correct dates
"""

import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion
import fixed_cycle

YEAR = 2026
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'output')


# Fixed great feasts by the Gregorian date they must fall on in each calendar
# style: Julian month-day for the Revised calendar, +13 days for the Old one.
FIXED_GREAT_DATES = {
    "nativity-of-christ": (12, 25), "theophany": (1, 6), "meeting-of-lord": (2, 2),
    "annunciation": (3, 25), "transfiguration": (8, 6), "dormition": (8, 15),
    "nativity-of-theotokos": (9, 8), "elevation-of-cross": (9, 14),
    "presentation-of-theotokos": (11, 21),
}

# Every id the greatFeast field can legitimately hold: the nine fixed ones, the
# three that follow Pascha, and Pascha itself. Used to tell a real mis-marking
# apart from two great feasts landing on one date.
GREAT_FEAST_IDS = set(FIXED_GREAT_DATES) | {
    "pascha", "entry-into-jerusalem", "ascension", "pentecost",
}


def validate_calendar(locale: str, year: int = None, directory: str = None):
    year = year or YEAR
    filepath = os.path.join(directory or DATA_DIR, f"calendar_{locale}_{year}.json")
    if not os.path.exists(filepath):
        print(f"\n=== {locale.upper()}: File not found: {filepath} ===")
        return False

    with open(filepath) as f:
        data = json.load(f)

    calendar = data["days"]
    new_calendar = (locale == 'en_nc')
    pasch = Paschalion(year, new_calendar=new_calendar)
    errors = []
    warnings = []

    print(f"\n=== Validating {locale.upper()} ({len(calendar)} days) ===")

    # Check 1: Every day has at least one feast entry
    days_without_feasts = 0
    for key, day in calendar.items():
        if not day.get("feasts"):
            days_without_feasts += 1
    if days_without_feasts > 0:
        warnings.append(f"{days_without_feasts} days without feast entries")

    # Check 2: Every day with feasts has a primary displayRole
    days_without_primary = 0
    for key, day in calendar.items():
        feasts = day.get("feasts", [])
        if feasts and not any(f.get("displayRole") == "primary" for f in feasts):
            days_without_primary += 1
            if days_without_primary <= 3:
                errors.append(f"  {key}: has feasts but no primary displayRole")
    if days_without_primary > 0:
        errors.append(f"{days_without_primary} days with feasts but no primary entry")

    # Check 3: all 12 Great Feasts are marked on the day they fall on.
    # great_feasts_gregorian() is calendar-style aware, so this covers the
    # Revised calendar's dates too; the moveable ones (Entry, Ascension,
    # Pentecost) are only covered here — Check 11 handles the fixed ones.
    great_feasts = pasch.great_feasts_gregorian()
    for feast_id, feast_date in great_feasts.items():
        key = feast_date.strftime("%m-%d")
        day = calendar.get(key)
        if not day:
            errors.append(f"Great feast {feast_id} ({feast_date}) missing from calendar")
        elif not day.get("greatFeast"):
            errors.append(f"Great feast {feast_id} ({feast_date}) not marked as greatFeast")
        elif day["greatFeast"] != feast_id:
            # A day carries one greatFeast, and two of them do legitimately land
            # on the same date: Annunciation falls on Palm Sunday in 2058, 2069
            # and 2080, and the pipeline marks the fixed one. Another great
            # feast's ID here is that coincidence, worth a note; anything else is
            # bad data. (Kyriopascha — Pascha on Annunciation, 2075 and 2086 —
            # never reaches this branch: Pascha is not one of the twelve, so the
            # only feast checked on that date is Annunciation, which is exactly
            # what the day is marked with.)
            other = day["greatFeast"]
            if other in GREAT_FEAST_IDS:
                warnings.append(f"{key}: {feast_id} shares the day with greatFeast {other!r}")
            else:
                errors.append(f"{key}: greatFeast is {other!r}, expected {feast_id!r}")

    # Check 4: Pascha present
    pascha_key = pasch.pascha.strftime("%m-%d")
    pascha_day = calendar.get(pascha_key)
    if not pascha_day:
        errors.append(f"Pascha ({pasch.pascha}) missing!")
    elif pascha_day.get("fasting", {}).get("type") != "free":
        errors.append(f"Pascha should be fast-free, got {pascha_day.get('fasting', {}).get('type')}")

    # Check 5: Great Friday is total abstinence
    gf_key = pasch.great_friday.strftime("%m-%d")
    gf_day = calendar.get(gf_key)
    if gf_day and gf_day.get("fasting", {}).get("type") != "totalAbstinence":
        errors.append(f"Great Friday should be totalAbstinence, got {gf_day.get('fasting', {}).get('type')}")

    # Check 6: Clean Monday is total abstinence
    cm_key = pasch.clean_monday.strftime("%m-%d")
    cm_day = calendar.get(cm_key)
    if cm_day and cm_day.get("fasting", {}).get("type") != "totalAbstinence":
        errors.append(f"Clean Monday should be totalAbstinence, got {cm_day.get('fasting', {}).get('type')}")

    # Check 7: Bright Week is fast-free
    for i in range(7):
        bw = pasch.pascha + timedelta(days=i)
        bw_key = bw.strftime("%m-%d")
        bw_day = calendar.get(bw_key)
        if bw_day and bw_day.get("fasting", {}).get("type") != "free":
            warnings.append(f"Bright Week day {bw} should be free, got {bw_day.get('fasting', {}).get('type')}")

    # Check 8: No free days during Great Lent (except Annunciation, Palm Sunday, Lazarus Saturday)
    lent_free = []
    current = pasch.great_lent_start
    while current <= pasch.great_saturday:
        key = current.strftime("%m-%d")
        day = calendar.get(key)
        if day and day.get("fasting", {}).get("type") == "free":
            lent_free.append(current)
        current += timedelta(days=1)
    if lent_free:
        errors.append(f"{len(lent_free)} free days during Great Lent: {lent_free[:3]}...")

    # Check 9: Readings coverage
    days_with_readings = sum(1 for d in calendar.values() if d.get("readings"))
    if days_with_readings < 200:
        warnings.append(f"Only {days_with_readings} days have readings (expected 300+)")

    # Check 10: every day of the year present (366 in a leap year)
    expected_days = (date(year, 12, 31) - date(year, 1, 1)).days + 1
    if len(calendar) != expected_days:
        errors.append(f"Expected {expected_days} days, got {len(calendar)}")

    # Check 11: each fixed great feast falls on its own date, exactly once.
    # en_nc used to carry the Old Calendar's saints as well as the Revised
    # great feasts, so every fixed great feast appeared twice — 13 days apart.
    offset = 0 if new_calendar else 13
    for feast_id, (jm, jd) in FIXED_GREAT_DATES.items():
        want = (date(year, jm, jd) + timedelta(days=offset)).strftime("%m-%d")
        on = [k for k, d in calendar.items() if d.get("greatFeast") == feast_id]
        if want in calendar and on != [want]:
            other = calendar[want].get("greatFeast")
            # Defensive: the fixed feast is marked nowhere and its own date
            # carries a different great feast, i.e. the moveable one won the day.
            # The pipeline currently always prefers the fixed feast, so no year
            # in 2024-2099 reaches this — Check 3 above catches the real
            # collisions. Kept as a downgrade so a future ordering change warns
            # instead of failing the build on correct data.
            if not on and other in GREAT_FEAST_IDS:
                warnings.append(f"{feast_id}: shares {want} with greatFeast {other!r}")
            else:
                errors.append(f"{feast_id}: expected only {want}, found {on or 'none'}")
    # The injected great feast's own name must not also appear on another day —
    # that is what a mis-keyed fixed cycle looks like (en_nc carried each of them
    # twice, 13 days apart). Scraped sources do mark several entries "great" on a
    # single day, so counting those would flag legitimate sr/ru data instead.
    for key, day in calendar.items():
        # Only the injected fixed great feast, which is always feast 0. Saints
        # legitimately recur (a repose and a translation of relics), so checking
        # any "great"-marked entry would flag those.
        if day.get("greatFeast") not in FIXED_GREAT_DATES or not day.get("feasts"):
            continue
        primary = day["feasts"][0]["name"]
        elsewhere = [k for k, d in calendar.items() if k != key
                     and any(f.get("name") == primary for f in d.get("feasts", []))]
        if elsewhere:
            errors.append(f"{primary[:40]!r} appears on {key} and also {elsewhere[:2]}")

    # Check 12: a great feast is never inside its own fast, and the fixed fasts
    # start where this calendar style puts them.
    nativity = (date(year, 12, 25) + timedelta(days=offset)).strftime("%m-%d")
    if nativity in calendar and calendar[nativity].get("fastingPeriod"):
        errors.append(f"Nativity ({nativity}) is inside {calendar[nativity]['fastingPeriod']}")
    dormition = (date(year, 8, 15) + timedelta(days=offset)).strftime("%m-%d")
    if dormition in calendar and calendar[dormition].get("fastingPeriod") == "dormition_fast":
        errors.append(f"Dormition ({dormition}) is inside its own fast")
    nf_start = (date(year, 11, 15) + timedelta(days=offset)).strftime("%m-%d")
    if nf_start in calendar and calendar[nf_start].get("fastingPeriod") != "nativity_fast":
        errors.append(f"Nativity Fast does not start on {nf_start}")

    # Report
    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ✗ {e}")
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    ⚠ {w}")
    if not errors and not warnings:
        print("  All checks passed! ✓")

    passed = len(errors) == 0
    print(f"\n  Result: {'PASS' if passed else 'FAIL'} ({len(errors)} errors, {len(warnings)} warnings)")
    return passed


MOVING_NAME = re.compile(
    r"Задушнице|Отдание праздника (Пасхи|Преполовения|Вознесения|Пятидесятницы)"
    r"|^(Sunday|Saturday) (before|after)|^Saturday the Nativity|Parents’ Saturday|\(Parental\) Saturday"
    r"|\(movable holiday|\(celebration on the|Week of Holy Forefathers"
    r"|– (Оци|Материце|Детињци|Теодорова субота)$")


def check_fixed_cycle(years, directory=None) -> bool:
    """Checks that need more than one year: a church day carries the same fixed
    commemorations in every year, and nothing that moves sits on a fixed day.

    The saints pools were scraped in one year. Read by the Gregorian date, a leap
    year's February 29 to March 12 came out a church day early; and the sources'
    moving commemorations (memorial Saturdays, the Sundays around the great
    feasts, synaxes kept on "the Sunday nearest") stayed on that year's dates in
    every other year. fixed_cycle.py explains both.
    """
    ok = True
    for locale in ['sr', 'ru', 'en', 'en_nc']:
        by_year = {}
        problems = []
        for year in years:
            path = os.path.join(directory or DATA_DIR, f"calendar_{locale}_{year}.json")
            if not os.path.exists(path):
                continue
            with open(path) as f:
                days = json.load(f)["days"]
            church_days = {}
            for key, day in days.items():
                church = key if locale == 'en_nc' else day["julianDate"]
                church_days[church] = tuple(x["name"] for x in day["feasts"] if not x.get("moveable"))
                for label in ("weekLabel", "liturgicalPeriod", "liturgicalNote"):
                    if day.get(label):
                        problems.append(f"{year}-{key}: {label} copied from the scraped year")
                for x in day["feasts"]:
                    name = x["name"]
                    if not x.get("moveable") and MOVING_NAME.search(name):
                        problems.append(f"{year}-{key}: a moving commemoration on a fixed day: {name[:60]}")
                    if re.match(r"^(Sunday|Неделя|Недеља)\b", name) and day["dayOfWeek"] != 6:
                        problems.append(f"{year}-{key}: a Sunday commemoration on a weekday: {name[:60]}")
                    if name.lstrip().startswith("*"):
                        problems.append(f"{year}-{key}: a rubric listed as a saint: {name[:60]}")
            by_year[year] = church_days
        common = [y for y in by_year if y % 4]
        if common:
            reference = by_year[common[0]]
            for year, church_days in by_year.items():
                for church, names in church_days.items():
                    if church == "02-29":
                        stray = [n for n in names if not fixed_cycle.LEAP_DAY.search(n)]
                        if stray:
                            problems.append(f"{year} church 02-29: not a February 29 commemoration: {stray[0][:50]}")
                        continue
                    want = reference.get(church)
                    if church == "02-28" and year % 4 == 0 and want is not None:
                        want = tuple(n for n in want if not fixed_cycle.LEAP_DAY.search(n))
                    if want is not None and names != want:
                        problems.append(f"{year} church {church}: fixed commemorations differ from {common[0]}'s")
        status = "OK" if not problems else f"{len(problems)} problems"
        print(f"  fixed cycle {locale}: {status}")
        for line in problems[:10]:
            print(f"    {line}")
        ok = ok and not problems
    return ok


def main():
    """validate.py [year|year-year] [--dir=DIR]"""
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    directory = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--dir=')), None)
    if args and '-' in args[0]:
        first, last = (int(x) for x in args[0].split('-'))
        years = range(first, last + 1)
    else:
        years = [int(args[0]) if args else YEAR]
    results = {}
    for year in years:
        for locale in ['sr', 'ru', 'en', 'en_nc']:
            results[f'{locale}{year}'] = validate_calendar(locale, year, directory)

    print(f"\n{'='*40}\nAcross years:")
    ok = check_fixed_cycle(years, directory) and all(results.values())
    print(f"\n{'='*40}")
    print(f"Overall: {'ALL PASS' if ok else 'FAILURES DETECTED'}")
    # Without this the CI step prints FAILURES DETECTED and exits 0, so the
    # data job can never go red — every invariant below was decoration.
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
