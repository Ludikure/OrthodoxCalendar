#!/usr/bin/env python3
"""
Orthodox fasting levels, per locale.

Seven levels from strictest to most permissive:

    totalAbstinence  → No food (Clean Monday, Great Friday)
    dryEating        → Сухоядение: bread, water, raw fruit/veg, nuts — no cooking
    hotNoOil         → Горячая без масла: cooked food, no oil, no wine
    hotWithOil       → Горячая с маслом: cooked food with oil, wine permitted
    fish             → Рыба: fish, oil, wine permitted
    fishRoe          → Икра: fish roe only, no fish (Lazarus Saturday)
    free             → Мрсно / Без поста: no restrictions

Each locale follows its own church's calendar, and each is checked against it:
sr the SPC's (pravoslavno.rs) through spc_fasting_level; ru, en and en_nc the
Russian Church's (days.pravoslavie.ru), ROCOR's (holytrinityorthodox.com) and the
OCA's (orthocal.info) through tables derived from them (table_fasting_level).

Usage:
    from paschalion import Paschalion
    from fasting_engine import compute_fasting
    p = Paschalion(2026)
    level = compute_fasting(date(2026, 4, 10), p, "ru")  # "totalAbstinence" (Great Friday)
"""

from datetime import date, timedelta
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion
from spc_fasting_relaxations import SPC_RELAXATIONS, SPC_LENT_FEASTS
try:
    from fasting_tables import FASTING_TABLES
except ImportError:          # before scripts/shared/derive_fasting.py has run once
    FASTING_TABLES = {}


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


# ─── Russian and English: tables derived from each locale's own calendar ───
#
# ru follows days.pravoslavie.ru, en holytrinityorthodox.com (ROCOR, the source
# of its saints) and en_nc orthocal.info (the OCA, Revised Julian) — see
# scripts/shared/reference_fasting.py. The Russian/OCA rules further down gave all
# three one set of tables, and each calendar disagreed with it on about a fifth of
# its days: oil on every ordinary Wednesday and Friday, where the Russian calendars
# allow fish in winter and the Paschal season and the OCA keeps a strict fast; fish
# on Tuesdays and Thursdays late in the Nativity Fast; one Great Lent for all three.
# As for the SPC, the rules are data: scripts/shared/derive_fasting.py derives each
# locale's tables into fasting_tables.py, and scripts/shared/validate_fasting.py
# (CI) checks them against the calendars.

def table_segment(greg_date: date, pasch: Paschalion) -> str:
    """The season a day belongs to — the key into a locale's weekly table."""
    if pasch.is_fast_free_week(greg_date):
        return "fast_free"
    if pasch.is_cheese_week(greg_date):
        return "cheese"
    period = pasch.get_fasting_period(greg_date)
    pdist = pasch.pascha_distance(greg_date)
    if period == "great_lent":
        return "holy_week" if pdist >= -6 else "great_lent"
    if period == "nativity_fast":
        jm, jd = pasch.fixed_month_day(greg_date)
        if jm == 11 or jd < 6:
            return "nativity_1"        # to St Nicholas
        return "nativity_2" if jd < 20 else "nativity_3"
    if period:
        return period
    if 0 < pdist < 49:
        return "paschal"
    if pdist >= 49:
        return "summer_autumn"
    return "triodion" if pdist >= -70 else "winter"


def table_fasting_level(greg_date: date, pasch: Paschalion, tables: dict) -> str:
    """A day's level from a locale's derived tables: its segment's level for the
    weekday, unless the day of the Pascha cycle sets its own, and then what the
    feast on its fixed church date does on a Wednesday or Friday, another weekday,
    or at a weekend (apply_feast_effect)."""
    segment = table_segment(greg_date, pasch)
    weekday = greg_date.weekday()
    level = tables["movable"].get(pasch.pascha_distance(greg_date), tables["week"][segment][weekday])
    jm, jd = pasch.fixed_month_day(greg_date)
    feast = tables["fixed"].get((jm, jd, segment))
    # No feast lifts a day kept without food (Clean Monday, Great Friday) — the
    # same rule the SPC engine follows. Without it a Clean Monday that falls on
    # the Forty Martyrs took the Lenten weekday's oil.
    if feast and level != TOTAL_ABSTINENCE:
        cls = "we" if weekday >= 5 else ("wf" if weekday in (2, 4) else "wd")
        effect = feast.get(cls)
        if cls not in feast:
            # A weekday class the calendar never showed this feast on borrows a
            # relaxation from another (it cannot make the day stricter), never an
            # imposed level: a dry Wednesday must not make a summer Sunday dry.
            effect = next((e for e in feast.values() if e and e[0] == "relax"), None)
        if effect is not None:
            level = apply_feast_effect(effect, level)
    return level


def apply_feast_effect(effect: tuple, level: str) -> str:
    """("relax", x) lifts a stricter day to x and never makes a day stricter (its
    Wednesday relaxation leaves an ordinary Monday free), as for the SPC;
    ("impose", x) holds a freer day to x (the Beheading); ("set", x) is x either
    way, for a feast whose level does not depend on the weekday's own."""
    kind, target = effect
    if kind == "set":
        return target
    if (kind == "relax") == (STRICTNESS[target] > STRICTNESS[level]):
        return target
    return level


# ─── Main Computation ───

def compute_fasting(greg_date: date, pasch: Paschalion, locale: str = "ru") -> str:
    """
    The fasting level of a Gregorian date in a locale's tradition.

    Args:
        greg_date: The Gregorian calendar date
        pasch: Paschalion instance for the year (new_calendar=True for en_nc)
        locale: "sr" for the SPC's rules (spc_fasting_level); "ru", "en" and
            "en_nc" for the tables derived from their own calendars
            (table_fasting_level, fasting_tables.py)

    Returns:
        One of: "totalAbstinence", "dryEating", "hotNoOil", "hotWithOil",
                "fish", "fishRoe", "free"
    """
    if locale == "sr":
        return spc_fasting_level(greg_date, pasch)
    tables = FASTING_TABLES.get(locale)
    if tables is None:
        raise ValueError(f"no fasting rules for locale {locale!r}; "
                         f"scripts/shared/derive_fasting.py writes ru, en and en_nc")
    return table_fasting_level(greg_date, pasch, tables)


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


if __name__ == "__main__":
    print("The engine is checked against the calendars themselves:\n"
          "  python3 scripts/serbian/validate_spc_fasting.py\n"
          "  python3 scripts/shared/validate_fasting.py")
