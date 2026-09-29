#!/usr/bin/env python3
"""
Check the SPC fasting engine against the SPC's own calendar.

Compares fasting_engine.compute_fasting(..., locale="sr") with every day in
data/processed/sr/pravoslavno_fasting.json (pravoslavno.rs, "Календар поста")
and exits 1 when agreement drops below FLOOR. This replaces the "93% match" the
project used to cite, which was measured against the month table's "пост"
marker — a word that also appears on Pascha and all of Bright Week, so it never
compared a level at all.

Usage: python3 scripts/serbian/validate_spc_fasting.py [--all]
"""
import collections, os, sys
from datetime import date

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "shared"))
from pravoslavno_levels import load_fixture, pravoslavno_level  # noqa: E402
from paschalion import Paschalion  # noqa: E402
import fasting_engine as fe  # noqa: E402

FLOOR = 0.99


def source_gap(d, p, entry, got, want):
    """A day where pravoslavno.rs's page leaves information out rather than
    stating a rule.

    A Transfiguration on a weekend is printed as the Dormition Fast's plain
    weekend — УЉЕ, and no feast name at all — while every weekday
    Transfiguration says РИБА and names the feast. Fish on a weekday but oil on a
    weekend would invert every other rule on the page, so the engine keeps fish
    and these days are reported apart from real disagreements.
    """
    return (p.fixed_month_day(d) == (8, 6) and d.weekday() >= 5 and not entry.get("note")
            and want == fe.HOT_WITH_OIL and got == fe.FISH)


def main():
    fixture = load_fixture()
    pasch = {}
    by_period = collections.defaultdict(lambda: [0, 0])
    misses, gaps = [], []
    for ds, entry in sorted(fixture.items()):
        d = date.fromisoformat(ds)
        p = pasch.setdefault(d.year, Paschalion(d.year))
        got = fe.compute_fasting(d, p, "sr")
        want = pravoslavno_level(entry)
        cell = by_period[fe.spc_period(d, p)]
        cell[1] += 1
        if got == want:
            cell[0] += 1
        elif source_gap(d, p, entry, got, want):
            cell[0] += 1
            gaps.append(ds)
        else:
            misses.append((ds, want, got, entry.get("note")))
    ok = sum(c[0] for c in by_period.values())
    n = sum(c[1] for c in by_period.values())
    years = sorted({k[:4] for k in fixture})
    print(f"SPC fasting vs pravoslavno.rs, {years[0]}-{years[-1]}: {ok}/{n} = {100 * ok / n:.2f}%")
    if gaps:
        print(f"  (counted as agreeing: {len(gaps)} weekend Transfigurations the page prints"
              f" without the feast — {', '.join(gaps)})")
    for period, (a, b) in sorted(by_period.items()):
        print(f"  {period:16s} {a:5d}/{b:<5d}")
    for ds, want, got, note in (misses if "--all" in sys.argv else misses[:40]):
        print(f"  {ds} {date.fromisoformat(ds):%a}: calendar {want}, engine {got}  {note or ''}")
    if ok / n < FLOOR:
        sys.exit(f"agreement {100 * ok / n:.2f}% is below the {100 * FLOOR:.0f}% floor")


if __name__ == "__main__":
    main()
