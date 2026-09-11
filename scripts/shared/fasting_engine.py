#!/usr/bin/env python3
"""
Algorithmic Orthodox Fasting Engine.

Computes the fasting level for any date based on the Typikon rules.
7 levels from strictest to most permissive:

    totalAbstinence  → No food (Clean Monday, Great Friday)
    dryEating        → Сухоядение: bread, water, raw fruit/veg, nuts — no cooking
    hotNoOil         → Горячая без масла: cooked food, no oil, no wine
    hotWithOil       → Горячая с маслом: cooked food with oil, wine permitted
    fish             → Рыба: fish, oil, wine permitted
    fishRoe          → Икра: fish roe only, no fish (Lazarus Saturday)
    free             → Мрсно / Без поста: no restrictions

Usage:
    from paschalion import Paschalion
    from fasting_engine import compute_fasting
    p = Paschalion(2026)
    level = compute_fasting(date(2026, 4, 10), p)  # "totalAbstinence" (Great Friday)
"""

from datetime import date, timedelta
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion
from spc_fasting_relaxations import SPC_RELAXATIONS, SPC_LENT_FEASTS


# ─── Fasting Level Constants ───

TOTAL_ABSTINENCE = "totalAbstinence"
DRY_EATING = "dryEating"
HOT_NO_OIL = "hotNoOil"
HOT_WITH_OIL = "hotWithOil"
FISH = "fish"
FISH_ROE = "fishRoe"
FREE = "free"

# Strictness ordering (lower = stricter)
STRICTNESS = {
    TOTAL_ABSTINENCE: 0,
    DRY_EATING: 1,
    HOT_NO_OIL: 2,
    HOT_WITH_OIL: 3,
    FISH: 4,
    FISH_ROE: 4,  # same level as fish
    FREE: 5,
}

# Day of week indices (0=Mon..6=Sun)
DOW_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


# ─── Fasting Period Rules ───

GREAT_LENT_RULES = {
    "mon": DRY_EATING,
    "tue": HOT_NO_OIL,
    "wed": DRY_EATING,
    "thu": HOT_NO_OIL,
    "fri": DRY_EATING,
    "sat": HOT_WITH_OIL,
    "sun": HOT_WITH_OIL,
}

HOLY_WEEK_RULES = {
    "mon": DRY_EATING,    # Great Monday
    "tue": DRY_EATING,    # Great Tuesday
    "wed": DRY_EATING,    # Great Wednesday
    "thu": HOT_WITH_OIL,  # Great Thursday
    "fri": TOTAL_ABSTINENCE,  # Great Friday
    "sat": HOT_NO_OIL,    # Great Saturday
}

APOSTLES_FAST_RULES = {
    "mon": HOT_NO_OIL,
    "tue": HOT_WITH_OIL,
    "wed": DRY_EATING,
    "thu": HOT_WITH_OIL,
    "fri": DRY_EATING,
    "sat": FISH,
    "sun": FISH,
}

DORMITION_FAST_RULES = {
    "mon": DRY_EATING,
    "tue": HOT_NO_OIL,
    "wed": DRY_EATING,
    "thu": HOT_NO_OIL,
    "fri": DRY_EATING,
    "sat": HOT_WITH_OIL,
    "sun": HOT_WITH_OIL,
}

NATIVITY_FAST_PERIOD1_RULES = {
    # Nov 15 - Dec 19 Julian (less strict)
    "mon": HOT_NO_OIL,
    "tue": FISH,
    "wed": DRY_EATING,
    "thu": FISH,
    "fri": DRY_EATING,
    "sat": FISH,
    "sun": FISH,
}

NATIVITY_FAST_PERIOD2_RULES = {
    # Dec 20-24 Julian (stricter)
    "mon": DRY_EATING,
    "tue": HOT_NO_OIL,
    "wed": DRY_EATING,
    "thu": HOT_NO_OIL,
    "fri": DRY_EATING,
    "sat": HOT_WITH_OIL,
    "sun": HOT_WITH_OIL,
}

REGULAR_WEEK_RULES = {
    "mon": FREE,
    "tue": FREE,
    "wed": HOT_WITH_OIL,  # Wednesday fast
    "thu": FREE,
    "fri": HOT_WITH_OIL,  # Friday fast
    "sat": FREE,
    "sun": FREE,
}

CHEESE_WEEK_RULES = {
    # No meat, but dairy/eggs/fish ok every day
    "mon": FISH,
    "tue": FISH,
    "wed": FISH,
    "thu": FISH,
    "fri": FISH,
    "sat": FISH,
    "sun": FISH,
}


# ─── SPC (Serbian Orthodox Church) ───
#
# The reference is the SPC's own calendar: pravoslavno.rs's "Календар поста",
# scraped into data/processed/sr/pravoslavno_fasting.json by
# scripts/serbian/scrape_pravoslavno_fasting.py and checked against this engine
# by scripts/serbian/validate_spc_fasting.py, which CI runs. It differs from the
# Russian tables above in more than the Wednesday/Friday rule, so SPC days go
# through their own function (spc_fasting_level) instead of overrides of the
# Russian one:
#
#  - A strict day is "на води" — no oil — not dry eating. The SPC calendar marks
#    dry eating (СУХО) only on three feasts, and only on a weekday.
#  - A feast relaxes a fast by name, not by rank: which feasts, and how far, is
#    the table in spc_fasting_relaxations.py, derived from the SPC calendar by
#    scripts/serbian/derive_spc_fasting.py. The saints data marks 341 of 365
#    days "bold", and upgrading every bold day to oil — what this engine used to
#    do — put oil on nearly every Great Lent weekday. Great feasts are no rule
#    either: the Nativity of the Theotokos keeps a Wednesday on water, the
#    Meeting of the Lord relaxes it to oil, the Dormition to fish, and the
#    Annunciation in Lent only to oil.

# Level by weekday, Monday first.
SPC_WEEK = {
    "regular":         (FREE, FREE, HOT_NO_OIL, FREE, HOT_NO_OIL, FREE, FREE),
    "paschal":         (FREE, FREE, HOT_WITH_OIL, FREE, HOT_WITH_OIL, FREE, FREE),
    "great_lent":      (HOT_NO_OIL,) * 5 + (HOT_WITH_OIL, HOT_WITH_OIL),
    "apostles_fast":   (HOT_NO_OIL, HOT_WITH_OIL, HOT_NO_OIL, HOT_WITH_OIL, HOT_NO_OIL, FISH, FISH),
    "dormition_fast":  (HOT_NO_OIL,) * 5 + (HOT_WITH_OIL, HOT_WITH_OIL),
    "nativity_fast_1": (HOT_WITH_OIL, HOT_WITH_OIL, HOT_NO_OIL, HOT_WITH_OIL, HOT_NO_OIL, FISH, FISH),
    "nativity_fast_2": (HOT_NO_OIL,) * 5 + (HOT_WITH_OIL, HOT_WITH_OIL),
}

# Holy Week, by pascha distance (Great Monday is -6).
SPC_HOLY_WEEK = {-6: HOT_NO_OIL, -5: HOT_NO_OIL, -4: HOT_NO_OIL,
                 -3: HOT_WITH_OIL, -2: TOTAL_ABSTINENCE, -1: HOT_NO_OIL}

# Movable days that set their own level, by pascha distance.
SPC_MOVABLE = {
    -48: TOTAL_ABSTINENCE,  # Clean Monday — "Уздржање"
    -47: TOTAL_ABSTINENCE,  # Clean Tuesday — "Уздржање"
    -46: TOTAL_ABSTINENCE,  # Clean Wednesday — "Уздржање до вечери"
    -18: HOT_WITH_OIL,      # Wednesday of the fifth week
    -17: HOT_WITH_OIL,      # Thursday of the Great Canon: oil and wine
    -16: HOT_NO_OIL,        # Friday of the fifth week: wine without oil — the nearest level we have
    -7: FISH,               # Palm Sunday
}

# Strict feasts (Julian month, day): dry eating on a weekday, oil on a weekend.
SPC_STRICT_FEASTS = {(1, 5): "Theophany Eve", (8, 29): "Beheading of St John the Baptist",
                     (9, 14): "Exaltation of the Cross"}
SPC_CHRISTMAS_EVE = (12, 24)    # oil, on any weekday
SPC_PETROVDAN_EVE = (6, 28)     # no oil on a weekday, even the Apostles' Fast's oil days
SPC_NATIVITY_STRICT_FROM = 19   # the Nativity Fast's strict stretch starts on Dec 19 (Julian)


def spc_period(greg_date: date, pasch: Paschalion) -> str:
    """The SPC period a date belongs to — the key into SPC_WEEK, or
    "fast_free"/"cheese"."""
    if pasch.is_fast_free_week(greg_date):
        return "fast_free"
    if pasch.is_cheese_week(greg_date):
        return "cheese"
    period = pasch.get_fasting_period(greg_date)
    if period == "nativity_fast":
        jm, jd = pasch.fixed_month_day(greg_date)
        return "nativity_fast_2" if jm == 12 and jd >= SPC_NATIVITY_STRICT_FROM else "nativity_fast_1"
    if period:
        return period
    return "paschal" if 0 < pasch.pascha_distance(greg_date) < 49 else "regular"


def spc_fasting_level(greg_date: date, pasch: Paschalion,
                      relaxations=None, lent_feasts=None) -> str:
    """The SPC fasting level for a date.

    relaxations, lent_feasts: the feast table and the feasts in it that also lift
    a day of Great Lent; default to the generated ones. Pass {} and set() to get
    the period level alone, which is what the derivation compares against.
    """
    if relaxations is None:
        relaxations = SPC_RELAXATIONS
    if lent_feasts is None:
        lent_feasts = SPC_LENT_FEASTS
    period = spc_period(greg_date, pasch)
    if period == "fast_free":
        return FREE
    if period == "cheese":
        return FISH  # БЕЛИ МРС: dairy, eggs and fish; fish is the nearest level
    jm, jd = pasch.fixed_month_day(greg_date)
    dow = greg_date.weekday()
    if (jm, jd) in SPC_STRICT_FEASTS:
        return HOT_WITH_OIL if dow >= 5 else DRY_EATING
    if (jm, jd) == SPC_CHRISTMAS_EVE:
        return HOT_WITH_OIL

    pdist = pasch.pascha_distance(greg_date)
    if pdist in SPC_MOVABLE:
        level = SPC_MOVABLE[pdist]
    elif -6 <= pdist <= -1:
        level = SPC_HOLY_WEEK[pdist]
    else:
        level = SPC_WEEK[period][dow]

    if (jm, jd) == SPC_PETROVDAN_EVE and dow < 5 and STRICTNESS[level] > STRICTNESS[HOT_NO_OIL]:
        level = HOT_NO_OIL  # at a weekend the fast's fish stands

    # A feast lifts a fast; it never imposes one, and never lifts the no-food
    # days. Great Lent keeps its level except for the few feasts that lift it
    # there too: St Haralampios relaxes an ordinary Wednesday to oil, but not a
    # Lenten one.
    relaxed = relaxations.get((jm, jd))
    if period == "great_lent" and (jm, jd) not in lent_feasts:
        relaxed = None
    if pdist == -1:
        relaxed = None  # Great Saturday keeps its water, even on the Annunciation (2029)
    if relaxed and level not in (FREE, TOTAL_ABSTINENCE) and STRICTNESS[relaxed] > STRICTNESS[level]:
        level = relaxed
    return level


# ─── Julian Date Helpers ───

JULIAN_OFFSET = 13

def to_julian(greg_date: date) -> tuple:
    """Convert Gregorian date to Julian (month, day)."""
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return (julian.month, julian.day)


# ─── Fixed Date Exceptions ───

def check_fixed_exceptions(greg_date: date, pasch: Paschalion,
                           locale: str = "ru") -> Optional[str]:
    """Fixed-date feasts that relax a Russian/OCA fast.

    Only relax: compute_fasting keeps whichever of this and the day's rule is more
    permissive. Strict days, which impose a fast, are strict_feast_level.

    Keyed by the fixed-cycle (Julian) month-day, which the Paschalion resolves
    for the calendar in use — the same feast, 13 days earlier in Gregorian terms
    on the Revised calendar.
    """
    jm, jd = pasch.fixed_month_day(greg_date)

    # Annunciation (Mar 25 Julian = Apr 7 Gregorian)
    if jm == 3 and jd == 25:
        return FISH

    # Transfiguration (Aug 6 Julian = Aug 19 Gregorian) — fish during Dormition Fast
    if jm == 8 and jd == 6:
        return FISH

    # Nativity Eve (Dec 24 Julian = Jan 6 Gregorian) — strict
    if jm == 12 and jd == 24:
        return HOT_NO_OIL

    # Dormition of Theotokos (Aug 15 Julian = Aug 28 Gregorian)
    # On a regular Fri, SPC relaxes to fish for this great feast
    if jm == 8 and jd == 15:
        return FISH

    # Nativity of St John Baptist (Jun 24 Julian = Jul 7 Gregorian)
    if jm == 6 and jd == 24:
        return FISH  # Great feast during Apostles' Fast

    # Ваведење (Entry of Theotokos, Nov 21 Julian = Dec 4 Gregorian)
    if jm == 11 and jd == 21:
        return FISH  # Feast day during Nativity Fast

    # Св. Никола (St Nicholas, Dec 6 Julian = Dec 19 Gregorian)
    if jm == 12 and jd == 6:
        return FISH  # Николдан during Nativity Fast

    return None


# ─── Movable Date Exceptions ───

def check_movable_exceptions(greg_date: date, pasch: Paschalion,
                             locale: str = "ru") -> Optional[str]:
    """Check for movable-date fasting exceptions."""
    pdist = pasch.pascha_distance(greg_date)

    # Clean Monday — total abstinence
    if pdist == -48:
        return TOTAL_ABSTINENCE

    # Lazarus Saturday
    if pdist == -8:
        return FISH_ROE

    # Palm Sunday — fish
    if pdist == -7:
        return FISH

    return None


# ─── Feast Rank Upgrade ───

def upgrade_fasting(base_level: str, feast_rank: Optional[str],
                    locale: str = "ru") -> str:
    """A great feast relaxes a Russian/OCA fast to fish.

    SPC days never come through here: which feasts relax an SPC fast, and how
    far, is named per feast in spc_fasting_relaxations.py rather than ranked.
    """
    if feast_rank == "great" and STRICTNESS.get(base_level, 5) < STRICTNESS[FISH]:
        return FISH
    return base_level


def strict_feast_level(greg_date: date, pasch: Paschalion) -> Optional[str]:
    """Russian/OCA strict feasts, which impose a fast on any weekday.

    They used to sit among the fixed-date exceptions, which can only relax a
    day's rule — so on a Monday or a Saturday, when the rule is no fast at all,
    the Beheading and the Exaltation came out as free, and a great feast's fish
    upgrade could still reach them on a Wednesday. Levels are what both sources
    show: pravoslavie.ru (Russian) gives oil on all three in 2026; orthocal.info
    (OCA) gives oil on the Beheading and the Exaltation on every weekday, and on
    Theophany Eve only at a weekend, a strict fast otherwise.
    """
    jm, jd = pasch.fixed_month_day(greg_date)
    if (jm, jd) in ((8, 29), (9, 14)):
        return HOT_WITH_OIL
    if (jm, jd) == (1, 5):
        return HOT_WITH_OIL if greg_date.weekday() >= 5 else HOT_NO_OIL
    return None


# ─── Main Computation ───

def compute_fasting(greg_date: date, pasch: Paschalion,
                    feast_rank: Optional[str] = None,
                    locale: str = "ru") -> str:
    """
    Compute the fasting level for a given Gregorian date.

    Args:
        greg_date: The Gregorian calendar date
        pasch: Paschalion instance for the year (new_calendar=True for en_nc)
        feast_rank: "great" on a great feast, which relaxes a Russian/OCA fast
            to fish; SPC days ignore it (see spc_fasting_level)
        locale: "sr" for the SPC calendar, anything else for Russian/OCA rules

    Returns:
        One of: "totalAbstinence", "dryEating", "hotNoOil", "hotWithOil",
                "fish", "fishRoe", "free"
    """
    if locale == "sr":
        return spc_fasting_level(greg_date, pasch)

    dow = DOW_NAMES[greg_date.weekday()]

    # Step 1: fast-free weeks
    if pasch.is_fast_free_week(greg_date):
        return FREE

    # Step 2: strict feasts impose their level, whatever the weekday or rank
    strict = strict_feast_level(greg_date, pasch)
    if strict is not None:
        return strict

    # Step 3: Cheese Week (Maslenitsa)
    if pasch.is_cheese_week(greg_date):
        return CHEESE_WEEK_RULES[dow]

    # Step 4: movable exceptions (Clean Monday, Lazarus Saturday, Palm Sunday)
    movable_exc = check_movable_exceptions(greg_date, pasch, locale)
    if movable_exc is not None:
        return movable_exc

    # Step 5: the period's rule for this weekday
    period = pasch.get_fasting_period(greg_date)
    if period == "great_lent":
        if pasch.is_holy_week(greg_date):
            base = HOLY_WEEK_RULES[dow]
            jm, jd = pasch.fixed_month_day(greg_date)
            if jm == 3 and jd == 25 and base != TOTAL_ABSTINENCE:
                return FISH  # Annunciation during Holy Week
            return base  # No feast upgrades during Holy Week
        base = GREAT_LENT_RULES[dow]
    elif period == "apostles_fast":
        base = APOSTLES_FAST_RULES[dow]
    elif period == "dormition_fast":
        base = DORMITION_FAST_RULES[dow]
    elif period == "nativity_fast":
        sub = pasch.get_nativity_fast_sub_period(greg_date)
        base = (NATIVITY_FAST_PERIOD2_RULES if sub == 2 else NATIVITY_FAST_PERIOD1_RULES)[dow]
    else:
        base = REGULAR_WEEK_RULES[dow]

    # Step 6: fixed-date feasts that relax the rule
    fixed_exc = check_fixed_exceptions(greg_date, pasch, locale)
    if fixed_exc is not None and STRICTNESS.get(fixed_exc, 5) > STRICTNESS.get(base, 5):
        base = fixed_exc

    # Step 7: a great feast relaxes to fish
    return upgrade_fasting(base, feast_rank, locale)


# ─── Localized Labels ───

FASTING_LABELS = {
    "sr": {
        TOTAL_ABSTINENCE: ("Потпуно уздржање", "Без хране"),
        DRY_EATING: ("Сухоједење", "Хлеб, воће, поврће, орашасти плодови — без кувања"),
        HOT_NO_OIL: ("Кувано без уља", "Кувана храна без уља и вина"),
        HOT_WITH_OIL: ("Уље дозвољено", "Кувана храна са уљем, вино дозвољено"),
        FISH: ("Риба дозвољена", "Риба, уље, вино дозвољени"),
        FISH_ROE: ("Риба дозвољена", "Риба, уље, вино дозвољени"),  # SPC treats fishRoe same as fish
        FREE: ("Без поста", "Нема ограничења у исхрани"),
    },
    "ru": {
        TOTAL_ABSTINENCE: ("Полное воздержание", "Без пищи"),
        DRY_EATING: ("Сухоядение", "Хлеб, фрукты, овощи, орехи — без тепловой обработки"),
        HOT_NO_OIL: ("Горячая без масла", "Варёная пища без растительного масла и вина"),
        HOT_WITH_OIL: ("С растительным маслом", "Варёная пища с маслом, вино разрешено"),
        FISH: ("Рыба разрешена", "Рыба, масло, вино разрешены"),
        FISH_ROE: ("Икра разрешена", "Рыбная икра разрешена, рыба нет"),
        FREE: ("Без поста", "Нет ограничений в пище"),
    },
    "en": {
        TOTAL_ABSTINENCE: ("Total Abstinence", "No food"),
        DRY_EATING: ("Dry Eating", "Bread, fruit, vegetables, nuts — no cooking"),
        HOT_NO_OIL: ("Hot food without oil", "Cooked food, no oil, no wine"),
        HOT_WITH_OIL: ("Oil allowed", "Cooked food with oil, wine permitted"),
        FISH: ("Fish allowed", "Fish, oil, wine permitted"),
        FISH_ROE: ("Fish roe allowed", "Fish roe only, no fish"),
        FREE: ("No fast", "No dietary restrictions"),
    },
}

FASTING_ABBREV = {
    "sr": {
        TOTAL_ABSTINENCE: "*",
        DRY_EATING: "суво",
        HOT_NO_OIL: "вода",
        HOT_WITH_OIL: "уље",
        FISH: "риба",
        FISH_ROE: "риба",  # SPC: no distinction
        FREE: "мрс",
    },
    "ru": {
        TOTAL_ABSTINENCE: "*",
        DRY_EATING: "сухо",
        HOT_NO_OIL: "вода",
        HOT_WITH_OIL: "елей",
        FISH: "рыба",
        FISH_ROE: "икра",
        FREE: "не пост",
    },
    "en": {
        TOTAL_ABSTINENCE: "*",
        DRY_EATING: "dry",
        HOT_NO_OIL: "water",
        HOT_WITH_OIL: "oil",
        FISH: "fish",
        FISH_ROE: "roe",
        FREE: "n/r",
    },
}

FASTING_ICONS = {
    TOTAL_ABSTINENCE: "🚫",
    DRY_EATING: "🍞",
    HOT_NO_OIL: "💧",
    HOT_WITH_OIL: "🫒",
    FISH: "🐟",
    FISH_ROE: "🐟",
    FREE: "✓",
}


def get_fasting_info(level: str, locale: str = "sr") -> dict:
    """Get full fasting info for a level and locale."""
    labels = FASTING_LABELS.get(locale, FASTING_LABELS["en"])
    abbrevs = FASTING_ABBREV.get(locale, FASTING_ABBREV["en"])
    label, explanation = labels.get(level, (level, ""))
    return {
        "type": level,
        "label": label,
        "explanation": explanation,
        "abbrev": abbrevs.get(level, ""),
        "icon": FASTING_ICONS.get(level, ""),
    }


# ─── Validation ───

def validate_fasting():
    """Validate fasting against known dates."""
    p = Paschalion(2026)

    tests = [
        (date(2026, 4, 10), None, TOTAL_ABSTINENCE, "Great Friday"),
        (date(2026, 2, 23), None, TOTAL_ABSTINENCE, "Clean Monday"),
        (date(2026, 4, 5), None, FISH, "Palm Sunday"),
        (date(2026, 4, 4), None, FISH_ROE, "Lazarus Saturday"),
        (date(2026, 4, 12), None, FREE, "Pascha"),
        (date(2026, 4, 13), None, FREE, "Bright Monday"),
        (date(2026, 3, 4), None, DRY_EATING, "Wed of 2nd week of Lent"),
        (date(2026, 3, 7), None, HOT_WITH_OIL, "Sat of 2nd week of Lent"),
        (date(2026, 4, 7), None, FISH, "Annunciation during Holy Week"),
        (date(2026, 8, 19), None, FISH, "Transfiguration during Dormition"),
        (date(2026, 1, 7), None, FREE, "Nativity — Svyatki"),
        (date(2026, 5, 31), None, FREE, "Pentecost"),
        (date(2026, 6, 1), None, FREE, "Trinity Week"),
    ]

    passed = 0
    for d, rank, expected, desc in tests:
        result = compute_fasting(d, p, rank)
        status = "✓" if result == expected else "✗"
        if result != expected:
            print(f"  {status} {desc} ({d}): expected {expected}, got {result}")
        else:
            passed += 1

    print(f"Fasting validation: {passed}/{len(tests)} passed.")
    return passed == len(tests)


if __name__ == "__main__":
    validate_fasting()

    print("\n=== Sample fasting levels for April 2026 ===")
    p = Paschalion(2026)
    for day in range(1, 13):
        d = date(2026, 4, day)
        level = compute_fasting(d, p)
        info = get_fasting_info(level, "sr")
        dow = ["Пн", "Ут", "Ср", "Чт", "Пт", "Сб", "Нд"][d.weekday()]
        print(f"  {d} {dow}: {info['abbrev']:<5} {info['label']:<25} ({level})")
