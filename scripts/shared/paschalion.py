#!/usr/bin/env python3
"""
Paschalion — Orthodox Easter (Pascha) computation and all movable feast dates.

Based on the Meeus algorithm for Julian Easter, then converts to Gregorian.
Computes all movable feasts, fasting periods, and liturgical seasons.

Usage:
    from paschalion import Paschalion
    p = Paschalion(2026)
    print(p.pascha)              # date(2026, 4, 12)
    print(p.palm_sunday)         # date(2026, 4, 5)
    print(p.great_lent_start)    # date(2026, 2, 23)
    print(p.movable_feasts)      # dict of all named dates
    print(p.is_in_fasting_period(date(2026, 3, 15)))  # ("great_lent", True)
"""

from datetime import date, timedelta
from typing import Optional

JULIAN_OFFSET = 13  # for 1900-2099


class Paschalion:
    """Compute all movable Orthodox feast dates for a given year."""

    def __init__(self, year: int):
        self.year = year
        self._compute_pascha()
        self._compute_movable_feasts()
        self._compute_fasting_periods()

    # ─── Pascha (Easter) ───

    def _compute_pascha(self):
        """Meeus algorithm for Julian Easter, converted to Gregorian."""
        y = self.year
        a = y % 19
        b = y % 4
        c = y % 7
        d = (19 * a + 15) % 30
        e = (2 * b + 4 * c + 6 * d + 6) % 7

        if d + e < 10:
            julian_month = 3
            julian_day = 22 + d + e
        else:
            julian_month = 4
            julian_day = d + e - 9

        # Convert Julian to Gregorian
        greg_day = julian_day + JULIAN_OFFSET
        greg_month = julian_month
        # Handle month overflow
        days_in_month = {3: 31, 4: 30}
        if greg_month in days_in_month and greg_day > days_in_month[greg_month]:
            greg_day -= days_in_month[greg_month]
            greg_month += 1

        self.pascha = date(y, greg_month, greg_day)

    # ─── Movable Feasts ───

    def _compute_movable_feasts(self):
        """Compute all movable feast dates relative to Pascha."""
        p = self.pascha
        d = timedelta

        # Pre-Lenten Sundays
        self.publican_pharisee = p - d(days=70)     # 10th Sunday before Pascha
        self.prodigal_son = p - d(days=63)           # 9th Sunday before Pascha
        self.meatfare_sunday = p - d(days=56)        # Мясопустная / Месопусна
        self.cheesefare_sunday = p - d(days=49)      # Сыропустная / Сиропусна

        # Great Lent
        self.clean_monday = p - d(days=48)           # Чисти Понедељак
        self.great_lent_start = self.clean_monday
        self.cross_veneration = p - d(days=28)       # 3rd Sunday of Lent

        # Holy Week approach
        self.lazarus_saturday = p - d(days=8)
        self.palm_sunday = p - d(days=7)

        # Holy Week
        self.great_monday = p - d(days=6)
        self.great_tuesday = p - d(days=5)
        self.great_wednesday = p - d(days=4)
        self.great_thursday = p - d(days=3)
        self.great_friday = p - d(days=2)
        self.great_saturday = p - d(days=1)

        # Pascha and after
        self.bright_monday = p + d(days=1)
        self.bright_saturday = p + d(days=6)
        self.thomas_sunday = p + d(days=7)
        self.myrrhbearers = p + d(days=14)
        self.mid_pentecost = p + d(days=24)
        self.ascension = p + d(days=39)
        self.pentecost = p + d(days=49)
        self.holy_spirit_monday = p + d(days=50)
        self.all_saints = p + d(days=56)

        # Apostles' Fast start (Monday after All Saints)
        self.apostles_fast_start = p + d(days=57)

        # Build lookup dict
        self.movable_feasts = {
            -70: ("publican_pharisee", "Sunday of the Publican and the Pharisee"),
            -63: ("prodigal_son", "Sunday of the Prodigal Son"),
            -56: ("meatfare_sunday", "Meatfare Sunday"),
            -49: ("cheesefare_sunday", "Cheesefare Sunday"),
            -48: ("clean_monday", "Clean Monday"),
            -28: ("cross_veneration", "Cross Veneration Sunday"),
            -8:  ("lazarus_saturday", "Lazarus Saturday"),
            -7:  ("palm_sunday", "Palm Sunday"),
            -6:  ("great_monday", "Great Monday"),
            -5:  ("great_tuesday", "Great Tuesday"),
            -4:  ("great_wednesday", "Great Wednesday"),
            -3:  ("great_thursday", "Great Thursday"),
            -2:  ("great_friday", "Great Friday"),
            -1:  ("great_saturday", "Great Saturday"),
             0:  ("pascha", "Pascha"),
             1:  ("bright_monday", "Bright Monday"),
             2:  ("bright_tuesday", "Bright Tuesday"),
             3:  ("bright_wednesday", "Bright Wednesday"),
             4:  ("bright_thursday", "Bright Thursday"),
             5:  ("bright_friday", "Bright Friday"),
             6:  ("bright_saturday", "Bright Saturday"),
             7:  ("thomas_sunday", "Thomas Sunday"),
            14:  ("myrrhbearers", "Sunday of the Myrrhbearing Women"),
            24:  ("mid_pentecost", "Mid-Pentecost"),
            39:  ("ascension", "Ascension"),
            49:  ("pentecost", "Pentecost"),
            50:  ("holy_spirit_monday", "Monday of the Holy Spirit"),
            56:  ("all_saints", "All Saints"),
            57:  ("apostles_fast_start", "Start of Apostles' Fast"),
        }

    # ─── Fasting Periods ───

    def _compute_fasting_periods(self):
        """Compute start/end dates for all fasting periods."""
        y = self.year
        d = timedelta

        # Great Lent: Clean Monday to Great Saturday (48 days before Pascha to day before)
        self.great_lent = (self.clean_monday, self.great_saturday)

        # Bright Week: Pascha to Bright Saturday (fast-free)
        self.bright_week = (self.pascha, self.bright_saturday)

        # Week after Pentecost (Trinity Week, fast-free)
        self.trinity_week = (self.pentecost, self.pentecost + d(days=6))

        # Apostles' Fast: Monday after All Saints to June 28 Julian (July 11 Gregorian)
        self.apostles_fast = (self.apostles_fast_start, date(y, 7, 11))

        # Dormition Fast: Aug 1-14 Julian (Aug 14-27 Gregorian) — fixed
        self.dormition_fast = (date(y, 8, 14), date(y, 8, 27))

        # Nativity Fast: Nov 15 - Dec 24 Julian (Nov 28 - Jan 6 Gregorian) — fixed
        self.nativity_fast = (date(y, 11, 28), date(y + 1, 1, 6))
        self.nativity_fast_period1 = (date(y, 11, 28), date(y + 1, 1, 1))  # Nov 28 - Jan 1 (less strict)
        self.nativity_fast_period2 = (date(y + 1, 1, 2), date(y + 1, 1, 6))  # Jan 2-6 (stricter)

        # Svyatki (Nativity to Eve of Theophany, fast-free)
        # Dec 25 Julian - Jan 4 Julian = Jan 7 - Jan 17 Gregorian
        self.svyatki = (date(y, 1, 7), date(y, 1, 17))

        # Publican & Pharisee week (fast-free, no Wed/Fri fasting)
        self.publican_pharisee_week = (self.publican_pharisee, self.publican_pharisee + d(days=6))

        # Maslenitsa / Cheese Week (no meat, but dairy/eggs ok — not full fast-free)
        self.cheese_week = (self.cheesefare_sunday - d(days=6), self.cheesefare_sunday)

    # ─── Period Queries ───

    def pascha_distance(self, greg_date: date) -> int:
        """Days from Pascha (negative = before, positive = after)."""
        return (greg_date - self.pascha).days

    def get_fasting_period(self, greg_date: date) -> Optional[str]:
        """Return which fasting period a date falls in, or None."""
        if self.great_lent[0] <= greg_date <= self.great_lent[1]:
            return "great_lent"
        if self.apostles_fast[0] <= greg_date <= self.apostles_fast[1]:
            return "apostles_fast"
        if self.dormition_fast[0] <= greg_date <= self.dormition_fast[1]:
            return "dormition_fast"
        # Nativity fast spans year boundary
        if greg_date >= self.nativity_fast[0] or greg_date <= date(self.year, 1, 6):
            # Check if we're in the nativity fast
            nf_start = date(self.year, 11, 28)
            nf_end = date(self.year + 1, 1, 6)
            if nf_start <= greg_date <= nf_end:
                return "nativity_fast"
            # Check previous year's nativity fast (Jan 1-6 of current year)
            if date(self.year, 1, 1) <= greg_date <= date(self.year, 1, 6):
                return "nativity_fast"
        return None

    def is_fast_free_week(self, greg_date: date) -> bool:
        """Check if date falls in a fast-free week (no Wed/Fri fasting)."""
        # Bright Week
        if self.bright_week[0] <= greg_date <= self.bright_week[1]:
            return True
        # Trinity Week (week after Pentecost)
        if self.trinity_week[0] <= greg_date <= self.trinity_week[1]:
            return True
        # Svyatki (after Nativity)
        if self.svyatki[0] <= greg_date <= self.svyatki[1]:
            return True
        # Publican & Pharisee week
        if self.publican_pharisee_week[0] <= greg_date <= self.publican_pharisee_week[1]:
            return True
        return False

    def is_cheese_week(self, greg_date: date) -> bool:
        """Check if date falls in Cheese Week (Maslenitsa) — no meat, dairy ok."""
        return self.cheese_week[0] <= greg_date <= self.cheese_week[1]

    def is_holy_week(self, greg_date: date) -> bool:
        """Check if date is in Holy Week (Great Monday through Great Saturday)."""
        return self.great_monday <= greg_date <= self.great_saturday

    def get_nativity_fast_sub_period(self, greg_date: date) -> Optional[int]:
        """Return 1 or 2 for which sub-period of Nativity Fast, or None."""
        if self.nativity_fast_period1[0] <= greg_date <= self.nativity_fast_period1[1]:
            return 1
        if self.nativity_fast_period2[0] <= greg_date <= self.nativity_fast_period2[1]:
            return 2
        # Check previous year's period 2 (Jan 2-6)
        if date(self.year, 1, 2) <= greg_date <= date(self.year, 1, 6):
            return 2
        return None

    # ─── Fixed Great Feasts ───

    @staticmethod
    def great_feasts_julian() -> dict:
        """12 Great Feasts by Julian month-day (fixed)."""
        return {
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

    def great_feasts_gregorian(self) -> dict:
        """All 12 Great Feasts with Gregorian dates for this year."""
        feasts = {}
        # Fixed (Julian → Gregorian)
        for jkey, feast_id in self.great_feasts_julian().items():
            jm, jd = int(jkey[:2]), int(jkey[3:])
            gd = jd + JULIAN_OFFSET
            gm = jm
            import calendar
            dim = calendar.monthrange(self.year, gm)[1]
            if gd > dim:
                gd -= dim
                gm += 1
                if gm > 12:
                    gm = 1
            feasts[feast_id] = date(self.year, gm, gd)

        # Movable
        feasts["entry-into-jerusalem"] = self.palm_sunday
        feasts["ascension"] = self.ascension
        feasts["pentecost"] = self.pentecost

        return feasts

    def is_great_feast(self, greg_date: date) -> Optional[str]:
        """Return canonical feast ID if date is a Great Feast, else None."""
        for feast_id, feast_date in self.great_feasts_gregorian().items():
            if feast_date == greg_date:
                return feast_id
        if greg_date == self.pascha:
            return "pascha"
        return None


def validate_pascha():
    """Validate Pascha dates against known values."""
    known = {
        2024: date(2024, 5, 5),
        2025: date(2025, 4, 20),
        2026: date(2026, 4, 12),
        2027: date(2027, 5, 2),
        2028: date(2028, 4, 16),
        2029: date(2029, 4, 8),
        2030: date(2030, 4, 28),
    }
    for year, expected in known.items():
        p = Paschalion(year)
        assert p.pascha == expected, f"{year}: expected {expected}, got {p.pascha}"
    print(f"Pascha validation passed for {len(known)} years.")


if __name__ == "__main__":
    validate_pascha()

    p = Paschalion(2026)
    print(f"\n=== Paschalion {p.year} ===")
    print(f"Pascha: {p.pascha}")
    print(f"Palm Sunday: {p.palm_sunday}")
    print(f"Great Lent: {p.great_lent_start} – {p.great_saturday}")
    print(f"Ascension: {p.ascension}")
    print(f"Pentecost: {p.pentecost}")
    print(f"Apostles' Fast: {p.apostles_fast_start} – {p.apostles_fast[1]}")
    print(f"Dormition Fast: {p.dormition_fast[0]} – {p.dormition_fast[1]}")
    print(f"Nativity Fast: {p.nativity_fast[0]} – {p.nativity_fast[1]}")
    print(f"\nGreat Feasts (Gregorian):")
    for fid, fdate in sorted(p.great_feasts_gregorian().items(), key=lambda x: x[1]):
        print(f"  {fdate}: {fid}")
