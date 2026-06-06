#!/usr/bin/env python3
"""
Generate Readings — Merges the Typikon lectionary engine output with scraped Bible text.

For a given year, uses the lectionary engine to compute which readings belong to each day,
then matches those references against the scraped Serbian and Russian Bible texts.

The matching is done by normalized chapter:verse ranges (NOT zachalo numbers, which differ
between traditions).

Usage:
    python generate_readings.py [year]
"""

import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from lectionary_engine import get_readings, gregorian_to_julian_date

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
DATA_DIR = os.path.join(BASE_DIR, 'data')
JULIAN_OFFSET = 13


# ---------------------------------------------------------------------------
# Book name mapping: engine (English) -> scraped data conventions
# ---------------------------------------------------------------------------

# Map OCA pericope book names to chapter:verse patterns in the display field
# Engine display format: "Matthew 2.1-12", "Romans 1.1-7", "Acts 1.1-8"

# Serbian book name fragments that appear in titles
SR_BOOK_MAP = {
    'Matthew': 'Матеј',
    'Mark': 'Марк',
    'Luke': 'Лук',
    'John': 'Јован',
    'Acts': 'Дела',
    'Romans': 'Римљаним',
    '1 Corinthians': 'Коринћаним',
    '2 Corinthians': 'Коринћаним',
    'Galatians': 'Галатим',
    'Ephesians': 'Ефесцим',
    'Philippians': 'Филипљаним',
    'Colossians': 'Колосјаним',
    '1 Thessalonians': 'Солуњаним',
    '2 Thessalonians': 'Солуњаним',
    '1 Timothy': 'Тимотеју',
    '2 Timothy': 'Тимотеју',
    'Titus': 'Тит',
    'Philemon': 'Филимон',
    'Hebrews': 'Јеврејим',
    'James': 'Јаков',
    '1 Peter': 'Петр',
    '2 Peter': 'Петр',
    '1 John': 'Јован',
    '2 John': 'Јован',
    '3 John': 'Јован',
    'Jude': 'Јуд',
    'Revelation': 'Откривењ',
    # OT books
    'Genesis': 'Постањ',
    'Exodus': 'Излаз',
    'Leviticus': 'Левитск',
    'Numbers': 'Број',
    'Deuteronomy': 'Понављањ',
    'Joshua': 'Навин',
    'Judges': 'Судиј',
    'Ruth': 'Рут',
    '1 Samuel': 'Самуил',
    '2 Samuel': 'Самуил',
    '1 Kings': 'Царев',
    '2 Kings': 'Царев',
    'Isaiah': 'Исаиј',
    'Jeremiah': 'Јеремиј',
    'Ezekiel': 'Језекиљ',
    'Daniel': 'Данил',
    'Hosea': 'Осиј',
    'Joel': 'Јоил',
    'Amos': 'Амос',
    'Obadiah': 'Авдиј',
    'Jonah': 'Јон',
    'Micah': 'Михеј',
    'Nahum': 'Наум',
    'Habakkuk': 'Авакум',
    'Zephaniah': 'Софониј',
    'Haggai': 'Агеј',
    'Zechariah': 'Захариј',
    'Malachi': 'Малахиј',
    'Proverbs': 'Приче',
    'Ecclesiastes': 'Проповедник',
    'Song of Solomon': 'Песма',
    'Wisdom': 'Премудрост',
    'Sirach': 'Сирахов',
    'Baruch': 'Варух',
    'Lamentations': 'Плач',
    # Composite book keys used in the readings SQL
    'Apostol': None,  # Generic epistle marker
}

# Russian book abbreviations
RU_BOOK_MAP = {
    'Matthew': 'Мф',
    'Mark': 'Мк',
    'Luke': 'Лк',
    'John': 'Ин',
    'Acts': 'Деян',
    'Romans': 'Рим',
    '1 Corinthians': '1Кор',
    '2 Corinthians': '2Кор',
    'Galatians': 'Гал',
    'Ephesians': 'Еф',
    'Philippians': 'Флп',
    'Colossians': 'Кол',
    '1 Thessalonians': '1Фес',
    '2 Thessalonians': '2Фес',
    '1 Timothy': '1Тим',
    '2 Timothy': '2Тим',
    'Titus': 'Тит',
    'Philemon': 'Флм',
    'Hebrews': 'Евр',
    'James': 'Иак',
    '1 Peter': '1Пет',
    '2 Peter': '2Пет',
    '1 John': '1Ин',
    '2 John': '2Ин',
    '3 John': '3Ин',
    'Jude': 'Иуд',
    'Revelation': 'Откр',
    'Genesis': 'Быт',
    'Exodus': 'Исх',
    'Isaiah': 'Ис',
    'Jeremiah': 'Иер',
    'Ezekiel': 'Иез',
    'Daniel': 'Дан',
    'Proverbs': 'Притч',
    'Joel': 'Иоил',
    'Jonah': 'Ион',
    'Zechariah': 'Зах',
    'Malachi': 'Мал',
    'Wisdom': 'Прем',
    'Sirach': 'Сир',
    'Apostol': None,
}

# English book names — identity map (engine already uses English names)
EN_BOOK_MAP = {
    'Matthew': 'Matthew',
    'Mark': 'Mark',
    'Luke': 'Luke',
    'John': 'John',
    'Acts': 'Acts',
    'Romans': 'Romans',
    '1 Corinthians': '1 Corinthians',
    '2 Corinthians': '2 Corinthians',
    'Galatians': 'Galatians',
    'Ephesians': 'Ephesians',
    'Philippians': 'Philippians',
    'Colossians': 'Colossians',
    '1 Thessalonians': '1 Thessalonians',
    '2 Thessalonians': '2 Thessalonians',
    '1 Timothy': '1 Timothy',
    '2 Timothy': '2 Timothy',
    'Titus': 'Titus',
    'Philemon': 'Philemon',
    'Hebrews': 'Hebrews',
    'James': 'James',
    '1 Peter': '1 Peter',
    '2 Peter': '2 Peter',
    '1 John': '1 John',
    '2 John': '2 John',
    '3 John': '3 John',
    'Jude': 'Jude',
    'Revelation': 'Revelation',
    'Genesis': 'Genesis',
    'Exodus': 'Exodus',
    'Leviticus': 'Leviticus',
    'Numbers': 'Numbers',
    'Deuteronomy': 'Deuteronomy',
    'Joshua': 'Joshua',
    'Judges': 'Judges',
    'Ruth': 'Ruth',
    '1 Samuel': '1 Samuel',
    '2 Samuel': '2 Samuel',
    '1 Kings': '1 Kings',
    '2 Kings': '2 Kings',
    'Isaiah': 'Isaiah',
    'Jeremiah': 'Jeremiah',
    'Ezekiel': 'Ezekiel',
    'Daniel': 'Daniel',
    'Hosea': 'Hosea',
    'Joel': 'Joel',
    'Amos': 'Amos',
    'Obadiah': 'Obadiah',
    'Jonah': 'Jonah',
    'Micah': 'Micah',
    'Nahum': 'Nahum',
    'Habakkuk': 'Habakkuk',
    'Zephaniah': 'Zephaniah',
    'Haggai': 'Haggai',
    'Zechariah': 'Zechariah',
    'Malachi': 'Malachi',
    'Proverbs': 'Proverbs',
    'Ecclesiastes': 'Ecclesiastes',
    'Song of Solomon': 'Song of Solomon',
    'Wisdom': 'Wisdom',
    'Sirach': 'Sirach',
    'Baruch': 'Baruch',
    'Lamentations': 'Lamentations',
    'Apostol': None,
}


# ---------------------------------------------------------------------------
# Reference normalization
# ---------------------------------------------------------------------------

def _extract_chapter_verses(display: str) -> list:
    """
    Extract normalized (chapter, verse_start, verse_end) tuples from an engine display string.

    Engine format examples:
        "Matthew 2.1-12"      -> [(2, 1, 12)]
        "Romans 1.1-7,13-17"  -> [(1, 1, 7), (1, 13, 17)]
        "Luke 1.39-49,56"     -> [(1, 39, 49), (1, 56, 56)]
        "Matthew 4.25-5.13"   -> [(4, 25, 99), (5, 1, 13)]  (cross-chapter)
        "Acts 1.1-8"          -> [(1, 1, 8)]
    """
    # Strip book name - find the first digit after space
    m = re.search(r'[\d]', display)
    if not m:
        return []
    ref_part = display[m.start():]
    return _parse_ref_segments(ref_part, '.')


def _parse_ref_segments(ref: str, chap_sep: str) -> list:
    """Parse chapter:verse segments from a reference string.

    chap_sep is '.' for engine format, ',' or ':' for scraped formats.
    """
    segments = []

    # Handle semicolon-separated sections (different chapters)
    sections = re.split(r'\s*;\s*', ref)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Try to find chapter.verse pattern
        # Handle formats like: "2.1-12", "4.25-5.13", "1.39-49,56"
        # Also handle: "2,1-12", "1:39-49"

        # Normalize separator
        norm = section

        # Split on the chapter separator (first occurrence)
        if chap_sep == '.':
            parts = norm.split('.', 1)
        elif chap_sep == ',':
            parts = norm.split(',', 1)
        elif chap_sep == ':':
            parts = norm.split(':', 1)
        else:
            parts = [norm]

        if len(parts) == 1:
            # Just a chapter number or something we can't parse
            try:
                ch = int(parts[0].strip())
                segments.append((ch, 1, 999))
            except ValueError:
                pass
            continue

        try:
            chapter = int(parts[0].strip())
        except ValueError:
            continue

        verse_part = parts[1].strip()

        # Parse verse ranges: "1-12", "39-49,56", "25-5.13"
        # Check for cross-chapter range (e.g., "25-5.13" or "25-5,13")
        cross_match = re.match(r'(\d+)\s*[-–]\s*(\d+)[.,:](\d+)', verse_part)
        if cross_match:
            v_start = int(cross_match.group(1))
            ch2 = int(cross_match.group(2))
            v_end = int(cross_match.group(3))
            segments.append((chapter, v_start, 999))
            segments.append((ch2, 1, v_end))
            # Handle any remaining comma-separated parts
            remaining = verse_part[cross_match.end():]
            if remaining.startswith(','):
                for extra in remaining[1:].split(','):
                    extra = extra.strip()
                    if not extra:
                        continue
                    r = re.match(r'(\d+)\s*[-–]\s*(\d+)', extra)
                    if r:
                        segments.append((ch2, int(r.group(1)), int(r.group(2))))
                    else:
                        try:
                            v = int(extra)
                            segments.append((ch2, v, v))
                        except ValueError:
                            pass
            continue

        # Simple verse ranges within one chapter: "1-12" or "39-49,56"
        comma_parts = verse_part.split(',')
        for cp in comma_parts:
            cp = cp.strip()
            if not cp:
                continue
            r = re.match(r'(\d+)\s*[-–]\s*(\d+)', cp)
            if r:
                segments.append((chapter, int(r.group(1)), int(r.group(2))))
            else:
                try:
                    v = int(cp)
                    segments.append((chapter, v, v))
                except ValueError:
                    pass

    return segments


def _extract_scraped_ref_sr(title: str, reference: str) -> list:
    """Extract chapter:verse segments from Serbian scraped data."""
    # The reference field is like "1,20-21; 2,1-9" or "2,1-12"
    if not reference:
        # Try to extract from title: "зачало 5 (2,1-20)"
        m = re.search(r'\(([^)]+)\)', title)
        if m:
            reference = m.group(1)
        else:
            return []

    # Clean: remove book name prefix if present
    # e.g., "Јеврејима 10,35-39; 11,1-7" -> "10,35-39; 11,1-7"
    # Check if the reference starts with a Cyrillic word
    ref_clean = re.sub(r'^[А-Яа-яЂђЉљЊњЋћЏџ\s]+(?=\d)', '', reference).strip()
    if not ref_clean:
        ref_clean = reference

    return _parse_ref_segments(ref_clean, ',')


def _extract_scraped_ref_ru(title: str, reference: str = None) -> list:
    """Extract chapter:verse segments from Russian scraped data."""
    # Russian titles are like "Мк.10:17–27" or "Евр.10:35-11:7"
    # Reference field might be the same as title
    text = reference or title
    if not text:
        return []

    # Remove book abbreviation: "Мк.10:17–27" -> "10:17–27"
    m = re.search(r'(\d)', text)
    if not m:
        return []
    ref_part = text[m.start():]

    return _parse_ref_segments(ref_part, ':')


def _extract_scraped_ref_en(title: str, reference: str = None) -> list:
    """Extract chapter:verse segments from English scraped data.

    English scraped titles use ':' as chapter separator, e.g. "Hebrews 10:35-11:7".
    """
    text = reference or title
    if not text:
        return []

    # Remove book name: find the first digit
    m = re.search(r'(\d)', text)
    if not m:
        return []
    ref_part = text[m.start():]

    return _parse_ref_segments(ref_part, ':')


def _segments_overlap(segs_a: list, segs_b: list) -> bool:
    """Check if two sets of (chapter, verse_start, verse_end) segments overlap significantly."""
    if not segs_a or not segs_b:
        return False

    for (ch_a, vs_a, ve_a) in segs_a:
        for (ch_b, vs_b, ve_b) in segs_b:
            if ch_a == ch_b:
                # Check verse overlap
                if vs_a <= ve_b and vs_b <= ve_a:
                    return True
    return False


def _book_matches_sr(engine_book: str, scraped_title: str) -> bool:
    """Check if engine book name matches the Serbian scraped title."""
    if not engine_book or engine_book == 'Apostol':
        # Apostol is a generic marker - match any epistle
        # Check if NOT a gospel
        for gospel_word in ['Матеј', 'Марк', 'Лук', 'Јован']:
            if 'Јеванђеље' in scraped_title and gospel_word in scraped_title:
                return False
        # Also not a prophet/OT book
        for ot_word in ['пророк', 'Книга', 'Постањ', 'Излаз', 'Приче', 'Премудрост']:
            if ot_word in scraped_title:
                return False
        return True

    sr_frag = SR_BOOK_MAP.get(engine_book)
    if sr_frag and sr_frag in scraped_title:
        return True

    return False


def _book_matches_ru(engine_book: str, scraped_title: str) -> bool:
    """Check if engine book name matches the Russian scraped title."""
    if not engine_book or engine_book == 'Apostol':
        # Match any epistle (not gospel, not OT)
        for gospel_abbr in ['Мф', 'Мк', 'Лк', 'Ин']:
            if scraped_title.startswith(gospel_abbr + '.') or scraped_title.startswith(gospel_abbr + ' '):
                return False
        return True

    ru_abbr = RU_BOOK_MAP.get(engine_book)
    if ru_abbr and (scraped_title.startswith(ru_abbr + '.') or scraped_title.startswith(ru_abbr + ' ') or
                     scraped_title.startswith(ru_abbr + ':')):
        return True

    return False


def _book_matches_en(engine_book: str, scraped_title: str) -> bool:
    """Check if engine book name matches the English scraped title."""
    if not engine_book or engine_book == 'Apostol':
        # Match any epistle (not gospel, not OT)
        for gospel_name in ['Matthew', 'Mark', 'Luke', 'John']:
            if scraped_title.startswith(gospel_name + ' '):
                return False
        return True

    en_name = EN_BOOK_MAP.get(engine_book)
    if en_name and scraped_title.startswith(en_name + ' '):
        return True

    return False


# ---------------------------------------------------------------------------
# Data loading — global index of scraped readings by normalized reference
# ---------------------------------------------------------------------------

# Serbian service-section headers occasionally bleed onto the end of a reading's
# text when the scraper fails to split the page on them — either as a bare label
# ("…рече.Литургија", "…ћути.Јутрења") or with the "На " prefix ("…земљи.На
# вечерњи"). Strip any such trailing header. The word list is explicit so we never
# truncate legitimate scripture text.
_SR_SERVICE_WORDS = (
    'вечерњи', 'вечерња', 'вечерње', 'вечерњу',
    'јутрења', 'јутрењу', 'јутрење',
    'литургија', 'литургији', 'литургије', 'литургију',
    'часови', 'часова', 'часовима',
    'повечерје', 'повечерју', 'повечерја',
)
_SR_SERVICE_TAIL_RE = re.compile(
    r'\s*(?:На\s+)?(?:' + '|'.join(_SR_SERVICE_WORDS) + r')\s*$',
    re.IGNORECASE,
)

# A Serbian reading is only identifiable if it carries a chapter:verse reference
# or a structural title (book name / зачало). Entries with neither are scraper
# artifacts — orphaned verse fragments that were split onto their own <b> tag.
_SR_STRUCT_TITLE_RE = re.compile(
    r'зачало|Јеванђеље|Посланиц|Псал[ам]|књига|Књига|пророка|Пророка|Дела\s'
    r'|Премудрост|Сирахов|Апостол|Мојсијев|Приче|Соломонов|Прокимен'
    r'|Изласка|Постањ|Бројева|Поновљених'
)


def _strip_service_tail(text: str) -> str:
    """Remove a trailing service-section header that bled into the reading text."""
    if not text:
        return text
    return _SR_SERVICE_TAIL_RE.sub('', text).strip()


def _is_orphan_fragment(reading: dict) -> bool:
    """True for a Serbian reading that is a scraper artifact, not a real reading.

    Such entries have no reference and no structural (book/зачало) title. The
    scraper sometimes split a single Gospel reading (e.g. John 14) into one entry
    per verse, putting the verse text in the title. Drop an orphan when it has no
    text, or when its "title" is a verse sentence rather than a short service
    label — legitimate short labels like the Lenten canticle odes ("Песма прва" …
    ≤ 13 chars) are kept, while verse fragments (> 16 chars, up to whole prayers)
    are dropped.
    """
    if reading.get('reference'):
        return False
    title = (reading.get('title') or '').strip()
    if _SR_STRUCT_TITLE_RE.search(title):
        return False
    if not (reading.get('text') or '').strip():
        return True
    return len(title) > 16


# ---------------------------------------------------------------------------
# Serbian Bible fallback — fill text for readings the day-scrape missed
# ---------------------------------------------------------------------------

# Engine book name -> knjiga number in the scraped Serbian Bible (bible.json).
ENGINE_TO_KNJIGA = {
    'Genesis': 1, 'Exodus': 2, 'Leviticus': 3, 'Numbers': 4, 'Deuteronomy': 5,
    'Joshua': 6, 'Judges': 7, 'Ruth': 8, '1 Samuel': 9, '2 Samuel': 10,
    '1 Kings': 11, '2 Kings': 12, '1 Chronicles': 13, '2 Chronicles': 14,
    'Ezra': 15, 'Nehemiah': 16, 'Esther': 17, 'Job': 18, 'Psalms': 19,
    'Proverbs': 20, 'Ecclesiastes': 21, 'Song of Songs': 22, 'Isaiah': 23,
    'Jeremiah': 24, 'Lamentations': 25, 'Ezekiel': 26, 'Daniel': 27, 'Hosea': 28,
    'Joel': 29, 'Amos': 30, 'Obadiah': 31, 'Jonah': 32, 'Micah': 33, 'Nahum': 34,
    'Habakkuk': 35, 'Zephaniah': 36, 'Haggai': 37, 'Zechariah': 38, 'Malachi': 39,
    'Matthew': 40, 'Mark': 41, 'Luke': 42, 'John': 43, 'Acts': 44, 'Romans': 45,
    '1 Corinthians': 46, '2 Corinthians': 47, 'Galatians': 48, 'Ephesians': 49,
    'Philippians': 50, 'Colossians': 51, '1 Thessalonians': 52,
    '2 Thessalonians': 53, '1 Timothy': 54, '2 Timothy': 55, 'Titus': 56,
    'Philemon': 57, 'Hebrews': 58, 'James': 59, '1 Peter': 60, '2 Peter': 61,
    '1 John': 62, '2 John': 63, '3 John': 64, 'Jude': 65, 'Revelation': 66,
}

# Serbian citation name for the reading 'reference' field (matches the style of
# the existing scraped references, e.g. "Римљанима 1,1-7", "1. Тимотеју 6,11-16").
SR_REF_NAME = {
    'Genesis': 'Постање', 'Exodus': 'Излазак', 'Leviticus': 'Левитска',
    'Numbers': 'Бројеви', 'Deuteronomy': 'Поновљени закони', 'Joshua': 'Исус Навин',
    'Judges': 'Судије', 'Ruth': 'Рута', '1 Samuel': '1. Самуилова',
    '2 Samuel': '2. Самуилова', '1 Kings': '1. о царевима', '2 Kings': '2. о царевима',
    'Job': 'Јов', 'Psalms': 'Псалам', 'Proverbs': 'Приче', 'Ecclesiastes': 'Проповедник',
    'Isaiah': 'Исаија', 'Jeremiah': 'Јеремија', 'Lamentations': 'Плач Јеремијин',
    'Ezekiel': 'Језекиљ', 'Daniel': 'Данило', 'Hosea': 'Осија', 'Joel': 'Јоил',
    'Amos': 'Амос', 'Obadiah': 'Авдије', 'Jonah': 'Јона', 'Micah': 'Михеј',
    'Nahum': 'Наум', 'Habakkuk': 'Авакум', 'Zephaniah': 'Софонија', 'Haggai': 'Агеј',
    'Zechariah': 'Захарија', 'Malachi': 'Малахија',
    'Matthew': 'Матеј', 'Mark': 'Марко', 'Luke': 'Лука', 'John': 'Јован',
    'Acts': 'Дела', 'Romans': 'Римљанима', '1 Corinthians': '1. Коринћанима',
    '2 Corinthians': '2. Коринћанима', 'Galatians': 'Галатима', 'Ephesians': 'Ефесцима',
    'Philippians': 'Филипљанима', 'Colossians': 'Колошанима',
    '1 Thessalonians': '1. Солуњанима', '2 Thessalonians': '2. Солуњанима',
    '1 Timothy': '1. Тимотеју', '2 Timothy': '2. Тимотеју', 'Titus': 'Титу',
    'Philemon': 'Филимону', 'Hebrews': 'Јеврејима', 'James': 'Јакова',
    '1 Peter': '1. Петрова', '2 Peter': '2. Петрова', '1 John': '1. Јованова',
    '2 John': '2. Јованова', '3 John': '3. Јованова', 'Jude': 'Јуде',
    'Revelation': 'Откривење',
}

_SR_BIBLE = None


def _load_sr_bible() -> dict:
    """Load the scraped Serbian Bible (books keyed by knjiga number)."""
    global _SR_BIBLE
    if _SR_BIBLE is None:
        path = os.path.join(DATA_DIR, 'processed', 'sr', 'bible.json')
        if os.path.exists(path):
            with open(path) as f:
                _SR_BIBLE = json.load(f).get('books', {})
            print(f"  [sr] Loaded Serbian Bible: {len(_SR_BIBLE)} books", file=sys.stderr)
        else:
            _SR_BIBLE = {}
    return _SR_BIBLE


def _sr_bible_fill(eng: dict) -> dict:
    """Build a Serbian reading from the scraped Bible for an engine reading that
    matched no scraped day-text. Returns a reading entry (with text) or None.
    """
    bible = _load_sr_bible()
    if not bible:
        return None
    display = eng.get('display') or eng.get('sdisplay') or ''
    bm = re.match(r'((?:[1-3]\s)?[A-Za-z ]+?)\s+\d', display)
    if not bm:
        return None
    book = bm.group(1).strip()
    knjiga = ENGINE_TO_KNJIGA.get(book)
    book_data = bible.get(str(knjiga)) if knjiga else None
    if not book_data:
        return None  # deuterocanon (e.g. Wisdom) or unmapped — leave to day-scrape
    chapters = book_data['chapters']

    # Parse the reference *after* the book name — _extract_chapter_verses would
    # mistake the "1" in e.g. "1 Corinthians" for the chapter.
    ref_part = display[bm.end() - 1:].strip()
    segments = _parse_ref_segments(ref_part, '.')
    if not segments:
        return None
    parts = []
    for ch, vstart, vend in segments:
        chap = chapters.get(str(ch))
        if not chap:
            continue
        last = max(int(v) for v in chap)
        for v in range(vstart, min(vend, last) + 1):
            t = chap.get(str(v))
            if t:
                parts.append(f"{v}. {t}")
    if not parts:
        return None

    ref_sr = ref_part.replace('.', ',')
    short = SR_REF_NAME.get(book, book)
    if 40 <= knjiga <= 43:
        rtype = 'gospel'
    elif 1 <= knjiga <= 39:
        rtype = 'ot'
    else:
        rtype = 'apostol'
    return {
        'title': f"{book_data['title']} ({ref_sr})",
        'type': rtype,
        'text': ' '.join(parts),
        'reference': f"{short} {ref_sr}",
    }


# English Bible fallback — fill readings the OCA (NKJV) day-scrape doesn't provide
# (festal Vespers prophecies, Hours, post-Pentecost weekday epistles). OT text is
# Brenton's Septuagint, NT is the KJV (see scripts/english/build_bible.py).
_EN_OT_BOOKS = frozenset({
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges',
    'Ruth', '1 Samuel', '2 Samuel', '1 Kings', '2 Kings', '1 Chronicles',
    '2 Chronicles', 'Ezra', 'Nehemiah', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes',
    'Song of Songs', 'Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel',
    'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk',
    'Zephaniah', 'Haggai', 'Zechariah', 'Malachi', 'Wisdom of Solomon', 'Sirach',
    'Baruch', 'Tobit', 'Judith',
})

_EN_BIBLE = None


def _load_en_bible() -> dict:
    global _EN_BIBLE
    if _EN_BIBLE is None:
        path = os.path.join(DATA_DIR, 'processed', 'en', 'bible.json')
        if os.path.exists(path):
            with open(path) as f:
                _EN_BIBLE = json.load(f).get('books', {})
            print(f"  [en] Loaded English Bible: {len(_EN_BIBLE)} books", file=sys.stderr)
        else:
            _EN_BIBLE = {}
    return _EN_BIBLE


def _en_bible_text(book: str, ref_part: str, sep: str) -> str:
    """Assemble public-domain (KJV/Brenton) text for a book + reference part
    (e.g. book='Romans', ref_part='1:1-7, 13-17', sep=':'). Returns text or None.
    """
    bible = _load_en_bible()
    chapters = bible.get(book) or bible.get(book + 's')  # tolerate scrape typo ("Colossian")
    if not chapters:
        return None
    segments = _parse_ref_segments(ref_part, sep)
    if not segments and len(chapters) == 1:
        # Single-chapter book referenced by verses only (e.g. "Jude 1-10").
        only_ch = next(iter(chapters))
        segments = _parse_ref_segments(f"{only_ch}{sep}{ref_part}", sep)
    if not segments:
        return None
    parts = []
    for ch, vstart, vend in segments:
        chap = chapters.get(str(ch))
        if not chap:
            continue
        last = max(int(v) for v in chap)
        for v in range(vstart, min(vend, last) + 1):
            t = chap.get(str(v))
            if t:
                parts.append(f"{v} {t}")  # OCA style: "13 For I speak…"
    return ' '.join(parts) if parts else None


def _en_parse_ref(ref: str, sep: str):
    """Split an English reference into (book, ref_part), normalizing LXX names
    and the "Jeremiah (Baruch …)" parenthetical. Returns (None, None) on failure.
    """
    ref = re.sub(r'\d\[(\d)\]\s*Kings', r'\1 Kings', ref or '')  # 3[1] Kings -> 1 Kings
    pm = re.search(r'\(([^)]+)\)', ref)
    if pm and re.match(r'[A-Z][A-Za-z]+\s+\d', pm.group(1).strip()):
        ref = pm.group(1).strip()
    bm = re.match(r'((?:[1-3]\s)?[A-Za-z][A-Za-z ]*?)\s+(\d.*)$', ref.strip())
    if not bm:
        return None, None
    return bm.group(1).strip(), bm.group(2).strip()


def _en_reading_type(book: str) -> str:
    if book in _EN_OT_BOOKS:
        return 'ot'
    if book in ('Matthew', 'Mark', 'Luke', 'John'):
        return 'gospel'
    return 'apostol'


def _en_bible_fill(eng: dict) -> dict:
    """Build an English reading from the KJV/Brenton index for an engine reading
    that matched no scraped day-text. Returns a reading entry or None.
    """
    if not _load_en_bible():
        return None
    display = eng.get('display') or eng.get('sdisplay') or ''
    book, ref_part = _en_parse_ref(display, '.')
    if not book:
        return None
    text = _en_bible_text(book, ref_part, '.')
    if not text:
        return None
    ref = book + ' ' + ref_part.replace('.', ':')
    return {'title': ref, 'type': _en_reading_type(book), 'text': text, 'reference': ref}


def _add_title_text(title_index: dict, entry: dict):
    """Index a scraped entry by its exact title, keeping the longest text seen."""
    title = (entry.get('title') or '').strip()
    text = (entry.get('text') or '').strip()
    if not title or not text:
        return
    existing = title_index.get(title)
    if existing is None or len(text) > len((existing.get('text') or '')):
        title_index[title] = entry


def _normalize_ref_key(segments: list) -> str:
    """Create a hashable key from parsed segments for index lookup."""
    if not segments:
        return ''
    # Use the first segment's chapter and verse_start as primary key
    parts = []
    for ch, vs, ve in sorted(segments):
        parts.append(f"{ch}:{vs}-{ve}")
    return '|'.join(parts)


def _build_scraped_index(locale: str) -> tuple:
    """
    Build a global index of all scraped readings keyed by normalized chapter:verse reference.

    Returns (text_index, julian_readings, title_index):
        text_index: dict mapping (book_key, ref_key) -> scraped entry (with text)
        julian_readings: dict mapping "MM-DD" (Julian) -> list of scraped entries
        title_index: dict mapping exact reading title -> scraped entry (with text)
    """
    proc_dir = os.path.join(DATA_DIR, 'processed', locale)
    title_index = {}

    if locale == 'en':
        # English: index scraped readings from holytrinityorthodox.com
        readings_path = os.path.join(proc_dir, 'readings.json')
        if not os.path.exists(readings_path):
            print(f"  [{locale}] No scraped readings data found", file=sys.stderr)
            return {}, {}, title_index

        with open(readings_path) as f:
            rdata = json.load(f)

        text_index = {}
        for day_key, entries in rdata.get('days', {}).items():
            for entry in entries:
                if not entry.get('text'):
                    continue
                _index_scraped_entry(text_index, entry, locale)
                _add_title_text(title_index, entry)

        print(f"  [{locale}] Indexed {len(text_index)} scraped readings with text", file=sys.stderr)
        return text_index, {}, title_index

    if locale == 'sr':
        path = os.path.join(proc_dir, 'lectionary_merged.json')
    else:
        path = os.path.join(proc_dir, 'lectionary_complete.json')

    if not os.path.exists(path):
        print(f"  WARNING: {path} not found", file=sys.stderr)
        return {}, {}, title_index

    with open(path) as f:
        data = json.load(f)

    text_index = {}  # (book_fragment, ref_key) -> scraped entry

    # Index all byPaschaDistance entries
    for pdist_key, entries in data.get('byPaschaDistance', {}).items():
        for entry in entries:
            if not entry.get('text'):
                continue
            _index_scraped_entry(text_index, entry, locale)
            _add_title_text(title_index, entry)


    # Index all byJulianDate entries
    for julian_key, entries in data.get('byJulianDate', {}).items():
        for entry in entries:
            if not entry.get('text'):
                continue
            _index_scraped_entry(text_index, entry, locale)
            _add_title_text(title_index, entry)

    # Also index the readings.json which has different reference formats
    readings_path = os.path.join(proc_dir, 'readings.json')
    if os.path.exists(readings_path):
        with open(readings_path) as f:
            rdata = json.load(f)
        for day_key, entries in rdata.get('days', {}).items():
            for entry in entries:
                if not entry.get('text'):
                    continue
                _index_scraped_entry(text_index, entry, locale)
                _add_title_text(title_index, entry)

    julian_readings = data.get('byJulianDate', {})

    print(f"  [{locale}] Indexed {len(text_index)} scraped readings with text", file=sys.stderr)
    return text_index, julian_readings, title_index


def _index_scraped_entry(index: dict, entry: dict, locale: str):
    """Add a scraped entry to the text index."""
    title = entry.get('title', '')
    reference = entry.get('reference', '')

    if locale == 'sr':
        segments = _extract_scraped_ref_sr(title, reference)
        book_key = _sr_book_key(title)
    elif locale == 'ru':
        segments = _extract_scraped_ref_ru(title, title)
        book_key = _ru_book_key(title)
    else:
        # English scraped: uses ":" separator (e.g., "Hebrews 10:35-11:7")
        segments = _extract_scraped_ref_en(title, reference)
        book_key = _engine_book_from_display(title)

    if not segments:
        return

    ref_key = _normalize_ref_key(segments)
    if not ref_key:
        return

    key = (book_key, ref_key)
    # Prefer entries with text
    if key not in index or (entry.get('text') and not index[key].get('text')):
        index[key] = entry


def _sr_book_key(title: str) -> str:
    """Extract a book identifier from a Serbian title for indexing."""
    title_lower = title.lower()
    if 'матеј' in title_lower or 'матеј' in title:
        return 'Matthew'
    if 'марк' in title_lower:
        return 'Mark'
    if 'лук' in title_lower:
        return 'Luke'
    if 'јован' in title_lower and ('јеванђеље' in title_lower or 'богослов' in title_lower):
        # Distinguish John's Gospel from John's Epistles
        if 'јеванђеље' in title_lower:
            return 'John'
        if 'саборна' in title_lower or 'посланица' in title_lower:
            return 'Epistles_John'
        return 'John'
    if 'јеврејим' in title_lower:
        return 'Hebrews'
    if 'римљаним' in title_lower:
        return 'Romans'
    if 'коринћаним' in title_lower:
        if 'прва' in title_lower or 'друга' not in title_lower:
            return '1Corinthians'
        return '2Corinthians'
    if 'галатим' in title_lower:
        return 'Galatians'
    if 'ефесцим' in title_lower:
        return 'Ephesians'
    if 'филипљаним' in title_lower:
        return 'Philippians'
    if 'колосјаним' in title_lower or 'колошаним' in title_lower:
        return 'Colossians'
    if 'солуњаним' in title_lower:
        if 'прва' in title_lower:
            return '1Thessalonians'
        return '2Thessalonians'
    if 'тимотеју' in title_lower:
        if 'прва' in title_lower:
            return '1Timothy'
        return '2Timothy'
    if 'титу' in title_lower or 'тит' in title_lower:
        return 'Titus'
    if 'филимон' in title_lower:
        return 'Philemon'
    if 'јаков' in title_lower:
        return 'James'
    if 'петр' in title_lower:
        if 'друга' in title_lower:
            return '2Peter'
        return '1Peter'
    if 'јуд' in title_lower:
        return 'Jude'
    if 'дел' in title_lower and 'апостол' in title_lower:
        return 'Acts'
    if 'откривењ' in title_lower:
        return 'Revelation'
    # OT books
    if 'исаиј' in title_lower:
        return 'Isaiah'
    if 'јоил' in title_lower:
        return 'Joel'
    if 'приче' in title_lower:
        return 'Proverbs'
    if 'премудрост' in title_lower:
        return 'Wisdom'
    # Generic
    return 'unknown'


def _ru_book_key(title: str) -> str:
    """Extract a book identifier from a Russian title for indexing."""
    # Russian titles start with abbreviation: "Мк.10:17–27"
    abbr_map = {
        'Мф': 'Matthew', 'Мк': 'Mark', 'Лк': 'Luke', 'Ин': 'John',
        'Деян': 'Acts', 'Рим': 'Romans',
        '1Кор': '1Corinthians', '2Кор': '2Corinthians',
        'Гал': 'Galatians', 'Еф': 'Ephesians', 'Флп': 'Philippians',
        'Кол': 'Colossians', '1Фес': '1Thessalonians', '2Фес': '2Thessalonians',
        '1Тим': '1Timothy', '2Тим': '2Timothy',
        'Тит': 'Titus', 'Флм': 'Philemon',
        'Евр': 'Hebrews', 'Иак': 'James',
        '1Пет': '1Peter', '2Пет': '2Peter',
        '1Ин': '1John', '2Ин': '2John', '3Ин': '3John',
        'Иуд': 'Jude', 'Откр': 'Revelation',
        'Быт': 'Genesis', 'Исх': 'Exodus', 'Ис': 'Isaiah',
        'Иер': 'Jeremiah', 'Иез': 'Ezekiel', 'Дан': 'Daniel',
        'Притч': 'Proverbs', 'Прем': 'Wisdom', 'Сир': 'Sirach',
        'Иоил': 'Joel', 'Ион': 'Jonah', 'Зах': 'Zechariah', 'Мал': 'Malachi',
    }
    for abbr, book in sorted(abbr_map.items(), key=lambda x: -len(x[0])):
        if title.startswith(abbr + '.') or title.startswith(abbr + ' ') or title.startswith(abbr + ':'):
            return book
    return 'unknown'


def _engine_book_key(book: str) -> str:
    """Convert engine book name to our standard book key."""
    # The engine uses: 'Matthew', 'Mark', 'Luke', 'John', 'Apostol', etc.
    # 'Apostol' is a composite book for epistles - we need the display to determine actual book
    return book if book != 'Apostol' else 'Apostol'


def _engine_book_from_display(display: str) -> str:
    """Extract book key from engine display string like 'Hebrews 10.35-11.7'."""
    book_map = {
        'Matthew': 'Matthew', 'Mark': 'Mark', 'Luke': 'Luke', 'John': 'John',
        'Acts': 'Acts', 'Romans': 'Romans',
        '1 Corinthians': '1Corinthians', '2 Corinthians': '2Corinthians',
        'Galatians': 'Galatians', 'Ephesians': 'Ephesians',
        'Philippians': 'Philippians', 'Colossians': 'Colossians',
        '1 Thessalonians': '1Thessalonians', '2 Thessalonians': '2Thessalonians',
        '1 Timothy': '1Timothy', '2 Timothy': '2Timothy',
        'Titus': 'Titus', 'Philemon': 'Philemon',
        'Hebrews': 'Hebrews', 'James': 'James',
        '1 Peter': '1Peter', '2 Peter': '2Peter',
        '1 John': '1John', '2 John': '2John', '3 John': '3John',
        'Jude': 'Jude', 'Revelation': 'Revelation',
        'Genesis': 'Genesis', 'Exodus': 'Exodus',
        'Isaiah': 'Isaiah', 'Jeremiah': 'Jeremiah',
        'Ezekiel': 'Ezekiel', 'Daniel': 'Daniel',
        'Proverbs': 'Proverbs', 'Wisdom': 'Wisdom', 'Sirach': 'Sirach',
        'Joel': 'Joel', 'Jonah': 'Jonah', 'Zechariah': 'Zechariah',
        'Malachi': 'Malachi',
    }
    for name, key in sorted(book_map.items(), key=lambda x: -len(x[0])):
        if display.startswith(name + ' '):
            return key
    return 'unknown'


def load_scraped_data(locale: str) -> dict:
    """Load scraped data for backward compatibility. Returns the raw structure."""
    if locale == 'en':
        return {'byPaschaDistance': {}, 'byJulianDate': {}}
    proc_dir = os.path.join(DATA_DIR, 'processed', locale)
    if locale == 'sr':
        path = os.path.join(proc_dir, 'lectionary_merged.json')
    else:
        path = os.path.join(proc_dir, 'lectionary_complete.json')
    if not os.path.exists(path):
        return {'byPaschaDistance': {}, 'byJulianDate': {}}
    with open(path) as f:
        data = json.load(f)
    return {
        'byPaschaDistance': data.get('byPaschaDistance', {}),
        'byJulianDate': data.get('byJulianDate', {}),
    }


# ---------------------------------------------------------------------------
# Matching engine — uses global index
# ---------------------------------------------------------------------------

def _find_matching_in_index(engine_reading: dict, text_index: dict) -> dict:
    """
    Find a scraped reading that matches the engine reading using the global text index.

    Returns the scraped entry if found, or None.
    """
    engine_display = engine_reading.get('display') or engine_reading.get('sdisplay', '')
    if not engine_display:
        return None

    engine_segments = _extract_chapter_verses(engine_display)
    if not engine_segments:
        return None

    book_key = _engine_book_from_display(engine_display)
    ref_key = _normalize_ref_key(engine_segments)

    if not ref_key:
        return None

    # Direct lookup
    result = text_index.get((book_key, ref_key))
    if result:
        return result

    # Try fuzzy matching: check if the engine segments overlap with any indexed entry
    # for the same book
    for (idx_book, idx_ref), entry in text_index.items():
        if idx_book != book_key:
            continue
        # Parse the indexed ref back to segments for overlap check
        idx_segments = []
        for part in idx_ref.split('|'):
            m = re.match(r'(\d+):(\d+)-(\d+)', part)
            if m:
                idx_segments.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        if _segments_overlap(engine_segments, idx_segments):
            return entry

    return None


def generate_readings_for_day(
    greg_date: date,
    text_index: dict,
    julian_readings: dict,
    locale: str,
    title_index: dict = None,
) -> list:
    """
    Generate readings for a single day by combining engine output with scraped text.

    Returns a list of reading entries in the format expected by the calendar JSON.
    """
    year, month, day = greg_date.year, greg_date.month, greg_date.day

    # Get engine readings
    engine_readings = get_readings(year, month, day)

    # Julian date for fixed feast lookups
    julian = greg_date - timedelta(days=JULIAN_OFFSET)
    julian_key = f"{julian.month:02d}-{julian.day:02d}"

    # Fixed feast readings from scraped Julian date data
    julian_scraped = julian_readings.get(julian_key, [])

    result = []
    used_julian_indices = set()

    # Process each engine reading
    for eng in engine_readings:
        source = eng.get('source', '')
        desc = eng.get('desc', '')
        display = eng.get('display') or eng.get('sdisplay', '')

        # Find matching scraped reading in the global index
        matched = _find_matching_in_index(eng, text_index)

        # Also try matching against the Julian date scraped entries
        if not matched:
            for i, js in enumerate(julian_scraped):
                if i in used_julian_indices:
                    continue
                title = js.get('title', '')
                reference = js.get('reference', '')
                if locale == 'sr':
                    js_segments = _extract_scraped_ref_sr(title, reference)
                elif locale == 'ru':
                    js_segments = _extract_scraped_ref_ru(title, title)
                else:
                    js_segments = _extract_chapter_verses(title)
                engine_segments = _extract_chapter_verses(display)
                if _segments_overlap(engine_segments, js_segments):
                    matched = js
                    used_julian_indices.add(i)
                    break

        if matched:
            entry = {
                'title': matched.get('title', ''),
                'type': matched.get('type', 'apostol' if source == 'Epistle' else 'gospel'),
            }
            if matched.get('text'):
                entry['text'] = matched['text']
            if matched.get('zachalo'):
                entry['zachalo'] = matched['zachalo']
            if matched.get('reference'):
                entry['reference'] = matched['reference']
            entry['source'] = source
            if desc:
                entry['desc'] = desc
            result.append(entry)
        else:
            # No scraped day-text matched. Fill the text from a Bible source using
            # the engine's known reference — this covers the festal/weekday
            # readings the day-scrape doesn't provide. (sr: pravoslavno.rs Bible;
            # en: KJV + Brenton Septuagint.)
            if locale == 'sr':
                filled = _sr_bible_fill(eng)
            elif locale == 'en':
                filled = _en_bible_fill(eng)
            else:
                filled = None
            if filled:
                filled['source'] = source
                if desc:
                    filled['desc'] = desc
                result.append(filled)
                continue

            # Map engine source to app-compatible type
            if source == 'Epistle':
                reading_type = 'apostol'
            elif source == 'Gospel' or source == 'Matins Gospel':
                reading_type = 'gospel'
            elif source in ('Vespers', '1st Hour, Prophecy', '3rd Hour, Prophecy',
                            '6th Hour, Prophecy', '9th Hour, Prophecy'):
                reading_type = 'ot'
            elif 'Passion Gospel' in source:
                reading_type = 'gospel'
            else:
                reading_type = 'gospel'
            entry = {
                'title': display,
                'type': reading_type,
                'source': source,
                'engineRef': display,
            }
            if desc:
                entry['desc'] = desc
            result.append(entry)

    # Add unmatched Julian date scraped readings (fixed feast readings engine doesn't know)
    for i, scraped in enumerate(julian_scraped):
        if i not in used_julian_indices:
            entry = dict(scraped)
            if 'source' not in entry:
                entry['source'] = 'fixed'
            result.append(entry)

    if locale == 'sr':
        # Recover text for readings left empty: the same reading is often indexed
        # elsewhere (a different Julian date / pascha distance) with its full text.
        # Match by exact localized title.
        if title_index:
            for r in result:
                if (r.get('text') or '').strip():
                    continue
                src = title_index.get((r.get('title') or '').strip())
                if src:
                    r['text'] = src['text']
                    if not r.get('zachalo') and src.get('zachalo'):
                        r['zachalo'] = src['zachalo']

        # Strip service-section headers ("На вечерњи" …) that bled into the text.
        for r in result:
            if r.get('text'):
                r['text'] = _strip_service_tail(r['text'])

    # Remove engine-only readings with English titles (no localized content)
    result = [r for r in result if not r.get('engineRef') or r.get('text')]

    if locale == 'sr':
        # Drop orphaned verse fragments: a reading the scraper split per-verse
        # onto its own <b> tag, leaving no reference, no book/зачало title, and no
        # recoverable text. (Fragments that carry text are kept above.)
        result = [r for r in result if not _is_orphan_fragment(r)]

    if locale == 'en' and _load_en_bible():
        # Use only public-domain text (KJV NT + Brenton Septuagint OT). Replace
        # every reading's text with the same passage assembled from the
        # public-domain Bible; readings that can't be assembled (e.g. Composite
        # catenae) keep their reference but show no body rather than ship the
        # copyrighted NKJV scrape text.
        for r in result:
            book, ref_part = _en_parse_ref(r.get('reference') or r.get('title') or '', ':')
            r['text'] = _en_bible_text(book, ref_part, ':') if book else None

    # Sort by liturgical service order
    SERVICE_ORDER = {
        '1st Passion Gospel': 21, '2nd Passion Gospel': 22, '3rd Passion Gospel': 23,
        '4th Passion Gospel': 24, '5th Passion Gospel': 25, '6th Passion Gospel': 26,
        '7th Passion Gospel': 27, '8th Passion Gospel': 28, '9th Passion Gospel': 29,
        '10th Passion Gospel': 30, '11th Passion Gospel': 31, '12th Passion Gospel': 32,
        '1st Hour': 100, '3rd Hour': 200, '6th Hour': 300, '9th Hour': 400,
        'Vespers': 500, 'Matins Gospel': 700,
        'Epistle': 800, 'Gospel': 900,
        'fixed': 950,
    }
    result.sort(key=lambda r: SERVICE_ORDER.get(r.get('source', ''), 850))

    # Deduplicate by title
    seen = set()
    deduped = []
    for r in result:
        title = r.get('title', '')
        if title and title in seen:
            continue
        if title:
            seen.add(title)
        deduped.append(r)

    return deduped


def generate_all_readings(year: int, locale: str) -> dict:
    """
    Generate readings for all days in a year.

    Returns a dict mapping "MM-DD" keys to lists of reading entries.
    """
    text_index, julian_readings, title_index = _build_scraped_index(locale)

    readings = {}
    current = date(year, 1, 1)
    end = date(year, 12, 31)

    total_with_readings = 0
    total_with_text = 0
    total_engine_only = 0
    total_scraped_only = 0

    while current <= end:
        key = current.strftime("%m-%d")
        day_readings = generate_readings_for_day(current, text_index, julian_readings, locale, title_index)
        readings[key] = day_readings

        if day_readings:
            total_with_readings += 1
            has_text = any(r.get('text') for r in day_readings)
            if has_text:
                total_with_text += 1
            engine_only = sum(1 for r in day_readings if r.get('engineRef') and not r.get('text'))
            scraped_only = sum(1 for r in day_readings if r.get('source') == 'fixed')
            total_engine_only += engine_only
            total_scraped_only += scraped_only

        current += timedelta(days=1)

    print(f"  [{locale}] Year {year}: {total_with_readings} days with readings, "
          f"{total_with_text} with text, "
          f"{total_engine_only} engine-only refs, "
          f"{total_scraped_only} scraped-only refs", file=sys.stderr)

    return readings


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_years(years: list, locale: str):
    """Validate readings across multiple years."""
    results = {}
    for year in years:
        print(f"\n--- Generating {locale} readings for {year} ---", file=sys.stderr)
        readings = generate_all_readings(year, locale)
        results[year] = readings

    # Check fixed feasts have same readings across years
    # Nativity: Jan 7 (Gregorian) = Dec 25 Julian
    nativity_key = "01-07"
    # Theophany: Jan 19 (Gregorian) = Jan 6 Julian
    theophany_key = "01-19"

    print(f"\n--- Fixed Feast Validation ({locale}) ---", file=sys.stderr)
    for feast_name, feast_key in [("Nativity", nativity_key), ("Theophany", theophany_key)]:
        titles_by_year = {}
        for year in years:
            titles = [r.get('title', '') for r in results[year].get(feast_key, [])]
            titles_by_year[year] = titles

        all_same = all(titles_by_year[y] == titles_by_year[years[0]] for y in years[1:])
        status = "PASS" if all_same else "DIFF"
        print(f"  {feast_name} ({feast_key}): {status}", file=sys.stderr)
        if not all_same:
            for y in years:
                count = len(titles_by_year[y])
                print(f"    {y}: {count} readings", file=sys.stderr)

    # Check that moveable feast days differ between years
    # Pick a regular weekday - June 15
    check_key = "06-15"
    print(f"\n--- Moveable Reading Validation ({locale}) ---", file=sys.stderr)
    titles_by_year = {}
    for year in years:
        titles = [r.get('title', '') for r in results[year].get(check_key, []) if r.get('title')]
        titles_by_year[year] = titles

    # They should differ for at least some years
    all_same = all(titles_by_year[y] == titles_by_year[years[0]] for y in years[1:])
    if not all_same:
        print(f"  June 15 readings differ across years: PASS", file=sys.stderr)
    else:
        print(f"  June 15 readings same across years: EXPECTED DIFF (may be OK for some dates)", file=sys.stderr)

    for y in years:
        print(f"    {y}: {titles_by_year[y][:2]}...", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if '--validate' in sys.argv:
        args = [a for a in sys.argv[1:] if a != '--validate']
    else:
        args = sys.argv[1:]
    year = int(args[0]) if args else 2026

    if '--validate' in sys.argv:
        years = [2026, 2027, 2028]
        for locale in ['sr', 'ru', 'en']:
            validate_years(years, locale)
        return

    for locale in ['sr', 'ru', 'en']:
        print(f"\n=== Generating readings for {locale} {year} ===", file=sys.stderr)
        readings = generate_all_readings(year, locale)

        output_path = os.path.join(DATA_DIR, 'output', f'readings_{locale}_{year}.json')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({
                'year': year,
                'locale': locale,
                'generatedBy': 'generate_readings.py (lectionary engine + scraped text)',
                'days': readings,
            }, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {output_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
