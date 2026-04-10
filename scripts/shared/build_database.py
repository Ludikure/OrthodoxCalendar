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
    # pdist: {locale: (name, importance, type, description)}
    # description is optional (4th element)
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
        'sr': ("Лазарева субота", "bold", "feast", "Спомен на васкрсење праведног Лазара, пријатеља Христовог, у Витанији. Господ га је васкрсао четири дана после смрти, показујући своју власт над смрћу и најављујући своје сопствено Васкрсење."),
        'ru': ("Воскрешение праведного Лазаря (Лазарева суббота)", "bold", "feast", "Воспоминание воскрешения праведного Лазаря, друга Христова, в Вифании. Господь воскресил его через четыре дня после смерти, явив Свою власть над смертью и предвозвестив Своё собственное Воскресение."),
        'en': ("Lazarus Saturday", "bold", "feast", "Commemoration of the raising of Righteous Lazarus, the friend of Christ, in Bethany. The Lord raised him four days after his death, showing His power over death and foreshadowing His own Resurrection."),
    },
    -7: {
        'sr': ("Улазак Господа Исуса Христа у Јерусалим – Цвети", "great", "feast", "Народ је дочекао Господа са палмовим гранама и клицањем „Осана!" када је ушао у Јерусалим на магарету, испуњавајући пророштво Захарије. Овај празник се зове и Цвети или Врбица."),
        'ru': ("Вход Господень в Иерусалим (Вербное воскресенье)", "great", "feast", "Народ встречал Господа с пальмовыми ветвями и восклицаниями «Осанна!», когда Он вошёл в Иерусалим на молодом осле, исполняя пророчество Захарии. Этот праздник называется также Вербным воскресеньем."),
        'en': ("Entry of the Lord into Jerusalem — Palm Sunday", "great", "feast", "The people greeted the Lord with palm branches and cries of 'Hosanna!' as He entered Jerusalem on a young donkey, fulfilling the prophecy of Zechariah. This feast is also called Palm Sunday."),
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
        'sr': ("Велики четвртак", "bold", "feast", "Спомен на Тајну вечеру на којој је Господ установио Свету Евхаристију (Причешће) и умио ноге ученицима. Те ноћи је Јуда издао Христа пољупцем у Гетсиманском врту."),
        'ru': ("Великий четверг", "bold", "feast", "Воспоминание Тайной Вечери, на которой Господь установил Таинство Евхаристии (Причащения) и омыл ноги ученикам. В ту ночь Иуда предал Христа поцелуем в Гефсиманском саду."),
        'en': ("Great Thursday", "bold", "feast", "Commemoration of the Mystical Supper at which the Lord instituted the Holy Eucharist (Communion) and washed the feet of His disciples. That night Judas betrayed Christ with a kiss in the Garden of Gethsemane."),
    },
    -2: {
        'sr': ("Велики петак", "bold", "feast", "На данашњи дан је страдао Господ наш Исус Христос. Осуђен од Понтија Пилата, бичеван, понижен и распет на Крсту на Голготи. Скинут са Крста и положен у гроб Јосифа из Ариматеје. Најтужнији дан хришћанског календара."),
        'ru': ("Великая пятница", "bold", "feast", "В сей день пострадал Господь наш Иисус Христос. Осуждённый Понтием Пилатом, бичёванный, поруганный и распятый на Кресте на Голгофе. Снятый со Креста и положенный во гроб Иосифа Аримафейского. Самый скорбный день христианского календаря."),
        'en': ("Great Friday", "bold", "feast", "On this day our Lord Jesus Christ suffered. Condemned by Pontius Pilate, scourged, mocked and crucified on the Cross at Golgotha. Taken down from the Cross and laid in the tomb of Joseph of Arimathea. The most sorrowful day of the Christian calendar."),
    },
    -1: {
        'sr': ("Велика субота", "bold", "feast", "Дан тишине и ишчекивања. Тело Христово лежи у гробу. Душом је сишао у ад и ослободио праведнике од Адама до Јована Крститеља. Церква ишчекује славно Васкрсење."),
        'ru': ("Великая суббота", "bold", "feast", "День тишины и ожидания. Тело Христово лежит во гробе. Душою Он сошёл во ад и освободил праведников от Адама до Иоанна Крестителя. Церковь ожидает славного Воскресения."),
        'en': ("Great Saturday", "bold", "feast", "A day of silence and expectation. The Body of Christ lies in the tomb. In soul He descended into Hades and freed the righteous from Adam to John the Baptist. The Church awaits the glorious Resurrection."),
    },
    0: {
        'sr': ("Васкрсење Христово – Васкрс", "great", "feast", "Христос Воскресе! Празник над празницима и торжество над торжествима. Господ наш Исус Христос васкрсао је из мртвих трећег дана, победивши смрт и даровавши живот свету. Васкрс је темељ хришћанске вере."),
        'ru': ("Светлое Христово Воскресение — Пасха", "great", "feast", "Христос Воскресе! Праздник праздников и торжество торжеств. Господь наш Иисус Христос воскрес из мёртвых в третий день, победив смерть и даровав жизнь миру. Пасха — основание христианской веры."),
        'en': ("The Resurrection of Our Lord Jesus Christ — Pascha", "great", "feast", "Christ is Risen! The Feast of Feasts and the Triumph of Triumphs. Our Lord Jesus Christ rose from the dead on the third day, conquering death and granting life to the world. Pascha is the foundation of the Christian faith."),
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
        'sr': ("Томина недеља", "bold", "feast", "Прва недеља по Васкрсу. Апостол Тома, који није био присутан при првом јављању Васкрслог Христа, рекао је: „Ако не видим на рукама Његовим ране од клинова и не метнем руку своју у ребра Његова, нећу веровати." Осам дана касније Господ му се јавио и рече: „Блажени који не видеше а вероваше.""),
        'ru': ("Антипасха (Фомина неделя)", "bold", "feast", "Первое воскресенье по Пасхе. Апостол Фома, не присутствовавший при первом явлении Воскресшего Христа, сказал: «Если не увижу на руках Его ран от гвоздей и не вложу руки моей в рёбра Его, не поверю.» Через восемь дней Господь явился ему и сказал: «Блаженны не видевшие и уверовавшие.»"),
        'en': ("Thomas Sunday (Antipascha)", "bold", "feast", "The first Sunday after Pascha. Apostle Thomas, absent at the first appearance of the Risen Christ, said: 'Unless I see the nail marks in His hands and put my hand into His side, I will not believe.' Eight days later the Lord appeared and said: 'Blessed are those who have not seen and yet have believed.'"),
    },
    14: {
        'sr': ("Недеља мироносица", "bold", "feast", "Спомен на жене мироносице — Марију Магдалину, Марију Клеопину, Саломију, Јоану и друге — које су рано ујутру дошле на гроб Христов са мирисима и прве чуле радосну вест о Васкрсењу од анђела."),
        'ru': ("Неделя святых жен-мироносиц", "bold", "feast", "Память святых жен-мироносиц — Марии Магдалины, Марии Клеоповой, Саломии, Иоанны и других, — которые рано утром пришли ко гробу Христову с ароматами и первыми услышали радостную весть о Воскресении от ангела."),
        'en': ("Sunday of the Myrrh-Bearing Women", "bold", "feast", "Commemoration of the Myrrh-Bearing Women — Mary Magdalene, Mary wife of Cleopas, Salome, Joanna and others — who came early in the morning to the tomb of Christ with spices and were the first to hear the joyful news of the Resurrection from the angel."),
    },
    24: {
        'sr': ("Преполовљење Педесетнице", "bold", "feast", "Средина периода од Васкрса до Духова. Господ је на половини празника Сеница ушао у храм и учио народ, говорећи: „Ко је жедан нека дође к мени и пије.""),
        'ru': ("Преполовение Пятидесятницы", "bold", "feast", "Середина периода от Пасхи до Пятидесятницы. В середине праздника Кущей Господь вошёл в храм и учил народ, говоря: «Кто жаждет, иди ко Мне и пей.»"),
        'en': ("Mid-Pentecost", "bold", "feast", "The midpoint between Pascha and Pentecost. At the middle of the Feast of Tabernacles the Lord entered the Temple and taught the people, saying: 'If anyone thirsts, let him come to Me and drink.'"),
    },
    39: {
        'sr': ("Вазнесење Господње – Спасовдан", "great", "feast", "Четрдесет дана по Васкрсењу Господ се вазнео на небо са Маслинске горе пред очима својих ученика. Два анђела су рекла апостолима: „Овај Исус који се од вас узнесе на небо, тако ће доћи као што сте Га видели да иде на небо.""),
        'ru': ("Вознесение Господне", "great", "feast", "Через сорок дней после Воскресения Господь вознёсся на небо с горы Елеонской на глазах Своих учеников. Два ангела сказали апостолам: «Сей Иисус, вознёсшийся от вас на небо, придёт таким же образом, как вы видели Его восходящим на небо.»"),
        'en': ("The Ascension of Our Lord Jesus Christ", "great", "feast", "Forty days after the Resurrection, the Lord ascended into heaven from the Mount of Olives before the eyes of His disciples. Two angels said to the apostles: 'This same Jesus, who was taken from you into heaven, will come in like manner as you saw Him go into heaven.'"),
    },
    49: {
        'sr': ("Силазак Светог Духа на Апостоле – Педесетница – Тројице", "great", "feast", "Педесет дана по Васкрсу, на дан јеврејске Педесетнице, Свети Дух сишао је на апостоле у виду огњених језика. Испуњени Духом Светим, апостоли су почели да говоре разним језицима и да проповедају Јеванђеље свим народима. Овај дан се сматра рођенданом Цркве."),
        'ru': ("День Святой Троицы — Пятидесятница", "great", "feast", "Через пятьдесят дней после Воскресения, в день еврейской Пятидесятницы, Святой Дух сошёл на апостолов в виде огненных языков. Исполнившись Духа Святого, апостолы начали говорить на разных языках и проповедовать Евангелие всем народам. Этот день считается днём рождения Церкви."),
        'en': ("Pentecost — The Descent of the Holy Spirit", "great", "feast", "Fifty days after the Resurrection, on the day of the Jewish Pentecost, the Holy Spirit descended upon the apostles in the form of tongues of fire. Filled with the Holy Spirit, the apostles began to speak in various languages and preach the Gospel to all nations. This day is considered the birthday of the Church."),
    },
    50: {
        'sr': ("Духовски понедељак", "bold", "feast", "Дан Светог Духа. Други дан Духова, посвећен посебно Светом Духу — трећем Лицу Свете Тројице."),
        'ru': ("День Святого Духа", "bold", "feast", "День Святого Духа. Второй день Пятидесятницы, посвящённый особо Святому Духу — третьему Лицу Святой Троицы."),
        'en': ("Monday of the Holy Spirit", "bold", "feast", "The Day of the Holy Spirit. The second day of Pentecost, dedicated especially to the Holy Spirit — the Third Person of the Holy Trinity."),
    },
    56: {
        'sr': ("Недеља свих светих", "bold", "feast", "Прва недеља по Духовима. Црква прославља све светитеље — познате и непознате — који су од постанка света до данас угодили Богу својим животом и подвизима."),
        'ru': ("Неделя всех святых", "bold", "feast", "Первое воскресенье по Пятидесятнице. Церковь прославляет всех святых — известных и неизвестных, — которые от начала мира до наших дней угодили Богу своей жизнью и подвигами."),
        'en': ("Sunday of All Saints", "bold", "feast", "The first Sunday after Pentecost. The Church glorifies all the saints — known and unknown — who from the beginning of the world to the present day have pleased God by their lives and struggles."),
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
    # Julian date: {locale: (name, type, isSlava, description)}
    '09-08': {  # Greg 09-21: Nativity of Theotokos
        'sr': ("Рођење Пресвете Богородице – Мала Госпојина", "feast", True, "Рођење Пресвете Богородице од праведних родитеља Јоакима и Ане. После дугогодишње неплодности, Бог им је даровао кћер, која ће постати мајка Спаситеља света."),
        'ru': ("Рождество Пресвятой Богородицы", "feast", False, "Рождение Пресвятой Богородицы от праведных родителей Иоакима и Анны. После долгих лет бесплодия Бог даровал им дочь, которая станет Матерью Спасителя мира."),
        'en': ("The Nativity of Our Most Holy Lady the Theotokos", "feast", False, "The birth of the Most Holy Theotokos from the righteous parents Joachim and Anna. After many years of childlessness, God granted them a daughter who would become the Mother of the Savior of the world."),
    },
    '09-14': {  # Greg 09-27: Elevation of Cross
        'sr': ("Воздвижење часног Крста – Крстовдан", "feast", True, "Света царица Јелена (мајка цара Константина) пронашла је Часни Крст Христов у Јерусалиму 326. године. Патријарх Макарије воздигао је Крст пред народом, и народ је узвикивао „Господи, помилуј!""),
        'ru': ("Воздвижение Честного Креста Господня", "feast", False, "Святая царица Елена (мать императора Константина) обрела Честной Крест Христов в Иерусалиме в 326 году. Патриарх Макарий воздвиг Крест перед народом, и народ восклицал «Господи, помилуй!»"),
        'en': ("The Universal Elevation of the Precious and Life-Giving Cross", "feast", False, "Holy Empress Helen (mother of Emperor Constantine) discovered the True Cross of Christ in Jerusalem in 326. Patriarch Macarius elevated the Cross before the people, who cried out 'Lord, have mercy!'"),
    },
    '11-21': {  # Greg 12-04: Entry/Presentation of Theotokos
        'sr': ("Ваведење Пресвете Богородице", "feast", True, "Праведни Јоаким и Ана довели су трогодишњу Марију у Јерусалимски храм, испуњавајући свој завет Богу. Првосвештеник Захарија увео ју је у Светињу над Светињама, где је живела до своје дванаесте године."),
        'ru': ("Введение во храм Пресвятой Богородицы", "feast", False, "Праведные Иоаким и Анна привели трёхлетнюю Марию в Иерусалимский храм, исполняя свой обет Богу. Первосвященник Захария ввёл Её во Святая Святых, где Она жила до двенадцатилетнего возраста."),
        'en': ("The Entry of the Most Holy Theotokos into the Temple", "feast", False, "The righteous Joachim and Anna brought three-year-old Mary to the Jerusalem Temple, fulfilling their vow to God. The High Priest Zacharias led Her into the Holy of Holies, where She lived until the age of twelve."),
    },
    '12-25': {  # Greg 01-07: Nativity of Christ
        'sr': ("Рождество Христово – Божић", "feast", True, "Господ наш Исус Христос рођен је у Витлејему Јудејском од Пресвете Дјеве Марије. Пастири и мудраци са Истока дошли су да Му се поклоне. „Слава на висини Богу, и на земљи мир, међу људима добра воља!""),
        'ru': ("Рождество Христово", "feast", False, "Господь наш Иисус Христос родился в Вифлееме Иудейском от Пресвятой Девы Марии. Пастухи и волхвы с Востока пришли поклониться Ему. «Слава в вышних Богу, и на земле мир, в человеках благоволение!»"),
        'en': ("The Nativity of Our Lord Jesus Christ", "feast", False, "Our Lord Jesus Christ was born in Bethlehem of Judea of the Most Holy Virgin Mary. Shepherds and wise men from the East came to worship Him. 'Glory to God in the highest, and on earth peace, good will toward men!'"),
    },
    '01-06': {  # Greg 01-19: Theophany
        'sr': ("Богојављење", "feast", True, "Крштење Господа Исуса Христа у реци Јордану од Светог Јована Крститеља. При крштењу се Света Тројица јавила свету: Отац гласом с неба, Син у води, и Дух Свети у виду голуба."),
        'ru': ("Святое Богоявление — Крещение Господне", "feast", False, "Крещение Господа Иисуса Христа в реке Иордан от святого Иоанна Крестителя. При Крещении Святая Троица явилась миру: Отец гласом с небес, Сын в воде, и Дух Святой в виде голубя."),
        'en': ("The Baptism of Our Lord Jesus Christ — Theophany", "feast", False, "The Baptism of our Lord Jesus Christ in the River Jordan by Saint John the Baptist. At the Baptism the Holy Trinity was revealed to the world: the Father by a voice from heaven, the Son in the water, and the Holy Spirit in the form of a dove."),
    },
    '02-02': {  # Greg 02-15: Meeting of the Lord (Сретење)
        'sr': ("Сретење Господње", "feast", True, "Четрдесет дана по рођењу, Младенац Христос је донесен у Јерусалимски храм. Старац Симеон Га је примио у наручје и рекао: „Сад отпушташ слугу свога, Владико, по речи својој, с миром, јер видеше очи моје спасење Твоје.""),
        'ru': ("Сретение Господне", "feast", False, "На сороковой день по рождении Младенец Христос был принесён в Иерусалимский храм. Старец Симеон принял Его на руки и сказал: «Ныне отпущаеши раба Твоего, Владыко, по глаголу Твоему, с миром, яко видеста очи мои спасение Твое.»"),
        'en': ("The Meeting of Our Lord Jesus Christ in the Temple", "feast", False, "Forty days after His birth, the infant Christ was brought to the Jerusalem Temple. The Elder Simeon received Him in his arms and said: 'Lord, now lettest Thou Thy servant depart in peace, according to Thy word, for mine eyes have seen Thy salvation.'"),
    },
    '03-25': {  # Greg 04-07: Annunciation
        'sr': ("Благовести – Благовештење Пресвете Богородице", "feast", True, "Архангел Гаврило јавио се Пресветој Дјеви Марији у Назарету и благовестио јој да ће родити Сина Божјег. Марија је одговорила: „Ево слушкиње Господње, нека ми буде по речи твојој.""),
        'ru': ("Благовещение Пресвятой Богородицы", "feast", False, "Архангел Гавриил явился Пресвятой Деве Марии в Назарете и благовестил Ей, что Она родит Сына Божия. Мария ответила: «Се, раба Господня; да будет Мне по слову твоему.»"),
        'en': ("The Annunciation of Our Most Holy Lady the Theotokos", "feast", False, "The Archangel Gabriel appeared to the Most Holy Virgin Mary in Nazareth and announced that She would bear the Son of God. Mary answered: 'Behold the handmaid of the Lord; be it unto me according to thy word.'"),
    },
    '08-06': {  # Greg 08-19: Transfiguration
        'sr': ("Преображење Господње", "feast", True, "Господ се преобразио на гори Тавор пред ученицима Петром, Јаковом и Јованом. Лице Његово засијало је као сунце, а хаљине Му постадоше беле као светлост. Јавише се Мојсије и Илија и глас с неба рече: „Ово је Син Мој љубљени, Њега слушајте.""),
        'ru': ("Преображение Господне", "feast", False, "Господь преобразился на горе Фавор перед учениками Петром, Иаковом и Иоанном. Лицо Его просияло как солнце, а одежды Его стали белыми как свет. Явились Моисей и Илия, и голос с небес сказал: «Сей есть Сын Мой возлюбленный, Его слушайте.»"),
        'en': ("The Transfiguration of Our Lord Jesus Christ", "feast", False, "The Lord was transfigured on Mount Tabor before His disciples Peter, James and John. His face shone like the sun, and His garments became white as light. Moses and Elijah appeared, and a voice from heaven said: 'This is My beloved Son; listen to Him.'"),
    },
    '08-15': {  # Greg 08-28: Dormition
        'sr': ("Успеније Пресвете Богородице – Велика Госпојина", "feast", True, "Успење (смрт) Пресвете Богородице у Јерусалиму. Сви апостоли били су чудесно донесени на облацима да би присуствовали Њеном упокојењу. Трећег дана гроб Њен нађен је празан — Господ је узнео Своју Мајку у небеску славу."),
        'ru': ("Успение Пресвятой Богородицы", "feast", False, "Успение (кончина) Пресвятой Богородицы в Иерусалиме. Все апостолы были чудесно перенесены на облаках, чтобы присутствовать при Её погребении. На третий день гроб Её оказался пуст — Господь вознёс Свою Матерь в небесную славу."),
        'en': ("The Dormition of Our Most Holy Lady the Theotokos", "feast", False, "The Dormition (falling asleep) of the Most Holy Theotokos in Jerusalem. All the apostles were miraculously transported on clouds to be present at Her burial. On the third day Her tomb was found empty — the Lord had taken His Mother into heavenly glory."),
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
    entry_tuple = feast[locale]
    name, importance, ftype = entry_tuple[0], entry_tuple[1], entry_tuple[2]
    description = entry_tuple[3] if len(entry_tuple) > 3 else None
    result = {
        "name": name,
        "position": 0,
        "importance": importance,
        "type": ftype,
        "displayRole": "primary",
        "isSlava": False,
        "liturgicalContext": None,
        "moveable": True,
    }
    if description:
        result["description"] = description
    return result


def _build_feasts(saints_data: dict, key: str, pdist: int, locale: str, great_feast, julian_key: str) -> list:
    """Build the feasts list for a day: fixed great feast + moveable feast + fixed saints."""
    feasts = []

    # 1. Get fixed saints from scraped data (filtering out pure moveable feasts)
    fixed = _get_fixed_saints(saints_data, key)

    # 2. Check for algorithmic fixed great feast (always injected, never lost)
    fixed_great = FIXED_GREAT_FEASTS.get(julian_key)
    fixed_great_entry = None
    if fixed_great and locale in fixed_great:
        entry_tuple = fixed_great[locale]
        name, ftype, is_slava = entry_tuple[0], entry_tuple[1], entry_tuple[2]
        description = entry_tuple[3] if len(entry_tuple) > 3 else None
        fixed_great_entry = {
            "name": name,
            "position": 0,
            "importance": "great",
            "type": ftype,
            "displayRole": "primary",
            "isSlava": is_slava,
            "liturgicalContext": None,
        }
        if description:
            fixed_great_entry["description"] = description
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

    # Saint biographies
    saint_bios_data = load_json(os.path.join(proc_dir, 'saint_bios.json')).get('days', {})

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
        # Check saints data for feast importance (bold saints upgrade fasting in SPC)
        day_saints = saints_data.get(key, {}).get("saints", [])
        if great_feast:
            feast_rank = "great"
        elif any(s.get("importance") == "bold" for s in day_saints):
            feast_rank = "bold"
        else:
            feast_rank = None

        # Compute algorithmic fasting
        fasting_level = compute_fasting(current, pasch, feast_rank, locale)
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

            # Saint biographies (keyed by MM-DD, year-independent)
            "saintBios": saint_bios_data.get(key) or None,

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
