"""Which scraped commemorations belong to a day, in any year.

The saints and bio pools were scraped from a single year, POOL_YEAR, on the Old
Calendar, and are keyed by that year's Gregorian dates: the entry for a church
(Julian) month-day sits 13 days later. Reading the pool by the *Gregorian*
month-day of the year being built — what build_database.py used to do — is
right only in a common year. In a leap year February gains a day, so from
Gregorian February 29 to March 12 every day showed the previous church day's
saints and February 29 was blank; the New Calendar had the same fault on
February 16-28. A day is now read by its church date.

Two kinds of entry in the pools are not fixed-cycle data at all:

- February 29 exists only in a leap year. A common-year source lists its
  commemorations (St John Cassian and the Cassians sharing his day) with
  February 28, so in a leap year they are split back out onto their own day.
- Commemorations that move: memorial Saturdays, the Sundays before and after a
  feast, the leave-takings of the Paschal feasts, synaxes kept on "the Sunday
  nearest" a date. The sources printed them on the dates they fell on in
  POOL_YEAR, and the build repeated those dates in every year — right in 2026
  and wrong in most others. They are taken off their fixed day and placed by
  their rule. The Serbian source appends some of them to a saint's name
  ("Свети мученик Трифун Задушнице зимске"); there the saint stays and the label
  becomes an entry of its own.

Every rule was checked against the sources' own placements in other years:
orthocal.info 2024-2037 for the Sunday and Saturday windows around the great
feasts, holytrinityorthodox.com 2025-2035 for its entries, days.pravoslavie.ru
2024-2026 for the Russian ones. An entry whose rule no source pins down is
dropped rather than guessed.
"""
import re
from datetime import date, timedelta

POOL_YEAR = 2026
JULIAN_OFFSET = 13

SATURDAY, SUNDAY = 5, 6


def pool_key(church_key: str) -> str:
    """Pool key of the entry holding a church month-day's commemorations."""
    month, day = int(church_key[:2]), int(church_key[3:])
    if (month, day) == (2, 29):
        day = 28
    return (date(POOL_YEAR, month, day) + timedelta(days=JULIAN_OFFSET)).strftime("%m-%d")


# ── February 29 ──

LEAP_DAY = re.compile(r"Касијан|Кассиан|Cassian")


def leap_split(church_key: str, year: int):
    """Name predicate for February 28/29, or None on every other day.

    `year` is the church year of the day; the Julian and Revised Julian calendars
    have the same leap years as the Gregorian one from 1901 to 2099."""
    if church_key == "02-29":
        return lambda name: bool(LEAP_DAY.search(name))
    if church_key == "02-28" and year % 4 == 0:
        return lambda name: not LEAP_DAY.search(name)
    return None


# ── Scraper leftovers ──

_MONTH_PREFIX = re.compile(r"^(ЈАНУАР|ФЕБРУАР|МАРТ|АПРИЛ|МАЈ|ЈУН|ЈУЛ|АВГУСТ|СЕПТЕМБАР|"
                           r"ОКТОБАР|НОВЕМБАР|ДЕЦЕМБАР)\s*[–-]\s*")


def is_note(name: str) -> bool:
    """A rubric the English source prints among the saints ("* If the service …")."""
    return name.lstrip().startswith("*")


# ── Moving commemorations ──
#
# A rule is ("pascha", n) — n days from Pascha — or ("between", weekday, first,
# last): that weekday (0 = Monday … 6 = Sunday) falling between two church
# month-days, inclusive; a window may cross the new year ("12-30".."01-05").
# Church dates are Julian on the Old Calendar and Gregorian on the Revised one,
# so a rule places the same commemoration on both. A window with no such weekday
# in it means no commemoration that year.

def between(first: str, last: str, weekday: int = SUNDAY) -> tuple:
    return ("between", weekday, first, last)


# Labels the Serbian source appends to a saint's name.
LABELS = [
    ("sr", r"\s+Задушнице зимске$", "Задушнице зимске", ("pascha", -57)),
    ("sr", r"\s+Задушнице летње$", "Задушнице летње", ("pascha", 48)),
    ("sr", r"\s+Задушнице михољске$", "Задушнице михољске", between("09-22", "09-28", SATURDAY)),
    ("sr", r"\s+Задушнице јесење$", "Задушнице јесење", between("10-19", "10-25", SATURDAY)),
    ("sr", r"\s+–\s+Детињци$", "Детињци", between("12-04", "12-10")),
    ("sr", r"\s+–\s+Материце$", "Материце", between("12-11", "12-17")),
    ("sr", r"\s+–\s+Оци$", "Оци", between("12-18", "12-24")),
    ("sr", r"\s+–\s+Теодорова субота$", "Теодорова субота", ("pascha", -43)),
]

# Whole entries: (locale, pool key, name prefix, rule). A rule of None drops the
# entry, because the build already injects that feast by pascha distance.
MOVED = [
    ("ru", "02-08", "Собор новомучеников и исповедников Церкви Русской", between("01-22", "01-28")),
    ("ru", "02-21", "Собор всех преподобных отцов, в подвиге просиявших", ("pascha", -50)),
    ("ru", "02-28", "Вмч. Феодора Тирона", ("pascha", -43)),
    ("ru", "03-08", "Свт. Григория Паламы", ("pascha", -35)),
    ("ru", "03-08", "Собор всех преподобных отцов Киево-Печерских", ("pascha", -35)),
    ("ru", "04-17", "Иконы Божией Матери Живоносный Источник", ("pascha", 5)),
    ("ru", "05-09", "Собор новомучеников, в Бутове пострадавших", ("pascha", 27)),
    ("ru", "05-13", "Отдание праздника Преполовения Пятидесятницы", ("pascha", 31)),
    ("ru", "05-20", "Отдание праздника Пасхи", ("pascha", 38)),
    ("ru", "05-29", "Отдание праздника Вознесения Господня", ("pascha", 47)),
    ("ru", "06-06", "Отдание праздника Пятидесятницы", ("pascha", 55)),
    ("ru", "06-14", "Всех преподобных и богоносных отцов, во Святой Горе Афонской", ("pascha", 63)),
    ("ru", "07-26", "Память святых отцов шести Вселенских Соборов", between("07-13", "07-19")),
    ("ru", "10-25", "Память святых отцов VII Вселенского Собора", between("10-11", "10-17")),
    ("ru", "06-21", "Собор Новгородских святых", ("pascha", 70)),
    ("ru", "06-21", "Собор Белорусских святых", ("pascha", 70)),
    ("ru", "06-21", "Собор Псковских святых", ("pascha", 70)),
    ("ru", "06-21", "Собор святых Санкт-Петербургской митрополии", ("pascha", 70)),
    ("ru", "06-21", "Собор святых Удмуртской земли", ("pascha", 70)),
    ("ru", "06-21", "Собор Волгоградских святых", ("pascha", 70)),
    ("ru", "06-28", "Собор преподобных отцов Псково-Печерских", ("pascha", 77)),
    ("ru", "09-06", "Собор Московских святых", between("08-19", "08-25")),
    ("ru", "06-07", "Собор мучеников Холмских и Подляшских", between("05-19", "05-25")),
    ("ru", "07-19", "Собор Тверских святых", between("06-30", "07-06")),
    ("ru", "08-09", "Собор Смоленских святых", between("07-21", "07-27")),
    ("ru", "10-11", "Собор святых Кубанской митрополии", between("09-28", "10-04")),
    ("ru", "02-15", "Собор святых Пермской митрополии", between("01-29", "02-04")),
    ("ru", "08-23", "Собор Валаамских святых", between("08-07", "08-13")),
    ("ru", "08-30", "Собор Кузбасских святых", between("08-11", "08-17")),
    ("ru", "09-13", "Собор Саратовских святых", between("08-28", "09-03")),
    ("ru", "09-13", "Собор святых Нижегородской митрополии", between("08-26", "09-01")),
    ("ru", "09-20", "Собор новомучеников и исповедников Казахстанских", between("09-03", "09-09")),
    ("ru", "09-27", "Собор Алтайских святых", between("09-07", "09-13")),
    ("ru", "10-11", "Собор святых, в земле Испанской и Португальской", between("09-23", "09-29")),
    ("ru", "11-22", "Собор Аланских святых", between("11-07", "11-13")),
    # These move with a Sunday, but no source pins their rule: holytrinityorthodox.com
    # puts Chelyabinsk anywhere from Julian Sep 24 to Oct 3 (no seven-day window
    # holds it); Lithuania is in no other source; Germany and Karelia have only two
    # observed years. Better absent than on the wrong Sunday.
    ("ru", "10-11", "Собор святых Челябинской митрополии", None),
    ("ru", "07-26", "Собор всех святых, в земле Литовской просиявших", None),
    ("ru", "10-04", "Собор святых, в земле Германской просиявших", None),
    ("ru", "11-01", "Собор новомучеников и исповедников земли Карельской", None),

    ("en", "01-04", "Sunday before the Nativity", between("12-18", "12-24")),
    ("en", "01-11", "Sunday after the Nativity", between("12-26", "12-31")),
    ("en", "01-18", "Sunday before the Baptism", between("01-01", "01-05")),
    ("en", "01-25", "Sunday after the Baptism", between("01-07", "01-13")),
    ("en", "02-08", "New Martyrs and Confessors of Russian Church", between("01-22", "01-28")),
    ("en", "02-21", "All of the venerable fathers, lit up with great deeds", ("pascha", -50)),
    ("en", "02-28", "Great Martyr Theodore Tyro", ("pascha", -43)),
    ("en", "03-07", "Parents’ Saturday", ("pascha", -36)),
    ("en", "03-14", "Parents’ Saturday", ("pascha", -29)),
    ("en", "03-21", "Parents’ Saturday", ("pascha", -22)),
    ("en", "03-08", "St. Gregory Palamas the Archbishop of Thessalonica", ("pascha", -35)),
    ("en", "03-08", "Synaxis of all Venerable Fathers of the Kiev Caves", ("pascha", -35)),
    ("en", "04-04", "Feast of the Georgian Language", ("pascha", -8)),
    ("en", "04-17", "Commemoration of the renewal (sanctification) of the Holy Theotokos temple", ("pascha", 5)),
    ("en", "04-26", "Sts. Myrrh-Bearing Women, righteous Joseph of Arimathea", None),
    ("en", "04-26", "All Saints of Thessalonica", ("pascha", 14)),
    ("en", "04-26", "New Hieromartyr Seraphim, archbishop of Phanarion", ("pascha", 14)),
    ("en", "04-26", "New Monk-martyr Elias (Ardunis)", ("pascha", 14)),
    ("en", "04-26", "New Martyr Demetrius of Peloponnesus", ("pascha", 14)),
    ("en", "05-03", "New Martyr Theodore of Bizantium", ("pascha", 21)),
    ("en", "05-03", "All Saints of Euboea", ("pascha", 21)),
    ("en", "05-09", "Synaxis of New Martyrs of Butovo", ("pascha", 27)),
    ("en", "05-21", "Holy Georgian Martyrs of Persia", ("pascha", 39)),
    ("en", "05-31", "Holy Fathers and Mothers of Atchara", ("pascha", 49)),
    ("en", "06-14", "All venerable and holy Fathers of the Holy Mount Athos", ("pascha", 63)),
    ("en", "06-21", "Synaxis of Saints of Belorussia", ("pascha", 70)),
    ("en", "07-26", "Commemoration of the Holy Fathers of the First Six Councils", between("07-13", "07-19")),
    ("en", "09-20", "Sunday before the Universal Elevation", between("09-07", "09-13")),
    ("en", "10-04", "Sunday after the Universal Elevation", between("09-15", "09-21")),
    ("en", "10-25", "Commemoration of the Holy Fathers of the Seventh Ecumenical Council", between("10-11", "10-17")),
    ("en", "12-27", "Week of Holy Forefathers", between("12-11", "12-17")),
    ("en", "01-03", "Saturday the Nativity of our Lord", between("12-18", "12-24", SATURDAY)),
    ("en", "01-10", "Saturday after the Nativity", between("12-26", "12-31", SATURDAY)),
    ("en", "01-17", "Saturday before the Theophany", between("12-30", "01-05", SATURDAY)),
    ("en", "01-24", "Saturday after the Baptism", between("01-07", "01-13", SATURDAY)),
    ("en", "09-26", "Saturday before the Universal Elevation", between("09-07", "09-13", SATURDAY)),
    ("en", "10-03", "Saturday after the Universal Elevation", between("09-15", "09-21", SATURDAY)),
    ("en", "11-07", "Demetrius (Parental) Saturday", between("10-19", "10-25", SATURDAY)),
    ("en", "04-26", "Sts. Mary and Martha, sisters of St. Lazarus", ("pascha", 14)),
    ("en", "06-14", "All venerable and holy Fathers of Bulgaria", ("pascha", 63)),
    ("en", "06-21", "Celebration in Vologda to the venerable fathers of Vologda", ("pascha", 70)),
    ("en", "06-21", "Synaxis of Novgorod Hierarchs", ("pascha", 70)),
    ("en", "06-21", "Synaxis of Saints of Pskov", ("pascha", 70)),
    ("en", "06-21", "Synaxis of Saints of St. Petersburg", ("pascha", 70)),
    ("en", "06-21", "Synaxis of Saints of the Lands of Udmurtia", ("pascha", 70)),
    ("en", "06-21", "Synaxis of Saints of Volgograd", ("pascha", 70)),
    ("en", "06-28", "Synaxis of All Saints of Pskov-Pechers", ("pascha", 77)),
    ("en", "09-06", "Synaxis of all saints of Moscow", between("08-19", "08-25")),
    ("en", "09-20", "Synaxis of All Saints of Altai", between("09-07", "09-13")),
    ("en", "06-07", "Synaxis of Hieromartyrs of Kholmsk and Podliash", between("05-19", "05-25")),
    ("en", "07-19", "Synaxis of saints of Tver", between("06-30", "07-06")),
    ("en", "08-09", "Synaxis of saints of Smolensk", between("07-21", "07-27")),
    ("en", "10-11", "Synaxis of Saints of Kuban Metropolia", between("09-28", "10-04")),
    ("en", "02-15", "Synaxis of All Saints of Perm Metropolia", between("01-29", "02-04")),
    ("en", "08-23", "Synaxis of saints of Valaam Monastery", between("08-07", "08-13")),
    ("en", "08-30", "Synaxis of saints of Kemerovo", between("08-11", "08-17")),
    ("en", "09-13", "Synaxis of All Saints of Saratov", between("08-28", "09-03")),
    ("en", "09-13", "Synaxis of all saints of Nizhny Novgorod", between("08-26", "09-01")),
    ("en", "09-20", "Synaxis of New Martyrs and Confessors of Kazakhstan", between("09-03", "09-09")),
    ("en", "10-11", "Synaxis of All Saints Who Shone Forth in the Spanish and Portuguese", between("09-23", "09-29")),
    ("en", "11-22", "Synaxis of Saints of Alania", between("11-07", "11-13")),
    ("en", "10-11", "Synaxis of Saints of Chelyabinsk Metropolia", None),   # no consistent Sunday
]


def clean_name(locale: str, name: str) -> str:
    """Strip the month header and moving labels the Serbian source glues onto names."""
    if locale != "sr":
        return name
    name = _MONTH_PREFIX.sub("", name)
    for _, suffix, _, _ in LABELS:
        name = re.sub(suffix, "", name)
    return name.strip()


def is_relocated(locale: str, key: str, name: str) -> bool:
    """True for a pool entry that does not belong on its fixed day."""
    return any(loc == locale and k == key and name.startswith(prefix)
               for loc, k, prefix, _ in MOVED)


def relocations(locale: str, saints_pool: dict) -> list:
    """(rule, entry) for every moving commemoration of a locale, read from its pool.

    Fails loudly when an entry is not where the table says: a re-scraped pool
    would otherwise silently put the commemoration back on its fixed date."""
    out = []
    for loc, key, prefix, rule in MOVED:
        if loc != locale:
            continue
        found = [s for s in saints_pool.get(key, {}).get("saints", [])
                 if s.get("name", "").startswith(prefix)]
        if not found:
            raise SystemExit(f"fixed_cycle: {locale} {key}: no pool entry starting {prefix!r}")
        if rule is not None:
            out.append((rule, dict(found[0])))
    for loc, suffix, label, rule in LABELS:
        if loc != locale:
            continue
        if not any(re.search(suffix, s.get("name", ""))
                   for day in saints_pool.values() for s in day.get("saints", [])):
            raise SystemExit(f"fixed_cycle: {locale}: no pool entry carries the label {label!r}")
        # "feast", like the build's other moveable days (Лазарева субота, Велика
        # субота): the apps print a type they do not know as the raw word, so a
        # new type would have put "commemoration" above Задушнице in Serbian.
        out.append((rule, {"name": label, "importance": "normal", "type": "feast",
                           "isSlava": False, "liturgicalContext": None}))
    return out


def falls_on(rule: tuple, church_key: str, weekday: int, pdist: int) -> bool:
    if rule[0] == "pascha":
        return pdist == rule[1]
    _, wday, first, last = rule
    inside = (first <= church_key <= last if first <= last
              else church_key >= first or church_key <= last)
    return weekday == wday and inside


def on_day(relocated: list, church_key: str, weekday: int, pdist: int) -> list:
    """The moving commemorations that fall on a day, as fresh entries."""
    return [dict(entry, moveable=True) for rule, entry in relocated
            if falls_on(rule, church_key, weekday, pdist)]
