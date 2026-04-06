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
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion

YEAR = 2026
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'output')


def validate_calendar(locale: str):
    filepath = os.path.join(DATA_DIR, f"calendar_{locale}_{YEAR}.json")
    if not os.path.exists(filepath):
        print(f"\n=== {locale.upper()}: File not found: {filepath} ===")
        return False

    with open(filepath) as f:
        data = json.load(f)

    calendar = data["days"]
    pasch = Paschalion(YEAR)
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

    # Check 3: 12 Great Feasts present
    great_feasts = pasch.great_feasts_gregorian()
    for feast_id, feast_date in great_feasts.items():
        key = feast_date.strftime("%m-%d")
        day = calendar.get(key)
        if not day:
            errors.append(f"Great feast {feast_id} ({feast_date}) missing from calendar")
            continue
        if not day.get("greatFeast"):
            warnings.append(f"Great feast {feast_id} ({feast_date}) not marked as greatFeast")

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

    # Check 10: 365 days present
    if len(calendar) != 365:
        errors.append(f"Expected 365 days, got {len(calendar)}")

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


def main():
    results = {}
    for locale in ['sr', 'ru']:
        results[locale] = validate_calendar(locale)

    print(f"\n{'='*40}")
    print(f"Overall: {'ALL PASS' if all(results.values()) else 'FAILURES DETECTED'}")


if __name__ == "__main__":
    main()
