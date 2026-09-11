#!/usr/bin/env python3
"""
Check the Russian and English fasting against the calendar each locale follows.

Compares fasting_engine.compute_fasting(..., locale) for ru, en and en_nc with
every day of their fixtures (scripts/shared/reference_fasting.py: days.pravoslavie.ru,
holytrinityorthodox.com, orthocal.info) and exits 1 when a locale falls below its
floor. The floors sit just under what the derived tables reach on the fixture;
scripts/shared/derive_fasting.py --holdout reports how well they predict a year
the derivation never saw, which is the number to quote.

Usage: python3 scripts/shared/validate_fasting.py [--all]
"""
import collections, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fasting_engine as fe  # noqa: E402
import reference_fasting as ref  # noqa: E402
from paschalion import Paschalion  # noqa: E402

# Each just under what the tables reach on their fixture (2026-09-11: ru 99.45%,
# en 99.42%, en_nc 99.92%).
FLOOR = {"ru": 0.99, "en": 0.99, "en_nc": 0.995}
NEW_CALENDAR = {"ru": False, "en": False, "en_nc": True}


def check(locale):
    pasch = {}
    by_segment = collections.defaultdict(lambda: [0, 0])
    misses = []
    for ds, entry in sorted(ref.load(locale).items()):
        want = ref.level(locale, entry)
        if want is None:
            continue
        d = date.fromisoformat(ds)
        p = pasch.setdefault(d.year, Paschalion(d.year, new_calendar=NEW_CALENDAR[locale]))
        got = fe.compute_fasting(d, p, locale)
        cell = by_segment[fe.table_segment(d, p)]
        cell[1] += 1
        if ref.agrees(locale, want, got):
            cell[0] += 1
        else:
            misses.append((ds, want, got))
    ok = sum(c[0] for c in by_segment.values())
    n = sum(c[1] for c in by_segment.values())
    years = sorted({int(k[:4]) for k in ref.load(locale)})
    print(f"{locale} fasting vs {ref.SOURCE[locale]}, {years[0]}-{years[-1]}: {ok}/{n} = {100 * ok / n:.2f}%")
    for segment, (a, b) in sorted(by_segment.items()):
        print(f"  {segment:15s} {a:5d}/{b:<5d}")
    for ds, want, got in (misses if "--all" in sys.argv else misses[:15]):
        print(f"  {ds} {date.fromisoformat(ds):%a}: calendar {want}, engine {got}")
    return ok / n


def main():
    failed = [f"{loc} {100 * r:.2f}% < {100 * FLOOR[loc]:.0f}%"
              for loc in ("ru", "en", "en_nc") for r in [check(loc)] if r < FLOOR[loc]]
    if failed:
        sys.exit("below the floor: " + "; ".join(failed))


if __name__ == "__main__":
    main()
