#!/usr/bin/env python3
"""
Merge Pipeline — Combines all scraped data into final calendar JSONs.

Inputs:
  - data/processed/sr/saints.json, readings.json
  - data/processed/ru/saints.json, readings.json, reflections.json, fasting.json
  - Paschalion (computed)
  - Fasting Engine (computed)

Outputs:
  - data/output/calendar_sr_2026.json
  - data/output/calendar_ru_2026.json
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from paschalion import Paschalion
from fasting_engine import compute_fasting, get_fasting_info, FASTING_ABBREV, FASTING_ICONS
from generate_readings import generate_all_readings

YEAR_START = 2024
YEAR_END = 2030
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
JULIAN_OFFSET = 13

# Short Serbian book names for readable references
SR_SHORT_BOOK = [
    # Gospels — match both "од Матеја" and "Матеј" forms
    ('Јеванђеље.*Матеј', 'Матеј'),
    ('Матеја', 'Матеј'),
    ('Јеванђеље.*Марк', 'Марко'),
    ('Марка', 'Марко'),
    ('Јеванђеље.*Лук', 'Лука'),
    ('Луке', 'Лука'),
    ('Јеванђеље.*Јован', 'Јован'),
    ('Јована', 'Јован'),
    # Acts
    ('Дела апостолска', 'Дела'),
    ('Дела светих апостола', 'Дела'),
    # Pauline epistles
    ('Јеврејима', 'Јеврејима'),
    ('Римљаним', 'Римљанима'),
    ('Прва.*Коринћаним', '1. Коринћанима'),
    ('Друга.*Коринћаним', '2. Коринћанима'),
    ('Коринћаним', 'Коринћанима'),
    ('Галатим', 'Галатима'),
    ('Ефесцим', 'Ефесцима'),
    ('Филипљаним', 'Филипљанима'),
    ('Колосјаним', 'Колосјанима'),
    ('Колошаним', 'Колосјанима'),
    ('Прва.*Солуњаним', '1. Солуњанима'),
    ('Друга.*Солуњаним', '2. Солуњанима'),
    ('Солуњаним', 'Солуњанима'),
    ('Прва.*Тимотеј', '1. Тимотеју'),
    ('Друга.*Тимотеј', '2. Тимотеју'),
    ('Тимотеју', 'Тимотеју'),
    ('Титу', 'Титу'),
    ('Филимон', 'Филимону'),
    # Catholic epistles
    ('Јаков', 'Јакова'),
    ('Прва.*Петр', '1. Петрова'),
    ('Друга.*Петр', '2. Петрова'),
    ('Петр', 'Петрова'),
    ('Јуд', 'Јуда'),
    ('Откривењ', 'Откривење'),
    # Pentateuch (Књига Мојсијева)
    ('Прва књига Мојсијева', 'Постање'),
    ('Друга књига Мојсијев', 'Излазак'),
    ('Трећа књига Мојсијева', 'Левитска'),
    ('Четврта књига Мојсијева', 'Бројеви'),
    ('Пета књига Мојсијева', 'Понављање'),
    ('Постањ', 'Постање'),
    ('Излаз', 'Излазак'),
    # Historical books
    ('Исуса Навина', 'Навин'),
    ('судијама', 'Судије'),
    ('Прва.*царевима', '1. Царевима'),
    ('Друга.*царевима', '2. Царевима'),
    ('царевима', 'Царевима'),
    # Prophets
    ('Исаиј', 'Исаија'),
    ('Јеремиј', 'Јеремија'),
    ('Језекиљ', 'Језекиљ'),
    ('Данил', 'Данило'),
    ('Софониј', 'Софонија'),
    ('Јоил', 'Јоил'),
    ('Јон', 'Јона'),
    ('Захариј', 'Захарија'),
    ('Малахиј', 'Малахија'),
    # Wisdom / other
    ('Књига о Јову', 'Јов'),
    ('Јов', 'Јов'),
    ('Приче', 'Приче'),
    ('Премудрост', 'Премудрост'),
    ('Сирахов', 'Сирах'),
    ('Варух', 'Варух'),
    ('Плач', 'Плач'),
]

import re as _re

def _enrich_sr_reference(reading: dict):
    """Add short book name to Serbian reading reference for readability."""
    ref = reading.get('reference')
    title = reading.get('title', '')
    if not ref or not title:
        return
    # Skip if reference already contains Cyrillic (already has book name)
    if _re.search(r'[А-Яа-яЂђЉљЊњЋћЏџ]', ref):
        return
    for pattern, short in SR_SHORT_BOOK:
        if _re.search(pattern, title):
            reading['reference'] = f'{short} {ref}'
            return


# ---------------------------------------------------------------------------
# Moveable feast names — injected algorithmically by pascha distance
# ---------------------------------------------------------------------------

MOVEABLE_FEASTS = {
    # pdist: {locale: (name, importance, type)}
    -70: {
        'sr': ("Недеља митара и фарисеја", "bold", "feast"),
        'ru': ("Неделя о мытаре и фарисее", "bold", "feast"),
        'en': ("Sunday of the Publican and the Pharisee", "bold", "feast"),
    },
    -63: {
        'sr': ("Недеља блудног сина", "bold", "feast"),
        'ru': ("Неделя о блудном сыне", "bold", "feast"),
        'en': ("Sunday of the Prodigal Son", "bold", "feast"),
    },
    -56: {
        'sr': ("Месопусна недеља – Страшни суд", "bold", "feast"),
        'ru': ("Неделя о Страшном Суде (мясопустная)", "bold", "feast"),
        'en': ("Meatfare Sunday — Sunday of the Last Judgment", "bold", "feast"),
    },
    -49: {
        'sr': ("Сиропусна недеља – Прости", "bold", "feast"),
        'ru': ("Прощёное воскресенье (сыропустная неделя)", "bold", "feast"),
        'en': ("Cheesefare Sunday — Forgiveness Sunday", "bold", "feast"),
    },
    -48: {
        'sr': ("Чисти понедељак – почетак Великог поста", "bold", "feast"),
        'ru': ("Чистый понедельник — начало Великого поста", "bold", "feast"),
        'en': ("Clean Monday — Beginning of Great Lent", "bold", "feast"),
    },
    -8: {
        'sr': ("Лазарева субота", "bold", "feast"),
        'ru': ("Воскрешение праведного Лазаря (Лазарева суббота)", "bold", "feast"),
        'en': ("Lazarus Saturday", "bold", "feast"),
    },
    -7: {
        'sr': ("Улазак Господа Исуса Христа у Јерусалим – Цвети", "great", "feast"),
        'ru': ("Вход Господень в Иерусалим (Вербное воскресенье)", "great", "feast"),
        'en': ("Entry of the Lord into Jerusalem — Palm Sunday", "great", "feast"),
    },
    -6: {
        'sr': ("Велики понедељак", "bold", "feast"),
        'ru': ("Великий понедельник", "bold", "feast"),
        'en': ("Great Monday", "bold", "feast"),
    },
    -5: {
        'sr': ("Велики уторак", "bold", "feast"),
        'ru': ("Великий вторник", "bold", "feast"),
        'en': ("Great Tuesday", "bold", "feast"),
    },
    -4: {
        'sr': ("Велика среда", "bold", "feast"),
        'ru': ("Великая среда", "bold", "feast"),
        'en': ("Great Wednesday", "bold", "feast"),
    },
    -3: {
        'sr': ("Велики четвртак", "bold", "feast"),
        'ru': ("Великий четверг", "bold", "feast"),
        'en': ("Great Thursday", "bold", "feast"),
    },
    -2: {
        'sr': ("Велики петак", "bold", "feast"),
        'ru': ("Великая пятница", "bold", "feast"),
        'en': ("Great Friday", "bold", "feast"),
    },
    -1: {
        'sr': ("Велика субота", "bold", "feast"),
        'ru': ("Великая суббота", "bold", "feast"),
        'en': ("Great Saturday", "bold", "feast"),
    },
    0: {
        'sr': ("Васкрсење Христово – Васкрс", "great", "feast"),
        'ru': ("Светлое Христово Воскресение — Пасха", "great", "feast"),
        'en': ("The Resurrection of Our Lord Jesus Christ — Pascha", "great", "feast"),
    },
    1: {
        'sr': ("Васкрсни понедељак", "bold", "feast"),
        'ru': ("Светлый понедельник", "bold", "feast"),
        'en': ("Bright Monday", "bold", "feast"),
    },
    2: {
        'sr': ("Васкрсни уторак", "bold", "feast"),
        'ru': ("Светлый вторник", "bold", "feast"),
        'en': ("Bright Tuesday", "bold", "feast"),
    },
    3: {
        'sr': ("Васкрсна среда", "bold", "feast"),
        'ru': ("Светлая среда", "bold", "feast"),
        'en': ("Bright Wednesday", "bold", "feast"),
    },
    4: {
        'sr': ("Васкрсни четвртак", "bold", "feast"),
        'ru': ("Светлый четверг", "bold", "feast"),
        'en': ("Bright Thursday", "bold", "feast"),
    },
    5: {
        'sr': ("Васкрсни петак", "bold", "feast"),
        'ru': ("Светлая пятница", "bold", "feast"),
        'en': ("Bright Friday", "bold", "feast"),
    },
    6: {
        'sr': ("Васкрсна субота", "bold", "feast"),
        'ru': ("Светлая суббота", "bold", "feast"),
        'en': ("Bright Saturday", "bold", "feast"),
    },
    7: {
        'sr': ("Томина недеља", "bold", "feast"),
        'ru': ("Антипасха (Фомина неделя)", "bold", "feast"),
        'en': ("Thomas Sunday (Antipascha)", "bold", "feast"),
    },
    14: {
        'sr': ("Недеља мироносица", "bold", "feast"),
        'ru': ("Неделя святых жен-мироносиц", "bold", "feast"),
        'en': ("Sunday of the Myrrh-Bearing Women", "bold", "feast"),
    },
    24: {
        'sr': ("Преполовљење Педесетнице", "bold", "feast"),
        'ru': ("Преполовение Пятидесятницы", "bold", "feast"),
        'en': ("Mid-Pentecost", "bold", "feast"),
    },
    39: {
        'sr': ("Вазнесење Господње – Спасовдан", "great", "feast"),
        'ru': ("Вознесение Господне", "great", "feast"),
        'en': ("The Ascension of Our Lord Jesus Christ", "great", "feast"),
    },
    49: {
        'sr': ("Силазак Светог Духа на Апостоле – Педесетница – Тројице", "great", "feast"),
        'ru': ("День Святой Троицы — Пятидесятница", "great", "feast"),
        'en': ("Pentecost — The Descent of the Holy Spirit", "great", "feast"),
    },
    50: {
        'sr': ("Духовски понедељак", "bold", "feast"),
        'ru': ("День Святого Духа", "bold", "feast"),
        'en': ("Monday of the Holy Spirit", "bold", "feast"),
    },
    56: {
        'sr': ("Недеља свих светих", "bold", "feast"),
        'ru': ("Неделя всех святых", "bold", "feast"),
        'en': ("Sunday of All Saints", "bold", "feast"),
    },
}

# Pascha distances that are moveable feasts — used to strip them from scraped saints
MOVEABLE_PDISTS = set(MOVEABLE_FEASTS.keys())

# 2026 Pascha date (the year saints were scraped for)
_PASCHA_2026 = date(2026, 4, 12)


def _is_pure_moveable_entry(name: str) -> bool:
    """Check if a saint entry is PURELY a moveable feast (not a fixed saint with a label appended)."""
    # Pure moveable feast entries — these are replaced by algorithmic injection
    pure_patterns = [
        # Serbian
        r'^В\s*а\s*с\s*к\s*р\s*с', r'^Васкрс', r'^Васкрсн', r'^Васкрсна',
        r'^Улазак Господа', r'^Цвети$',
        r'^(Литургија\s+)?Велик[иа]\s+(понедељак|уторак|среда|четвртак|петак|субота)',
        r'^Лазарева субота', r'^Силазак Светог Духа', r'^Педесетница',
        r'^Вазнесење Господње', r'^Спасовдан',
        r'^Духовски понедељак', r'^Недеља свих светих',
        r'^Недеља митара', r'^Недеља блудног', r'^Месопусна',
        r'^Сиропусна', r'^Чисти понедељак',
        r'^Томина недеља', r'^Недеља мироносица', r'^Преполовљење',
        r'^Источни петак',
        # Russian
        r'^Светлое Христово', r'^Светлый', r'^Светлая',
        r'^Вход Господень', r'^Великий (понедельник|вторник|четверг)',
        r'^Великая (среда|пятница|суббота)',
        r'^Воскрешение прав\. Лазаря', r'^День Святой Троицы', r'^Пятидесятница',
        r'^Вознесение Господне', r'^Антипасха', r'^День Святого Духа',
        r'^Неделя всех святых', r'^Неделя о мытаре', r'^Неделя о блудном',
        r'^Неделя о Страшном', r'^Прощёное', r'^Чистый понедельник',
        r'^Неделя святых жен-мироносиц', r'^Преполовение',
        # English
        r'^The Resurrection of Our Lord', r'^Pascha', r'^Bright (Mon|Tues|Wednes|Thurs|Fri|Satur)day',
        r'^Entry of the Lord.*Palm Sunday', r'^Great (Mon|Tues|Wednes|Thurs|Fri|Satur)day',
        r'^Lazarus Saturday', r'^Pentecost', r'^The Ascension',
        r'^Thomas Sunday', r'^Sunday of the Myrrh', r'^Mid-Pentecost',
        r'^Monday of the Holy Spirit', r'^Sunday of All Saints',
        r'^Meatfare Sunday', r'^Cheesefare Sunday', r'^Forgiveness Sunday',
        r'^Sunday of the Publican', r'^Sunday of the Prodigal',
        r'^Clean Monday',
    ]
    for pat in pure_patterns:
        if _re.search(pat, name):
            return True
    return False


def _clean_moveable_label(name: str) -> str:
    """Remove moveable feast labels appended to fixed saint names."""
    # "Свети X – Лазарева субота" → "Свети X"
    # "Покајни канон Свети X" → "Свети X" (Lenten prefix)
    name = _re.sub(r'\s*–\s*(Лазарева субота|Цвети|Спасовдан)$', '', name)
    name = _re.sub(r'^Литургија\s+', '', name)
    name = _re.sub(r'^Покајни канон\s+', '', name)
    return name.strip()


# Fixed great feasts by Julian month-day (Gregorian = Julian + 13 for 1900-2099)
# These are always present regardless of moveable feast collisions.
FIXED_GREAT_FEASTS = {
    # Julian date: {locale: (name, type, isSlava)}
    '09-08': {  # Greg 09-21: Nativity of Theotokos
        'sr': ("Рођење Пресвете Богородице – Мала Госпојина", "feast", True),
        'ru': ("Рождество Пресвятой Богородицы", "feast", False),
        'en': ("The Nativity of Our Most Holy Lady the Theotokos", "feast", False),
    },
    '09-14': {  # Greg 09-27: Elevation of Cross
        'sr': ("Воздвижење часног Крста – Крстовдан", "feast", True),
        'ru': ("Воздвижение Честного Креста Господня", "feast", False),
        'en': ("The Universal Elevation of the Precious and Life-Giving Cross", "feast", False),
    },
    '11-21': {  # Greg 12-04: Entry/Presentation of Theotokos
        'sr': ("Ваведење Пресвете Богородице", "feast", True),
        'ru': ("Введение во храм Пресвятой Богородицы", "feast", False),
        'en': ("The Entry of the Most Holy Theotokos into the Temple", "feast", False),
    },
    '12-25': {  # Greg 01-07: Nativity of Christ
        'sr': ("Рождество Христово – Божић", "feast", True),
        'ru': ("Рождество Христово", "feast", False),
        'en': ("The Nativity of Our Lord Jesus Christ", "feast", False),
    },
    '01-06': {  # Greg 01-19: Theophany
        'sr': ("Богојављење", "feast", True),
        'ru': ("Святое Богоявление — Крещение Господне", "feast", False),
        'en': ("The Baptism of Our Lord Jesus Christ — Theophany", "feast", False),
    },
    '02-02': {  # Greg 02-15: Meeting of the Lord (Сретење)
        'sr': ("Сретење Господње", "feast", True),
        'ru': ("Сретение Господне", "feast", False),
        'en': ("The Meeting of Our Lord Jesus Christ in the Temple", "feast", False),
    },
    '03-25': {  # Greg 04-07: Annunciation
        'sr': ("Благовести – Благовештење Пресвете Богородице", "feast", True),
        'ru': ("Благовещение Пресвятой Богородицы", "feast", False),
        'en': ("The Annunciation of Our Most Holy Lady the Theotokos", "feast", False),
    },
    '08-06': {  # Greg 08-19: Transfiguration
        'sr': ("Преображење Господње", "feast", True),
        'ru': ("Преображение Господне", "feast", False),
        'en': ("The Transfiguration of Our Lord Jesus Christ", "feast", False),
    },
    '08-15': {  # Greg 08-28: Dormition
        'sr': ("Успеније Пресвете Богородице – Велика Госпојина", "feast", True),
        'ru': ("Успение Пресвятой Богородицы", "feast", False),
        'en': ("The Dormition of Our Most Holy Lady the Theotokos", "feast", False),
    },
}


def _get_fixed_saints(saints_data: dict, key: str) -> list:
    """Get only fixed saints from scraped data, filtering out pure moveable feast entries."""
    day_data = saints_data.get(key, {})
    saints = day_data.get("saints", [])
    result = []
    for s in saints:
        name = s.get("name", "")
        if _is_pure_moveable_entry(name):
            continue
        # Clean any moveable feast label appended to a fixed saint name
        cleaned = _clean_moveable_label(name)
        if cleaned != name:
            s = dict(s)
            s["name"] = cleaned
        result.append(s)
    return result


def _get_moveable_feast_entry(pdist: int, locale: str) -> dict:
    """Create a feast entry for a moveable feast at the given pascha distance."""
    feast = MOVEABLE_FEASTS.get(pdist)
    if not feast or locale not in feast:
        return None
    name, importance, ftype = feast[locale]
    return {
        "name": name,
        "position": 0,
        "importance": importance,
        "type": ftype,
        "displayRole": "primary",
        "isSlava": False,
        "liturgicalContext": None,
    }


def _build_feasts(saints_data: dict, key: str, pdist: int, locale: str, great_feast, julian_key: str) -> list:
    """Build the feasts list for a day: fixed great feast + moveable feast + fixed saints."""
    feasts = []

    # 1. Get fixed saints from scraped data (filtering out pure moveable feasts)
    fixed = _get_fixed_saints(saints_data, key)

    # 2. Check for algorithmic fixed great feast (always injected, never lost)
    fixed_great = FIXED_GREAT_FEASTS.get(julian_key)
    fixed_great_entry = None
    if fixed_great and locale in fixed_great:
        name, ftype, is_slava = fixed_great[locale]
        fixed_great_entry = {
            "name": name,
            "position": 0,
            "importance": "great",
            "type": ftype,
            "displayRole": "primary",
            "isSlava": is_slava,
            "liturgicalContext": None,
        }
        # Remove any scraped entry that duplicates this great feast
        fixed = [s for s in fixed if s.get("importance") != "great"]

    # 3. Inject moveable feast
    moveable = _get_moveable_feast_entry(pdist, locale)

    # 4. Assemble: fixed great feast > moveable feast > fixed saints
    if fixed_great_entry and moveable:
        # Collision: both a fixed great feast and a moveable feast
        feasts.append(fixed_great_entry)
        moveable["position"] = 1
        moveable["displayRole"] = "secondary"
        feasts.append(moveable)
    elif fixed_great_entry:
        feasts.append(fixed_great_entry)
    elif moveable:
        feasts.append(moveable)

    # Add remaining fixed saints
    for i, saint in enumerate(fixed):
        saint = dict(saint)
        saint["position"] = len(feasts) + i
        if feasts:
            saint["displayRole"] = "secondary" if len(feasts) == 1 and i == 0 else "tertiary"
        feasts.append(saint)

    return feasts


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, using empty dict", file=sys.stderr)
        return {"days": {}}
    with open(path) as f:
        return json.load(f)


def to_julian_key(greg_date: date) -> str:
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    return f"{julian.month:02d}-{julian.day:02d}"


def build_calendar(locale: str, year: int):
    """Build the final calendar JSON for a locale."""
    pasch = Paschalion(year)
    proc_dir = os.path.join(DATA_DIR, 'processed', locale)

    # Load scraped data
    saints_data = load_json(os.path.join(proc_dir, 'saints.json')).get('days', {})

    # Use the lectionary engine + scraped text for readings
    print(f"  Generating engine-based readings for {locale} {year}...", file=sys.stderr)
    engine_readings = generate_all_readings(year, locale)

    # Fall back: load raw scraped readings for days the engine has no data
    readings_data = load_json(os.path.join(proc_dir, 'readings.json')).get('days', {})

    # Russian-specific
    reflections_data = {}
    fasting_descriptions = {}
    if locale == 'ru':
        reflections_data = load_json(os.path.join(proc_dir, 'reflections.json')).get('days', {})
        fasting_descriptions = load_json(os.path.join(proc_dir, 'fasting.json')).get('days', {})

    calendar = {}
    current = date(year, 1, 1)
    end = date(year, 12, 31)

    while current <= end:
        key = current.strftime("%m-%d")
        julian_key = to_julian_key(current)

        # Pascha distance for this day
        pdist = pasch.pascha_distance(current)

        # Determine feast rank for fasting upgrade
        great_feast = pasch.is_great_feast(current)
        feast_rank = "great" if great_feast else None

        # Compute algorithmic fasting
        fasting_level = compute_fasting(current, pasch, feast_rank)
        fasting_info = get_fasting_info(fasting_level, locale)

        # Get scraped fasting description (supplements algorithmic)
        scraped_fasting = fasting_descriptions.get(key, {})

        # Build day entry
        day = {
            "gregorianDate": current.isoformat(),
            "julianDate": julian_key,
            "dayOfWeek": current.weekday(),  # 0=Mon..6=Sun
            "paschaDistance": pdist,

            # Feasts/Saints — fixed saints from scraped data + algorithmic moveable feasts
            "feasts": _build_feasts(saints_data, key, pdist, locale, great_feast, julian_key),
            "liturgicalPeriod": saints_data.get(key, {}).get("liturgicalPeriod"),
            "weekLabel": saints_data.get(key, {}).get("weekLabel"),

            # Great feast override
            "greatFeast": great_feast,

            # Fasting (algorithmic + scraped description)
            "fasting": {
                "type": fasting_level,
                "label": fasting_info["label"],
                "explanation": scraped_fasting.get("description") or fasting_info["explanation"],
                "abbrev": fasting_info["abbrev"],
                "icon": fasting_info["icon"],
            },

            # Readings: prefer engine-generated, fall back to raw scraped
            "readings": engine_readings.get(key) or readings_data.get(key, []),

            # Reflection
            "reflection": reflections_data.get(key),

            # Fasting period context
            "fastingPeriod": pasch.get_fasting_period(current),
            "isFastFreeWeek": pasch.is_fast_free_week(current),
        }

        # Add liturgical note from pravoslavie.ru
        if scraped_fasting.get("liturgicalNote"):
            day["liturgicalNote"] = scraped_fasting["liturgicalNote"]

        # Enrich Serbian references with short book names
        if locale == 'sr':
            for r in day["readings"]:
                _enrich_sr_reference(r)

        calendar[key] = day
        current += timedelta(days=1)

    return calendar


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Support command-line year range override: build_database.py [start] [end]
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) >= 2:
        year_start, year_end = int(args[0]), int(args[1])
    elif len(args) == 1:
        year_start = year_end = int(args[0])
    else:
        year_start, year_end = YEAR_START, YEAR_END

    for year in range(year_start, year_end + 1):
        for locale in ['sr', 'ru', 'en']:
            print(f"\n=== Building calendar_{locale}_{year}.json ===", file=sys.stderr)
            calendar = build_calendar(locale, year)

            output_file = os.path.join(OUTPUT_DIR, f"calendar_{locale}_{year}.json")
            with open(output_file, 'w') as f:
                json.dump({
                    "year": year,
                    "locale": locale,
                    "generatedBy": "build_database.py",
                    "days": calendar,
                }, f, ensure_ascii=False, indent=2)

            # Stats
            days_with_saints = sum(1 for d in calendar.values() if d["feasts"])
            days_with_readings = sum(1 for d in calendar.values() if d["readings"])
            days_with_reflection = sum(1 for d in calendar.values() if d.get("reflection"))
            great_feasts = sum(1 for d in calendar.values() if d["greatFeast"])

            print(f"  Days: {len(calendar)}", file=sys.stderr)
            print(f"  With saints: {days_with_saints}", file=sys.stderr)
            print(f"  With readings: {days_with_readings}", file=sys.stderr)
            print(f"  With reflection: {days_with_reflection}", file=sys.stderr)
            print(f"  Great feasts: {great_feasts}", file=sys.stderr)
            print(f"  Saved: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
