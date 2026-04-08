#!/usr/bin/env python3
"""
Lectionary Engine — Orthodox Typikon lectionary algorithm.

Ported from the Go orthocal library. Computes daily scripture readings
by calculating pascha distance (pdist), applying the Lucan Jump for
Gospel readings after the Elevation of the Cross, and looking up
readings from parsed SQL data (no SQLite dependency).

Usage:
    from lectionary_engine import get_readings, get_tone
    readings = get_readings(2026, 1, 7)   # Nativity
    tone = get_tone(2026, 4, 19)          # 1st Sunday after Pascha
"""

import os
import re
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday = range(7)

# ---------------------------------------------------------------------------
# Date tools  (ported from orthocal/datetools.go)
# ---------------------------------------------------------------------------

def _trunc_div(a: int, b: int) -> int:
    """Integer division truncating toward zero (Go/C semantics)."""
    return int(a / b)


def julian_date_to_jdn(year: int, month: int, day: int) -> int:
    """Convert a Julian calendar date to a Julian Day Number."""
    # Uses Go/C truncation semantics for integer division
    return (367 * year
            - _trunc_div(7 * (year + 5001 + _trunc_div(month - 9, 7)), 4)
            + _trunc_div(275 * month, 9)
            + day + 1729777)


def gregorian_date_to_jdn(year: int, month: int, day: int) -> int:
    """Convert a Gregorian calendar date to a Julian Day Number (PHP-style)."""
    if month > 2:
        month -= 3
    else:
        month += 9
        year -= 1
    century = year // 100
    ya = year - 100 * century
    return (146097 * century) // 4 + (1461 * ya) // 4 + (153 * month + 2) // 5 + day + 1721119


def compute_julian_pascha(year: int) -> Tuple[int, int]:
    """Meeus Julian algorithm -> (month, day) on the Julian calendar."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return month, day


def compute_pascha_jdn(year: int) -> int:
    """JDN of Pascha for *year* (based on the Julian calendar)."""
    m, d = compute_julian_pascha(year)
    return julian_date_to_jdn(year, m, d)


def compute_pascha_distance(year: int, month: int, day: int) -> Tuple[int, int]:
    """
    Compute distance of a Gregorian date from Pascha.
    Returns (pdist, pyear).  pyear may be year-1 when the date is
    early in the church year (before ~70 days before Pascha).
    """
    jdn = gregorian_date_to_jdn(year, month, day)
    distance = jdn - compute_pascha_jdn(year)
    if distance < -77:
        year -= 1
        distance = jdn - compute_pascha_jdn(year)
    return distance, year


def weekday_from_pdist(pdist: int) -> int:
    """0=Sun 1=Mon ... 6=Sat, same convention as the Go code."""
    return (7 + pdist % 7) % 7


def surrounding_weekends(pdist: int) -> Tuple[int, int, int, int]:
    """Return (satBefore, sunBefore, satAfter, sunAfter) relative to *pdist*."""
    wd = weekday_from_pdist(pdist)
    sat_before = pdist - wd - 1
    sun_before = pdist - 7 + ((7 - wd) % 7)
    sat_after  = pdist + 7 - ((wd + 1) % 7)
    sun_after  = pdist + 7 - wd
    return sat_before, sun_before, sat_after, sun_after


def gregorian_to_julian_date(year: int, month: int, day: int) -> date:
    """Subtract 13 days to convert Gregorian -> Julian (2001-2099)."""
    return date(year, month, day) - timedelta(days=13)


# ---------------------------------------------------------------------------
# SQL Parsing — build in-memory lookup tables from .sql dump files
# ---------------------------------------------------------------------------

_INSERT_RE = re.compile(
    r"insert\s+into\s+(\w+)\s+values\s*\((.+?)\)\s*;",
    re.IGNORECASE,
)


def _parse_sql_value(v: str):
    v = v.strip()
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    if v.lower() == 'null':
        return None
    try:
        return int(v)
    except ValueError:
        return v


def _split_sql_values(s: str) -> list:
    """Split a comma-separated SQL values string respecting single quotes."""
    parts = []
    current = []
    in_quote = False
    for ch in s:
        if ch == "'" and not in_quote:
            in_quote = True
            current.append(ch)
        elif ch == "'" and in_quote:
            in_quote = False
            current.append(ch)
        elif ch == ',' and not in_quote:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return [_parse_sql_value(p) for p in parts]


def _parse_sql_file(path: str) -> List[tuple]:
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = _INSERT_RE.match(line.strip())
            if m:
                vals = _split_sql_values(m.group(2))
                rows.append(tuple(vals))
    return rows


# Parsed data singletons
_readings_rows: Optional[List[tuple]] = None
_pericopes_map: Optional[Dict[Tuple[str, str], dict]] = None


_custom_sql_dir: Optional[str] = None


def set_sql_dir(path: str):
    """Set a custom directory for the SQL data files."""
    global _custom_sql_dir, _readings_rows, _pericopes_map
    _custom_sql_dir = path
    # Reset cached data so it reloads from the new path
    _readings_rows = None
    _pericopes_map = None


def _sql_dir() -> str:
    if _custom_sql_dir:
        return _custom_sql_dir
    # Try data/processed/shared first, fall back to /tmp
    base = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'shared')
    if os.path.exists(os.path.join(base, 'readings.sql')):
        return base
    return '/tmp'


def _ensure_loaded():
    global _readings_rows, _pericopes_map
    if _readings_rows is not None:
        return

    sql_dir = _sql_dir()

    # Parse readings - try both naming conventions
    readings_path = os.path.join(sql_dir, 'readings.sql')
    if not os.path.exists(readings_path):
        readings_path = os.path.join(sql_dir, 'orthocal_readings.sql')
    _readings_rows = _parse_sql_file(readings_path)

    # Parse pericopes into dict keyed by (book, pericope)
    pericopes_path = os.path.join(sql_dir, 'pericopes.sql')
    if not os.path.exists(pericopes_path):
        pericopes_path = os.path.join(sql_dir, 'orthocal_pericopes.sql')
    pericope_rows = _parse_sql_file(pericopes_path)
    _pericopes_map = {}
    for row in pericope_rows:
        # pericope, book, display, sdisplay, desc, preverse, prefix, prefixb, verses, suffix, flag
        pericope_id = str(row[0])
        book = str(row[1])
        display = str(row[2]) if row[2] else ''
        sdisplay = str(row[3]) if row[3] else ''
        _pericopes_map[(book, pericope_id)] = {
            'display': display,
            'sdisplay': sdisplay,
        }


def _lookup_pericope(book: str, pericope: str) -> Tuple[str, str]:
    """Return (display, sdisplay) for a given book+pericope, or ('', '')."""
    _ensure_loaded()
    key = (book, pericope)
    info = _pericopes_map.get(key, {})
    return info.get('display', ''), info.get('sdisplay', '')


# ---------------------------------------------------------------------------
# Reading row: (month, day, pdist, source, desc, book, pericope, ordering, flag)
#               0      1    2      3       4     5     6         7         8
# ---------------------------------------------------------------------------

def _query_readings(
    *,
    pdist_values: List[int],
    month_day_pairs: List[Tuple[int, int]],
    source_filters: Optional[Dict[str, List[str]]] = None,
    epistle_pdist: int,
    gospel_pdist: int,
    day_pdist: int,
    no_departed: bool = False,
    no_matins_gospel_for_monthday: bool = False,
    no_vespers_for_monthday: bool = False,
    no_theotokos_annunciation: bool = False,
) -> List[dict]:
    """
    Query the in-memory readings table, mimicking the SQL query from addReadings().

    The Go query is:
      WHERE
        (pdist = gPDist AND source = 'Gospel' ...)
        OR (pdist = ePDist AND source = 'Epistle' ...)
        OR (pdist = day.PDist AND source != 'Epistle' AND source != 'Gospel')
        OR (pdist = floatIndex)
        OR (pdist = matinsGospel+700)
        OR (month = M AND day = D ...)
    """
    _ensure_loaded()

    results = []
    departed_filter = no_departed

    for row in _readings_rows:
        r_month, r_day, r_pdist, r_source, r_desc, r_book, r_pericope, r_ordering, r_flag = row

        matched = False

        # Gospel by pdist
        if r_month == 0 and r_day == 0 and r_pdist == gospel_pdist and r_source == 'Gospel':
            if departed_filter and r_desc == 'Departed':
                continue
            matched = True

        # Epistle by pdist
        if r_month == 0 and r_day == 0 and r_pdist == epistle_pdist and r_source == 'Epistle':
            if departed_filter and r_desc == 'Departed':
                continue
            matched = True

        # Other sources by day pdist (not Epistle or Gospel)
        if r_month == 0 and r_day == 0 and r_pdist == day_pdist and r_source != 'Epistle' and r_source != 'Gospel':
            matched = True

        # Float / matins gospel pdists
        for pv in pdist_values:
            if r_month == 0 and r_day == 0 and r_pdist == pv:
                matched = True
                break

        # Month/day matches
        for (mm, dd) in month_day_pairs:
            if r_month == mm and r_day == dd:
                # Apply filters for month/day matches
                if no_matins_gospel_for_monthday and r_source == 'Matins Gospel' and r_month == mm and r_day == dd and (mm, dd) == month_day_pairs[0]:
                    # Only suppress for the primary month/day, not paremias
                    continue
                if no_vespers_for_monthday and r_source == 'Vespers' and (mm, dd) == month_day_pairs[0]:
                    continue
                if no_theotokos_annunciation and r_desc == 'Theotokos' and (mm, dd) == month_day_pairs[0]:
                    continue
                matched = True
                break

        if matched:
            book_str = str(r_book) if r_book else ''
            pericope_str = str(r_pericope) if r_pericope else ''
            display, sdisplay = _lookup_pericope(book_str, pericope_str)
            results.append({
                'source': r_source or '',
                'desc': r_desc or '',
                'book': book_str,
                'pericope': pericope_str,
                'display': display,
                'sdisplay': sdisplay,
                'ordering': r_ordering,
            })

    # Sort by ordering
    results.sort(key=lambda r: r['ordering'])

    return results


# ---------------------------------------------------------------------------
# Year class (ported from orthocal/year.go)
# ---------------------------------------------------------------------------

class Year:
    """Precompute all year-specific values for the lectionary algorithm."""

    def __init__(self, year: int):
        self.year = year
        self.pascha = compute_pascha_jdn(year)
        self.previous_pascha = compute_pascha_jdn(year - 1)
        self.next_pascha = compute_pascha_jdn(year + 1)

        self.floats: List[Tuple[int, int]] = []  # (index, pdist)
        self.no_daily: set = set()
        self.reserves: List[int] = []
        self.paremias: List[int] = [499]
        self.no_paremias: List[int] = [499]
        self.extra_sundays = 0

        self._compute_pdists()
        self._compute_floats()
        self._compute_no_daily_readings()
        self._compute_reserves()
        self._compute_paremias()

    def date_to_pdist(self, month: int, day: int, year: int) -> int:
        """Convert a Julian calendar date to a distance from Pascha."""
        return julian_date_to_jdn(year, month, day) - self.pascha

    def _compute_pdists(self):
        self.theophany = self.date_to_pdist(1, 6, self.year + 1)
        self.finding = self.date_to_pdist(2, 24, self.year)
        self.annunciation = self.date_to_pdist(3, 25, self.year)
        self.peter_and_paul = self.date_to_pdist(6, 29, self.year)

        # Fathers of 6th Ecumenical Council: Sunday nearest 7/16
        pdist = self.date_to_pdist(7, 16, self.year)
        wd = weekday_from_pdist(pdist)
        if wd < Thursday:
            self.fathers_six = pdist - wd
        else:
            self.fathers_six = pdist + 7 - wd

        self.beheading = self.date_to_pdist(8, 29, self.year)
        self.nativity_theotokos = self.date_to_pdist(9, 8, self.year)
        self.elevation = self.date_to_pdist(9, 14, self.year)

        # Fathers of 7th Ecumenical Council: Sunday on or after 10/11
        pdist = self.date_to_pdist(10, 11, self.year)
        wd = weekday_from_pdist(pdist)
        if wd > Sunday:
            pdist += 7 - wd
        self.fathers_seven = pdist

        # Demetrius Saturday: Saturday before 10/26
        pdist = self.date_to_pdist(10, 26, self.year)
        self.demetrius_saturday = pdist - weekday_from_pdist(pdist) - 1

        # Synaxis of the Unmercenaries: Sunday following 11/1
        pdist = self.date_to_pdist(11, 1, self.year)
        self.synaxis_unmercenaries = pdist + 7 - weekday_from_pdist(pdist)

        self.nativity = self.date_to_pdist(12, 25, self.year)

        # Forefathers Sunday: 2 weeks before the Sunday of Nativity week
        wd = weekday_from_pdist(self.nativity)
        self.forefathers = self.nativity - 14 + ((7 - wd) % 7)

        # Lucan Jump = 168 - (Sunday after Elevation)
        self.lucan_jump = 168 - (self.elevation + 7 - weekday_from_pdist(self.elevation))

    def _add_float(self, index: int, pdist: int):
        self.floats.append((index, pdist))

    def _compute_floats(self):
        self._add_float(1001, self.fathers_six)
        self._add_float(1002, self.fathers_seven)
        self._add_float(1003, self.demetrius_saturday)
        self._add_float(1004, self.synaxis_unmercenaries)

        # Floats around the Elevation of the Cross
        sat_before, sun_before, sat_after, sun_after = surrounding_weekends(self.elevation)
        if sat_before == self.nativity_theotokos:
            self._add_float(1005, self.elevation - 1)
        else:
            self._add_float(1006, sat_before)
        self._add_float(1007, sun_before)
        self._add_float(1008, sat_after)
        self._add_float(1009, sun_after)
        self._add_float(1010, self.forefathers)

        # Floats around Nativity
        sat_before, sun_before, sat_after, sun_after = surrounding_weekends(self.nativity)
        eve = self.nativity - 1
        if eve == sat_before:
            self._add_float(1013, self.nativity - 2)
            self._add_float(1012, sun_before)
            self._add_float(1015, eve)
        elif eve == sun_before:
            self._add_float(1013, self.nativity - 3)
            self._add_float(1011, sat_before)
            self._add_float(1016, eve)
        else:
            self._add_float(1014, eve)
            self._add_float(1011, sat_before)
            self._add_float(1012, sun_before)

        sat_before_th, sun_before_th, sat_after_th, sun_after_th = surrounding_weekends(self.theophany)
        nat_wd = weekday_from_pdist(self.nativity)

        if nat_wd == Sunday:
            self._add_float(1017, sat_after)
            self._add_float(1020, self.nativity + 1)
            self._add_float(1024, sun_before_th)
            self._add_float(1026, self.theophany - 1)
        elif nat_wd == Monday:
            self._add_float(1017, sat_after)
            self._add_float(1021, sun_after)
            self._add_float(1023, self.theophany - 5)
            self._add_float(1026, self.theophany - 1)
        elif nat_wd == Tuesday:
            self._add_float(1019, sat_after)
            self._add_float(1021, sun_after)
            self._add_float(1027, sat_before_th)
            self._add_float(1023, self.theophany - 5)
            self._add_float(1025, self.theophany - 2)
        elif nat_wd == Wednesday:
            self._add_float(1019, sat_after)
            self._add_float(1021, sun_after)
            self._add_float(1022, sat_before_th)
            self._add_float(1028, sun_before_th)
            self._add_float(1025, self.theophany - 3)
        elif nat_wd in (Thursday, Friday):
            self._add_float(1019, sat_after)
            self._add_float(1021, sun_after)
            self._add_float(1022, sat_before_th)
            self._add_float(1024, sun_before_th)
            self._add_float(1026, self.theophany - 1)
        elif nat_wd == Saturday:
            self._add_float(1018, self.nativity + 6)
            self._add_float(1021, sun_after)
            self._add_float(1022, sat_before_th)
            self._add_float(1024, sun_before_th)
            self._add_float(1026, self.theophany - 1)

        self._add_float(1029, sat_after_th)
        self._add_float(1030, sun_after_th)

        # New Martyrs of Russia (OCA): Sunday on or before 1/31
        martyrs = self.date_to_pdist(1, 31, self.year)
        wd = weekday_from_pdist(martyrs)
        if wd != Sunday:
            martyrs = martyrs - 7 + ((7 - wd) % 7)
        self._add_float(1031, martyrs)

        # Floats around Annunciation
        ann_wd = weekday_from_pdist(self.annunciation)
        if ann_wd == Saturday:
            self._add_float(1032, self.annunciation - 1)
            self._add_float(1033, self.annunciation)
        elif ann_wd == Sunday:
            self._add_float(1034, self.annunciation)
        elif ann_wd == Monday:
            self._add_float(1035, self.annunciation)
        else:
            self._add_float(1036, self.annunciation - 1)
            self._add_float(1037, self.annunciation)

    def _compute_no_daily_readings(self):
        _, sun_before, sat_after, sun_after = surrounding_weekends(self.theophany)
        self.no_daily.add(sun_before)
        self.no_daily.add(sun_after)
        self.no_daily.add(self.theophany - 5)
        self.no_daily.add(self.theophany - 1)
        self.no_daily.add(self.theophany)
        if sat_after == self.theophany + 1:
            self.no_daily.add(self.theophany + 1)

        self.no_daily.add(self.forefathers)

        _, sun_before, _, sun_after = surrounding_weekends(self.nativity)
        self.no_daily.add(sun_before)
        self.no_daily.add(self.nativity - 1)
        self.no_daily.add(self.nativity)
        self.no_daily.add(self.nativity + 1)
        self.no_daily.add(sun_after)

        if weekday_from_pdist(self.annunciation) == Saturday:
            self.no_daily.add(self.annunciation)

    def _compute_reserves(self):
        _, _, _, sun_after = surrounding_weekends(self.theophany)
        self.extra_sundays = (self.next_pascha - self.pascha - 84 - sun_after) // 7

        if self.extra_sundays > 0:
            i = self.forefathers + self.lucan_jump + 7
            while i <= 266:
                self.reserves.append(i)
                i += 7
            remainder = self.extra_sundays - len(self.reserves)
            if remainder > 0:
                j = 175 - remainder * 7
                while j < 169:
                    self.reserves.append(j)
                    j += 7

    def _compute_paremias(self):
        days = [
            (2, 24), (2, 27), (3, 9), (3, 31),
            (4, 7), (4, 23), (4, 25), (4, 30),
        ]
        for (m, d) in days:
            pdist = self.date_to_pdist(m, d, self.year)
            wd = weekday_from_pdist(pdist)
            if pdist > -44 and pdist < -7 and wd > 1:
                self.paremias.append(pdist - 1)
                self.no_paremias.append(pdist)

    def lookup_float_index(self, pdist: int) -> int:
        for idx, pd in self.floats:
            if pd == pdist:
                return idx
        return 499

    def has_paremias(self, pdist: int) -> bool:
        return pdist in self.paremias

    def has_no_paremias(self, pdist: int) -> bool:
        return pdist in self.no_paremias

    def has_no_daily_readings(self, pdist: int) -> bool:
        return pdist in self.no_daily


# Year cache
_year_cache: Dict[int, Year] = {}


def _get_year(pyear: int) -> Year:
    if pyear not in _year_cache:
        _year_cache[pyear] = Year(pyear)
    return _year_cache[pyear]


# ---------------------------------------------------------------------------
# Matins Gospel (ported from day.go matinsGospel)
# ---------------------------------------------------------------------------

def _matins_gospel(pdist: int, weekday: int, jdn: int, year: Year, feast_level: int = 0) -> Tuple[bool, int]:
    """
    Returns (has_matins_gospel_from_monthday, matins_gospel_number).
    has_matins_gospel_from_monthday=True means we should include month/day Matins Gospel.
    matins_gospel_number > 0 means we add that number (+700) as a pdist query.
    """
    if weekday == Sunday:
        if pdist > -8 and pdist < 50:
            return False, 0
        elif feast_level < 7:
            pbase = pdist
            if pbase < 0:
                pbase = jdn - year.previous_pascha
            x = (pbase - 49) % 77
            if x == 0:
                x = 77
            return False, x // 7
    return True, 0


# ---------------------------------------------------------------------------
# Adjusted pdists (ported from day.go getAdjustedPDists)
# ---------------------------------------------------------------------------

def get_adjusted_pdists(pdist: int, weekday: int, jdn: int, year: Year, do_jump: bool = True) -> Tuple[int, int]:
    """
    Return (epistle_pdist, gospel_pdist) with Lucan Jump applied.
    """
    jump = 0
    _, _, _, sun_after_elev = surrounding_weekends(year.elevation)
    if do_jump and pdist > sun_after_elev:
        jump = year.lucan_jump

    if year.has_no_daily_readings(pdist):
        return 499, 499

    limit = 272

    # Epistle pdist
    if pdist == 252:
        e_pdist = year.forefathers
    elif pdist > limit:
        e_pdist = jdn - year.next_pascha
    else:
        e_pdist = pdist

    if weekday_from_pdist(year.theophany) < Tuesday:
        limit = 279

    # Gospel pdist
    _, _, _, sun_after_theoph = surrounding_weekends(year.theophany)
    if pdist == 245 - year.lucan_jump:
        g_pdist = year.forefathers + year.lucan_jump
    elif pdist > sun_after_theoph and weekday == Sunday and year.extra_sundays > 1:
        i = (pdist - sun_after_theoph) // 7
        if i - 1 < len(year.reserves):
            g_pdist = year.reserves[i - 1]
        else:
            g_pdist = pdist + jump
    elif pdist + jump > limit:
        # Theophany stepback
        g_pdist = jdn - year.next_pascha
    else:
        g_pdist = pdist + jump

    return e_pdist, g_pdist


# ---------------------------------------------------------------------------
# Tone (ported from day.go addTone)
# ---------------------------------------------------------------------------

def get_tone(year: int, month: int, day: int) -> int:
    """Return the tone (1-8) for a given Gregorian date, or 0 near Pascha."""
    pdist, pyear = compute_pascha_distance(year, month, day)
    yr = _get_year(pyear)
    jdn = gregorian_date_to_jdn(year, month, day)

    if -9 < pdist < 7:
        return 0

    pbase = pdist
    if pbase < 0:
        pbase = jdn - yr.previous_pascha

    x = pbase % 56
    if x == 0:
        x = 56
    return x // 7


# ---------------------------------------------------------------------------
# Main API: get_readings
# ---------------------------------------------------------------------------

def get_readings(year: int, month: int, day: int) -> List[dict]:
    """
    Return a list of readings for a given Gregorian date.

    Each reading is a dict with keys:
        source, desc, book, pericope, display, sdisplay
    """
    pdist, pyear = compute_pascha_distance(year, month, day)
    yr = _get_year(pyear)
    jdn = gregorian_date_to_jdn(year, month, day)
    weekday = weekday_from_pdist(pdist)

    # Convert Gregorian date to Julian for month/day lookups
    jul = gregorian_to_julian_date(year, month, day)
    jul_month, jul_day = jul.month, jul.day

    # Adjusted pdists for epistle and gospel
    e_pdist, g_pdist = get_adjusted_pdists(pdist, weekday, jdn, yr)

    # Float index
    float_index = yr.lookup_float_index(pdist)

    # Matins Gospel
    has_matins_from_md, matins_num = _matins_gospel(pdist, weekday, jdn, yr)

    # Build extra pdist values to query
    extra_pdists = []
    if float_index != 499:
        extra_pdists.append(float_index)
    if matins_num != 0:
        extra_pdists.append(matins_num + 700)

    # Build month/day pairs
    md_pairs = [(jul_month, jul_day)]

    # Paremias: if this day has paremias shifted from tomorrow
    if yr.has_paremias(pdist):
        tomorrow = date(year, month, day) + timedelta(days=1)
        jul_tom = gregorian_to_julian_date(tomorrow.year, tomorrow.month, tomorrow.day)
        # Only vespers paremias from tomorrow
        # We handle this by adding the month/day pair; the Go code filters by source='Vespers'
        # For simplicity we add the pair and note it's for Vespers
        md_pairs.append((jul_tom.month, jul_tom.day))

    # Has no memorial?
    no_departed = (
        (pdist == -36 or pdist == -29 or pdist == -22)
        and jul_month == 3
        and jul_day in (9, 24, 25, 26)
    )

    # Suppress Matins Gospel for month/day if has_matins_from_md is False
    no_matins_md = not has_matins_from_md

    # Suppress Vespers for month/day if no_paremias
    no_vespers_md = yr.has_no_paremias(pdist)

    # Suppress Theotokos for leavetaking Annunciation on non-liturgy weekday
    no_theotokos = (
        jul_month == 3 and jul_day == 26
        and weekday in (Monday, Tuesday, Thursday)
    )

    results = _query_readings(
        pdist_values=extra_pdists,
        month_day_pairs=md_pairs,
        epistle_pdist=e_pdist,
        gospel_pdist=g_pdist,
        day_pdist=pdist,
        no_departed=no_departed,
        no_matins_gospel_for_monthday=no_matins_md,
        no_vespers_for_monthday=no_vespers_md,
        no_theotokos_annunciation=no_theotokos,
    )

    # Move Lenten Matins Gospel to the top
    if pdist > -42 and pdist < -7:
        # feast_level check omitted since we don't have feast data here
        for i, r in enumerate(results):
            if r['source'] == 'Matins Gospel':
                mg = results.pop(i)
                results.insert(0, mg)
                break

    return results


# ---------------------------------------------------------------------------
# Convenience: format readings for display
# ---------------------------------------------------------------------------

def format_readings(readings: List[dict]) -> str:
    lines = []
    for r in readings:
        display = r.get('display') or r.get('sdisplay') or f"{r['book']} {r['pericope']}"
        desc = r.get('desc', '')
        src = r.get('source', '')
        if desc:
            lines.append(f"  {src} ({desc}): {display}")
        else:
            lines.append(f"  {src}: {display}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate():
    print("=== Lectionary Engine Validation ===\n")
    ok = True

    # 1. Nativity 2026: Jan 7 (Gregorian) = Dec 25 Julian
    print("--- 2026-01-07 (Nativity) ---")
    readings = get_readings(2026, 1, 7)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}  [{r['book']} {r['pericope']}]")
    # Check for Gal 4:4-7 and Mt 2:1-12
    found_gal = any('Galatians 4.4-7' in r.get('display', '') for r in readings)
    found_mt = any('Matthew 2.1-12' in r.get('display', '') for r in readings)
    if found_gal and found_mt:
        print("  [PASS] Nativity readings found: Gal 4:4-7, Mt 2:1-12")
    else:
        print(f"  [FAIL] Expected Gal 4:4-7 ({found_gal}) and Mt 2:1-12 ({found_mt})")
        ok = False

    # 2. Pascha 2026: Apr 12
    print("\n--- 2026-04-12 (Pascha) ---")
    readings = get_readings(2026, 4, 12)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}  [{r['book']} {r['pericope']}]")
    found_acts = any('Acts 1.1-8' in r.get('display', '') for r in readings)
    found_jn = any('John 1.1-17' in r.get('display', '') for r in readings)
    if found_acts and found_jn:
        print("  [PASS] Pascha readings found: Acts 1:1-8, John 1:1-17")
    else:
        print(f"  [FAIL] Expected Acts 1:1-8 ({found_acts}) and John 1:1-17 ({found_jn})")
        ok = False

    # 3. Great Friday 2026: Apr 10
    print("\n--- 2026-04-10 (Great Friday) ---")
    readings = get_readings(2026, 4, 10)
    passion_gospels = [r for r in readings if 'Passion Gospel' in r.get('source', '')]
    print(f"  Found {len(passion_gospels)} Passion Gospels")
    for r in passion_gospels:
        print(f"    {r['source']}: {r['display']}")
    if len(passion_gospels) == 12:
        print("  [PASS] 12 Passion Gospels found")
    else:
        print(f"  [FAIL] Expected 12 Passion Gospels, got {len(passion_gospels)}")
        ok = False

    # 4. Tone validation
    print("\n--- Tone Validation ---")
    # Thomas Sunday (pdist=7) should be tone 1
    tone = get_tone(2026, 4, 19)
    print(f"  2026-04-19 (Thomas Sunday, pdist=7): tone={tone}")
    if tone == 1:
        print("  [PASS]")
    else:
        print(f"  [FAIL] Expected tone 1, got {tone}")
        ok = False

    # pdist=0 (Pascha) should have tone 0
    tone = get_tone(2026, 4, 12)
    print(f"  2026-04-12 (Pascha): tone={tone}")
    if tone == 0:
        print("  [PASS]")
    else:
        print(f"  [FAIL] Expected tone 0, got {tone}")
        ok = False

    # 5. Year metadata
    print("\n--- Year 2026 Metadata ---")
    yr = _get_year(2026)
    # Pascha 2026 Julian: month 3, day 30 (Julian) -> JDN
    m, d = compute_julian_pascha(2026)
    print(f"  Julian Pascha: {m}/{d}")
    print(f"  Pascha JDN: {yr.pascha}")
    print(f"  Lucan Jump: {yr.lucan_jump}")
    print(f"  Elevation pdist: {yr.elevation}")
    print(f"  Nativity pdist: {yr.nativity}")
    print(f"  Theophany pdist: {yr.theophany}")
    print(f"  Forefathers pdist: {yr.forefathers}")
    print(f"  Extra Sundays: {yr.extra_sundays}")
    print(f"  Reserves: {yr.reserves}")

    # 6. A regular weekday
    print("\n--- 2026-06-01 (regular weekday, Mon after Pentecost) ---")
    readings = get_readings(2026, 6, 1)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}")

    # 7. Myrrhbearers Sunday
    print("\n--- 2026-04-26 (Myrrhbearers, pdist=14) ---")
    readings = get_readings(2026, 4, 26)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}")

    # 8. Palm Sunday
    print("\n--- 2026-04-05 (Palm Sunday) ---")
    readings = get_readings(2026, 4, 5)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}")

    # 9. Theophany Jan 19 (= Jan 6 Julian)
    print("\n--- 2026-01-19 (Theophany) ---")
    readings = get_readings(2026, 1, 19)
    for r in readings:
        print(f"  {r['source']} ({r['desc']}): {r['display']}")

    # 10. Different year: 2025 Pascha (Apr 20 Gregorian)
    print("\n--- 2025-04-20 (Pascha 2025) ---")
    readings = get_readings(2025, 4, 20)
    found_acts = any('Acts 1.1-8' in r.get('display', '') for r in readings)
    found_jn = any('John 1.1-17' in r.get('display', '') for r in readings)
    for r in readings:
        print(f"  {r['source']}: {r['display']}")
    if found_acts and found_jn:
        print("  [PASS] Pascha 2025 readings correct")
    else:
        print(f"  [FAIL] Pascha 2025: Acts ({found_acts}), John ({found_jn})")
        ok = False

    # 11. Verify Lucan Jump for 2025
    print("\n--- Year 2025 Metadata ---")
    yr25 = Year(2025)
    print(f"  Lucan Jump: {yr25.lucan_jump}")
    print(f"  Elevation pdist: {yr25.elevation}")
    elev_wd = weekday_from_pdist(yr25.elevation)
    print(f"  Elevation weekday: {elev_wd} (0=Sun)")

    print(f"\n=== Overall: {'PASS' if ok else 'FAIL'} ===")
    return ok


if __name__ == '__main__':
    _validate()
