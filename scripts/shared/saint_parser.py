#!/usr/bin/env python3
"""
Saint Name Parser & Hierarchy Ranking.

Parses raw saint text from scraped calendar pages into ranked, structured entries.
Supports both Russian (HTML-structure-based) and Serbian (text-analysis-based) pipelines.

Output per day: list of Feast objects with:
    - name: cleaned saint/feast name
    - importance: "great" / "vigil" / "polyeleos" / "bold" / "normal"
    - displayRole: "primary" / "secondary" / "tertiary"
    - type: saint type ("apostle", "martyr", "venerable", etc.)
    - isSlava: bool (Serbian only)
    - liturgicalContext: optional parenthetical text
"""

import re
from typing import Optional


# ─── Title Rank System ───

TITLE_RANK = {
    # Serbian / Russian variants → rank score (lower = more important)
    "апостол": 1,
    "великомученик": 2, "великомученица": 2,
    "великомученик/ца": 2, "великомученик/ица": 2,
    "святитель": 2, "светитељ": 2,
    "равноапостольный": 2, "равноапостолни": 2,
    "преподобный": 3, "преподобни": 3, "преподобна": 3,
    "священномученик": 3, "свештеномученик": 3,
    "мученик": 4, "мученица": 4,
    "праведный": 4, "праведни": 4, "праведна": 4,
    "блаженный": 4, "блажени": 4, "блажена": 4, "блаженная": 4,
    "исповедник": 4,
    "собор": 5, "сабор": 5,
}

# Abbreviation → full title mapping
ABBREVIATIONS = {
    # Serbian
    "Прп.": "Преподобни", "Мч.": "Мученик", "Мц.": "Мученица",
    "Свт.": "Светитељ", "Сщмч.": "Свештеномученик",
    "Вмч.": "Великомученик", "Вмц.": "Великомученица",
    "Прмч.": "Преподобномученик", "Блж.": "Блажени",
    "Преп.": "Преподобни", "Св.": "Свети",
    # Russian
    "Прп.": "Преподобный", "Сщмч.": "Священномученик",
    "Свт.": "Святитель", "Вмч.": "Великомученик", "Вмц.": "Великомученица",
    "Прмч.": "Преподобномученик", "Блж.": "Блаженный",
    "Блгв.": "Благоверный", "Равноап.": "Равноапостольный",
    "Ап.": "Апостол", "Мч.": "Мученик", "Мц.": "Мученица",
}

RANK_KEYWORDS = {
    "великий праздник": "great", "велики празник": "great",
    "двунадесятый": "great", "двунадесети": "great",
    "бдение": "vigil", "бденије": "vigil",
    "полиелей": "polyeleos", "полијелеј": "polyeleos",
    "славословие": "doxology", "славословије": "doxology",
    "красное": "red_letter", "црвено слово": "red_letter",
}

# 12 Great Feasts by Julian date
GREAT_FEASTS_JULIAN = {
    "09-08": "nativity-of-theotokos",
    "09-14": "elevation-of-cross",
    "11-21": "presentation-of-theotokos",
    "12-25": "nativity-of-christ",
    "01-06": "theophany",
    "02-02": "meeting-of-lord",
    "03-25": "annunciation",
    "08-06": "transfiguration",
    "08-15": "dormition",
}

RANK_ORDER = {
    "great": 0, "vigil": 1, "polyeleos": 2,
    "red_letter": 2, "doxology": 3, "bold": 4, "normal": 5,
}


# ─── Type Detection ───

def detect_saint_type(name: str) -> str:
    """Detect saint type from name prefixes/abbreviations."""
    name_lower = name.lower().strip()

    type_map = [
        (["апостол", "ап."], "apostle"),
        (["великомученик", "великомученица", "вмч.", "вмц."], "great_martyr"),
        (["святитель", "светитељ", "свт."], "hierarch"),
        (["равноапостольный", "равноапостолни", "равноап."], "equal_to_apostles"),
        (["преподобный", "преподобни", "преподобна", "прп.", "преп."], "venerable"),
        (["священномученик", "свештеномученик", "сщмч."], "hieromartyr"),
        (["преподобномученик", "прмч."], "venerable_martyr"),
        (["мученик", "мученица", "мч.", "мц."], "martyr"),
        (["праведный", "праведни", "праведна"], "righteous"),
        (["блаженный", "блажени", "блж."], "blessed"),
        (["исповедник"], "confessor"),
        (["благоверный", "благоверна", "блгв."], "noble"),
        (["пророк", "пророчица"], "prophet"),
        (["собор", "сабор"], "synaxis"),
    ]

    for prefixes, stype in type_map:
        for prefix in prefixes:
            if name_lower.startswith(prefix):
                return stype

    # Check for feast keywords
    feast_keywords = [
        "рождество", "богојављење", "богоявление", "сретење", "сретение",
        "благовещение", "благовести", "преображење", "преображение",
        "успение", "успење", "воздвижение", "воздвижење", "введение",
        "ваведење", "покров", "вход господень", "вознесение", "вазнесење",
        "пятидесятница", "духови", "воскресение", "васкрс",
    ]
    for kw in feast_keywords:
        if kw in name_lower:
            return "feast"

    return "saint"


# ─── Main Parser ───

def parse_saints_text(raw_text: str, julian_key: Optional[str] = None,
                       html_bold: Optional[list] = None,
                       html_red: Optional[list] = None,
                       html_italic: Optional[list] = None) -> list:
    """
    Parse raw saint text into ranked, structured entries.

    Args:
        raw_text: semicolon-separated saint names
        julian_key: "MM-DD" Julian date for great feast detection
        html_bold: list of names that had <b> tags in source HTML
        html_red: list of names that had red color in source HTML
        html_italic: list of names that had <i> tags (Serbian saints)

    Returns:
        List of feast dicts sorted by importance, with displayRole assigned.
    """
    html_bold = html_bold or []
    html_red = html_red or []
    html_italic = html_italic or []

    # Check for great feast override
    is_great_feast_day = julian_key in GREAT_FEASTS_JULIAN if julian_key else False

    # Split on semicolons
    raw_entries = [e.strip() for e in raw_text.split(";") if e.strip()]

    feasts = []
    for i, entry in enumerate(raw_entries):
        feast = {
            "name": entry,
            "position": i,
            "importance": "normal",
            "type": "saint",
            "liturgicalContext": None,
            "isSlava": False,
        }

        # Extract parenthetical context
        paren_match = re.search(r'\(([^)]+)\)', entry)
        if paren_match:
            feast["liturgicalContext"] = paren_match.group(1)
            feast["name"] = re.sub(r'\s*\([^)]+\)', '', entry).strip()

        # Check СЛАВА marker
        if "СЛАВА" in entry:
            feast["isSlava"] = True
            feast["name"] = re.sub(r'СЛАВА\s*', '', feast["name"]).strip()

        # Check HTML formatting
        name_clean = feast["name"]
        if any(name_clean in b or b in name_clean for b in html_bold):
            feast["importance"] = "bold"
        if any(name_clean in r or r in name_clean for r in html_red):
            feast["importance"] = "great"

        # Detect saint type
        feast["type"] = detect_saint_type(name_clean)

        # Parse title prefix for rank
        name_lower = name_clean.lower()
        for prefix, rank in TITLE_RANK.items():
            if prefix in name_lower:
                if feast["importance"] == "normal" and rank <= 2:
                    feast["importance"] = "bold"
                break

        # Check for rank keywords
        for keyword, rank in RANK_KEYWORDS.items():
            if keyword in name_lower:
                feast["importance"] = rank
                break

        # Check for collective entries → never promote
        if any(word in name_lower for word in ["собор", "сабор", "светих ", "святых "]):
            if re.search(r'\d{3,}', entry):  # numbers like 20,000
                feast["importance"] = "normal"

        # Mark Serbian saints
        if any(name_clean in it or it in name_clean for it in html_italic):
            feast["serbianSaint"] = True

        feasts.append(feast)

    # Great feast override
    if is_great_feast_day:
        feast_id = GREAT_FEASTS_JULIAN[julian_key]
        # Find which entry is the great feast, or mark the first one
        found_great = False
        for f in feasts:
            if f["type"] == "feast":
                f["importance"] = "great"
                found_great = True
                break
        if not found_great and feasts:
            feasts[0]["importance"] = "great"

    # Position-based ranking: first entry is at minimum "bold"
    if feasts and feasts[0]["importance"] == "normal":
        feasts[0]["importance"] = "bold"

    # Sort by importance (stable sort preserves position for equal ranks)
    feasts.sort(key=lambda f: RANK_ORDER.get(f["importance"], 5))

    # Assign display roles
    if feasts:
        feasts[0]["displayRole"] = "primary"
    if len(feasts) > 1:
        feasts[1]["displayRole"] = "secondary"
    for f in feasts[2:]:
        f["displayRole"] = "tertiary"

    return feasts


def parse_azbyka_saints(saint_items: list) -> list:
    """
    Parse saints from azbyka.ru HTML structure.

    Args:
        saint_items: list of dicts with keys:
            - name: saint name text
            - level: ideograph level (1=great, 6-7=normal)
            - is_bold: bool
            - has_liturgika_icon: bool

    Returns:
        List of feast dicts sorted by importance with displayRole.
    """
    feasts = []
    for i, item in enumerate(saint_items):
        importance = "normal"
        if item.get("has_liturgika_icon") or item.get("level", 7) <= 2:
            importance = "great"
        elif item.get("is_bold") or item.get("level", 7) <= 4:
            importance = "bold"

        feast = {
            "name": item["name"],
            "position": i,
            "importance": importance,
            "type": detect_saint_type(item["name"]),
            "displayRole": "tertiary",
            "liturgicalContext": None,
            "isSlava": False,
        }

        # Extract parenthetical context
        paren_match = re.search(r'\(([^)]+)\)', item["name"])
        if paren_match:
            feast["liturgicalContext"] = paren_match.group(1)
            feast["name"] = re.sub(r'\s*\([^)]+\)', '', item["name"]).strip()

        feasts.append(feast)

    # Sort and assign roles
    feasts.sort(key=lambda f: RANK_ORDER.get(f["importance"], 5))
    if feasts:
        feasts[0]["displayRole"] = "primary"
    if len(feasts) > 1:
        feasts[1]["displayRole"] = "secondary"
    for f in feasts[2:]:
        f["displayRole"] = "tertiary"

    return feasts


# ─── Saint Type Labels ───

SAINT_TYPE_LABELS = {
    "sr": {
        "apostle": "Апостол",
        "great_martyr": "Великомученик",
        "hierarch": "Светитељ",
        "equal_to_apostles": "Равноапостолни",
        "venerable": "Преподобни",
        "hieromartyr": "Свештеномученик",
        "venerable_martyr": "Преподобномученик",
        "martyr": "Мученик",
        "righteous": "Праведни",
        "blessed": "Блажени",
        "confessor": "Исповедник",
        "noble": "Благоверни",
        "prophet": "Пророк",
        "synaxis": "Сабор",
        "feast": "Празник",
        "saint": "Свети",
    },
    "ru": {
        "apostle": "Апостол",
        "great_martyr": "Великомученик",
        "hierarch": "Святитель",
        "equal_to_apostles": "Равноапостольный",
        "venerable": "Преподобный",
        "hieromartyr": "Священномученик",
        "venerable_martyr": "Преподобномученик",
        "martyr": "Мученик",
        "righteous": "Праведный",
        "blessed": "Блаженный",
        "confessor": "Исповедник",
        "noble": "Благоверный",
        "prophet": "Пророк",
        "synaxis": "Собор",
        "feast": "Праздник",
        "saint": "Святой",
    },
    "en": {
        "apostle": "Apostle",
        "great_martyr": "Great Martyr",
        "hierarch": "Holy Hierarch",
        "equal_to_apostles": "Equal-to-Apostles",
        "venerable": "Venerable",
        "hieromartyr": "Hieromartyr",
        "venerable_martyr": "Venerable Martyr",
        "martyr": "Martyr",
        "righteous": "Righteous",
        "blessed": "Blessed",
        "confessor": "Confessor",
        "noble": "Right-believing",
        "prophet": "Prophet",
        "synaxis": "Synaxis",
        "feast": "Feast",
        "saint": "Saint",
    },
}


def get_type_label(saint_type: str, locale: str = "sr") -> str:
    """Get localized label for a saint type."""
    return SAINT_TYPE_LABELS.get(locale, SAINT_TYPE_LABELS["en"]).get(saint_type, saint_type)


# ─── Validation ───

if __name__ == "__main__":
    # Test Serbian parsing
    test_sr = "СЛАВА Свети Игњатије Богоносац; Свети Јован Кронштатски; Свети Данило Други, архипископ српски (Претпразништво Рождества)"
    result = parse_saints_text(test_sr)
    print("=== Serbian parsing test ===")
    for f in result:
        print(f"  [{f['displayRole']}] {f['importance']}: {f['name']} (type={f['type']}, slava={f['isSlava']})")

    # Test Russian parsing
    test_ru = "Рождество Господа Бога и Спаса нашего Иисуса Христа; Преставление сщмч. Леонида, еп. Марийского; Поклонение волхвов"
    result2 = parse_saints_text(test_ru, julian_key="12-25")
    print("\n=== Russian parsing test (Nativity) ===")
    for f in result2:
        print(f"  [{f['displayRole']}] {f['importance']}: {f['name']} (type={f['type']})")

    # Test azbyka parsing
    test_azbyka = [
        {"name": "Рождество Господа Бога и Спаса нашего Иисуса Христа", "level": 1, "is_bold": False, "has_liturgika_icon": True},
        {"name": "Преставление сщмч. Леонида Серебренникова, пресвитера", "level": 7, "is_bold": False, "has_liturgika_icon": False},
    ]
    result3 = parse_azbyka_saints(test_azbyka)
    print("\n=== Azbyka parsing test ===")
    for f in result3:
        print(f"  [{f['displayRole']}] {f['importance']}: {f['name']} (type={f['type']})")
