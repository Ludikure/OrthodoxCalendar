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


# ─── Julian Date Helpers ───

JULIAN_OFFSET = 13

def to_julian(greg_date: date) -> tuple:
    """Convert Gregorian date to Julian (month, day)."""
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return (julian.month, julian.day)


# ─── Fixed Date Exceptions ───

def check_fixed_exceptions(greg_date: date, fasting_period: Optional[str]) -> Optional[str]:
    """Check for specific fixed-date fasting exceptions."""
    jm, jd = to_julian(greg_date)

    # Annunciation (Mar 25 Julian = Apr 7 Gregorian) — always fish, even during Lent
    # Exception: during Holy Week, Annunciation allows fish but not on Great Friday
    if jm == 3 and jd == 25:
        return FISH

    # Transfiguration (Aug 6 Julian = Aug 19 Gregorian) — fish during Dormition Fast
    if jm == 8 and jd == 6:
        return FISH

    # Nativity Eve (Dec 24 Julian = Jan 6 Gregorian) — strict
    if jm == 12 and jd == 24:
        return HOT_NO_OIL

    # Theophany Eve (Jan 5 Julian = Jan 18 Gregorian) — strict
    if jm == 1 and jd == 5:
        return HOT_NO_OIL

    # Beheading of St John Baptist (Aug 29 Julian = Sep 11 Gregorian) — strict
    if jm == 8 and jd == 29:
        return HOT_WITH_OIL

    # Elevation of Cross (Sep 14 Julian = Sep 27 Gregorian) — strict
    if jm == 9 and jd == 14:
        return HOT_WITH_OIL

    return None


# ─── Movable Date Exceptions ───

def check_movable_exceptions(greg_date: date, pasch: Paschalion) -> Optional[str]:
    """Check for movable-date fasting exceptions."""
    pdist = pasch.pascha_distance(greg_date)

    # Clean Monday — total abstinence
    if pdist == -48:
        return TOTAL_ABSTINENCE

    # Lazarus Saturday — fish roe (not fish)
    if pdist == -8:
        return FISH_ROE

    # Palm Sunday — fish
    if pdist == -7:
        return FISH

    return None


# ─── Feast Rank Upgrade ───

def upgrade_fasting(base_level: str, feast_rank: Optional[str]) -> str:
    """A higher-ranked feast can relax the fasting level."""
    if feast_rank is None:
        return base_level

    if feast_rank == "great":
        # Great feasts always allow fish, except during Holy Week
        if STRICTNESS.get(base_level, 5) < STRICTNESS[FISH]:
            return FISH
        return base_level

    if feast_rank in ("vigil", "polyeleos"):
        # Upgrade dry eating or hot-no-oil to oil
        if base_level in (DRY_EATING, HOT_NO_OIL):
            return HOT_WITH_OIL
        return base_level

    return base_level


# ─── Main Computation ───

def compute_fasting(greg_date: date, pasch: Paschalion,
                    feast_rank: Optional[str] = None) -> str:
    """
    Compute the fasting level for a given Gregorian date.

    Args:
        greg_date: The Gregorian calendar date
        pasch: Paschalion instance for the year
        feast_rank: Optional feast rank ("great", "vigil", "polyeleos", None)

    Returns:
        One of: "totalAbstinence", "dryEating", "hotNoOil", "hotWithOil",
                "fish", "fishRoe", "free"
    """
    dow = DOW_NAMES[greg_date.weekday()]  # 0=Mon..6=Sun

    # Step 1: Check fast-free weeks
    if pasch.is_fast_free_week(greg_date):
        return FREE

    # Step 2: Check Cheese Week (Maslenitsa) — special rules
    if pasch.is_cheese_week(greg_date):
        return CHEESE_WEEK_RULES[dow]

    # Step 3: Check movable date exceptions (Clean Monday, Lazarus Sat, Palm Sun)
    movable_exc = check_movable_exceptions(greg_date, pasch)
    if movable_exc is not None:
        return movable_exc

    # Step 4: Determine fasting period and get base rule
    period = pasch.get_fasting_period(greg_date)

    if period == "great_lent":
        if pasch.is_holy_week(greg_date):
            base = HOLY_WEEK_RULES[dow]
            # Annunciation during Holy Week: special handling
            jm, jd = to_julian(greg_date)
            if jm == 3 and jd == 25 and base != TOTAL_ABSTINENCE:
                return FISH
            return base  # No feast upgrades during Holy Week
        else:
            base = GREAT_LENT_RULES[dow]

    elif period == "apostles_fast":
        base = APOSTLES_FAST_RULES[dow]

    elif period == "dormition_fast":
        base = DORMITION_FAST_RULES[dow]

    elif period == "nativity_fast":
        sub = pasch.get_nativity_fast_sub_period(greg_date)
        if sub == 2:
            base = NATIVITY_FAST_PERIOD2_RULES[dow]
        else:
            base = NATIVITY_FAST_PERIOD1_RULES[dow]

    else:
        # Regular week
        base = REGULAR_WEEK_RULES[dow]

    # Step 5: Check fixed date exceptions
    fixed_exc = check_fixed_exceptions(greg_date, period)
    if fixed_exc is not None:
        # Use the more permissive of base rule and exception
        if STRICTNESS.get(fixed_exc, 5) > STRICTNESS.get(base, 5):
            base = fixed_exc

    # Step 6: Apply feast rank upgrade
    final = upgrade_fasting(base, feast_rank)

    return final


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
        DRY_EATING: "вода",
        HOT_NO_OIL: "вода",
        HOT_WITH_OIL: "уље",
        FISH: "риба",
        FISH_ROE: "риба",  # SPC: no distinction
        FREE: "мрс",
    },
    "ru": {
        TOTAL_ABSTINENCE: "*",
        DRY_EATING: "вода",
        HOT_NO_OIL: "вода",
        HOT_WITH_OIL: "елей",
        FISH: "рыба",
        FISH_ROE: "икра",
        FREE: "б/п",
    },
    "en": {
        TOTAL_ABSTINENCE: "*",
        DRY_EATING: "water",
        HOT_NO_OIL: "water",
        HOT_WITH_OIL: "oil",
        FISH: "fish",
        FISH_ROE: "roe",
        FREE: "n/r",
    },
}

FASTING_ICONS = {
    TOTAL_ABSTINENCE: "🚫",
    DRY_EATING: "💧",
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
