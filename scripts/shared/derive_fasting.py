#!/usr/bin/env python3
"""
Derive the Russian and English fasting tables (scripts/shared/fasting_tables.py)
from each locale's own calendar — the counterpart of
scripts/serbian/derive_spc_fasting.py.

A day takes its season segment's level for its weekday
(fasting_engine.table_segment), unless its day of the Pascha cycle sets its own
(Clean Monday, Great Friday, Lazarus Saturday …), and then whatever the feast on its
fixed church date does — lift the fast, or impose one, as the Beheading does. All
three are read off the reference calendar (scripts/shared/reference_fasting.py):
the level a segment and weekday takes most often; the Pascha-cycle days that take
one other level in at least two thirds of the years; and, for each fixed date and
segment, what the day became on a weekday and at a weekend.

  python3 scripts/shared/derive_fasting.py            write the tables for ru, en, en_nc
  python3 scripts/shared/derive_fasting.py --holdout  also derive each year's tables
      without that year and report how well they predict it: the honest measure of
      a year nobody has scraped.
"""
import collections, math, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fasting_engine as fe  # noqa: E402
import reference_fasting as ref  # noqa: E402
from paschalion import Paschalion  # noqa: E402

LOCALES = ("ru", "en", "en_nc")
NEW_CALENDAR = {"ru": False, "en": False, "en_nc": True}
SEGMENTS = ("fast_free", "cheese", "great_lent", "holy_week", "nativity_1", "nativity_2",
            "nativity_3", "apostles_fast", "dormition_fast", "paschal", "summer_autumn",
            "triodion", "winter")
OUT = os.path.join(HERE, "fasting_tables.py")
_P = {}


def pasch(year, new_calendar):
    if (year, new_calendar) not in _P:
        _P[(year, new_calendar)] = Paschalion(year, new_calendar=new_calendar)
    return _P[(year, new_calendar)]


def observations(locale, exclude=()):
    obs = []
    for ds, entry in ref.load(locale).items():
        d = date.fromisoformat(ds)
        want = ref.level(locale, entry)
        if d.year in exclude or want is None:
            continue
        p = pasch(d.year, NEW_CALENDAR[locale])
        obs.append((d, fe.table_segment(d, p), p.pascha_distance(d), p.fixed_month_day(d), want))
    return obs


def _cls(weekday):
    """Wednesday and Friday, the other weekdays, the weekend: a feast that lifts a
    Wednesday leaves a free Monday alone, and a weekend has rules of its own."""
    return "we" if weekday >= 5 else ("wf" if weekday in (2, 4) else "wd")


def _week(obs, skip):
    counts = collections.defaultdict(collections.Counter)
    for i, (d, seg, _, _, want) in enumerate(obs):
        if i not in skip:
            counts[(seg, d.weekday())][want] += 1
    week = {}
    for seg in SEGMENTS:
        whole = sum((counts[(seg, w)] for w in range(7)), collections.Counter())
        fallback = whole.most_common(1)[0][0] if whole else fe.FREE
        week[seg] = tuple(counts[(seg, w)].most_common(1)[0][0] if counts[(seg, w)] else fallback
                          for w in range(7))
    return week


# The Typikon's own rule for three days of Lent and Holy Week, taken wherever it
# agrees with everything the calendar says about them: the OCA prints Clean Monday
# and Great Friday only as "strict" and leaves the degree open, and
# days.pravoslavie.ru prints no diet line at all on Great Saturday.
PRIOR = {-48: fe.TOTAL_ABSTINENCE, -2: fe.TOTAL_ABSTINENCE, -1: fe.HOT_NO_OIL}


def _movable(obs, week, locale):
    by = collections.defaultdict(list)
    for d, seg, pd, _, want in obs:
        if -70 <= pd <= 60:
            by[pd].append((want, week[seg][d.weekday()]))
    movable = {}
    for pd, vals in by.items():
        level, n = collections.Counter(w for w, _ in vals).most_common(1)[0]
        if level != vals[0][1] and n >= 2 and n >= math.ceil(2 * len(vals) / 3):
            movable[pd] = level
    for pd, level in PRIOR.items():
        if all(ref.agrees(locale, want, level) for want, _ in by.get(pd, [])):
            movable[pd] = level
    return movable


LEVELS = (fe.TOTAL_ABSTINENCE, fe.DRY_EATING, fe.HOT_NO_OIL, fe.HOT_WITH_OIL, fe.FISH, fe.FISH_ROE, fe.FREE)
# In order of preference on a tie: no effect, then the narrowest effect that fits.
CANDIDATES = ([None] + [("relax", l) for l in LEVELS] + [("impose", l) for l in LEVELS]
              + [("set", l) for l in LEVELS])


def _apply(effect, level):
    if effect is None or level == fe.TOTAL_ABSTINENCE:   # as fasting_engine.table_fasting_level
        return level
    return fe.apply_feast_effect(effect, level)


def _fixed(obs, week, movable, locale):
    """For each fixed date, segment and weekday class, the effect — none, relax to
    a level, impose a level — that agrees with the most observed years. Ties go to
    no effect: a feast has to show itself to get an entry."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for d, seg, pd, (jm, jd), want in obs:
        by[(jm, jd, seg)][_cls(d.weekday())].append((movable.get(pd, week[seg][d.weekday()]), want))
    fixed = {}
    for key, classes in by.items():
        effect = {}
        for cls, pairs in classes.items():
            effect[cls] = max(CANDIDATES, key=lambda c: sum(ref.agrees(locale, w, _apply(c, b)) for b, w in pairs))
        if any(v is not None for v in effect.values()):
            fixed[key] = effect
    return fixed


def _explained(obs, week, movable, fixed, locale):
    skip = set()
    for i, (d, seg, pd, (jm, jd), want) in enumerate(obs):
        if pd in movable:
            skip.add(i); continue
        effect = fixed.get((jm, jd, seg), {}).get(_cls(d.weekday()))
        base = week[seg][d.weekday()]
        if effect is not None and _apply(effect, base) != base:
            skip.add(i)
    return skip


def derive(locale, exclude=()):
    obs = observations(locale, exclude)
    week = _week(obs, set())
    for _ in range(3):
        movable = _movable(obs, week, locale)
        fixed = _fixed(obs, week, movable, locale)
        week = _week(obs, _explained(obs, week, movable, fixed, locale))
    movable = _movable(obs, week, locale)
    return {"week": week, "movable": movable, "fixed": _fixed(obs, week, movable, locale)}


def score(locale, tables, years=None):
    ok = n = 0
    misses = []
    for d, seg, pd, jmd, want in observations(locale):
        if years and d.year not in years:
            continue
        got = fe.table_fasting_level(d, pasch(d.year, NEW_CALENDAR[locale]), tables)
        n += 1
        if ref.agrees(locale, want, got):
            ok += 1
        else:
            misses.append((d, seg, want, got))
    return ok, n, misses


def write(result, years):
    lines = ['"""',
             "Fasting tables for the Russian and English calendars.",
             "",
             "Generated by scripts/shared/derive_fasting.py from each locale's own calendar",
             "(scripts/shared/reference_fasting.py). Do not edit by hand: refresh the",
             "fixture and re-run the script.",
             "",
             "week:    level by season segment (fasting_engine.table_segment), Monday first.",
             "movable: days of the Pascha cycle, by distance from Pascha, that set their own level.",
             "fixed:   (church month, day, segment) -> what that date's feast does on a Wednesday or",
             "         Friday (\"wf\"), another weekday (\"wd\") and at a weekend (\"we\"):",
             "         (\"relax\", level) lifts a stricter day to that level, (\"impose\", level)",
             "         holds a freer one to it, (\"set\", level) is that level either way, None",
             "         leaves the day. See fasting_engine.apply_feast_effect.",
             '"""',
             "",
             "FASTING_TABLES = {"]
    for locale in LOCALES:
        t = result[locale]
        lines.append(f'    "{locale}": {{  # {ref.SOURCE[locale]}, {years[locale][0]}-{years[locale][-1]}')
        lines.append('        "week": {')
        for seg in SEGMENTS:
            lines.append(f'            "{seg}": {t["week"][seg]!r},')
        lines.append("        },")
        lines.append('        "movable": {' + ", ".join(f"{pd}: {lvl!r}" for pd, lvl in sorted(t["movable"].items())) + "},")
        lines.append('        "fixed": {')
        for key in sorted(t["fixed"]):
            lines.append(f"            {key!r}: {dict(sorted(t['fixed'][key].items()))!r},")
        lines.append("        },")
        lines.append("    },")
    lines.append("}")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    holdout = "--holdout" in sys.argv
    result, years = {}, {}
    for locale in LOCALES:
        result[locale] = derive(locale)
        years[locale] = sorted({d.year for d, *_ in observations(locale)})
        ok, n, _ = score(locale, result[locale])
        t = result[locale]
        print(f"{locale}: {len(t['movable'])} Pascha-cycle days, {len(t['fixed'])} feast entries, "
              f"{years[locale][0]}-{years[locale][-1]}: in-sample {ok}/{n} = {100 * ok / n:.2f}%")
        if holdout:
            for y in years[locale]:
                ok, n, _ = score(locale, derive(locale, exclude=(y,)), {y})
                print(f"    holdout {y}: {ok}/{n} = {100 * ok / n:.2f}%")
    write(result, years)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
