"""
Reading pravoslavno.rs fasting markers as engine levels.

Shared by derive_spc_fasting.py and validate_spc_fasting.py so the two cannot
disagree about what the SPC calendar says.
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from fasting_engine import (STRICTNESS, TOTAL_ABSTINENCE, DRY_EATING, HOT_NO_OIL,  # noqa: E402
                            HOT_WITH_OIL, FISH, FREE)

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "sr",
                       "pravoslavno_fasting.json")

MARKER_LEVEL = {
    "СУХО": DRY_EATING,
    "ВОДА": HOT_NO_OIL,
    "ВИНО": HOT_NO_OIL,     # wine without oil: the engine has no wine-only level
    "УЉЕ": HOT_WITH_OIL,
    "РИБА": FISH,
    "БЕЛИ МРС": FISH,       # Cheese Week: dairy, eggs and fish; fish is the nearest level
    "ЦВЕТИ": FISH,          # Palm Sunday
    "БОЖИЋ": FREE,
    "ВАСКРС": FREE,
}


def load_fixture() -> dict:
    return json.load(open(FIXTURE, encoding="utf-8"))


def pravoslavno_level(entry: dict) -> str:
    """The level the SPC calendar shows for one day.

    Several markers on one day (Vidovdan on a Wednesday shows ВОДА and РИБА)
    mean the feast lifts the weekday: the most permissive wins. An unmarked day
    is free — except the no-food days inside Lent, which the page also leaves
    unmarked and annotates "Уздржање" (abstinence).
    """
    levels = [MARKER_LEVEL[m] for m in entry.get("markers", []) if m in MARKER_LEVEL]
    if levels:
        return max(levels, key=lambda lvl: STRICTNESS[lvl])
    if "Уздржање" in (entry.get("note") or ""):
        return TOTAL_ABSTINENCE
    return FREE
