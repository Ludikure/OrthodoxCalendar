#!/usr/bin/env python3
"""Reference implementation of the app's saint-bio matcher, run over a year of data.

The iOS BioMatcher.swift (and the Android port) implement exactly these rules;
change them here first, check the numbers, then port. For each locale the
script reports how many fixed feasts get a bio with the previous matcher
("old", the pre-1.4.4 keyword/contains heuristic) and with the current rules
("new"), lists every feast whose assignment differs, and lists days where a
feast stays unmatched although unclaimed bios remain.

Usage: python3 scripts/shared/simulate_bio_matching.py [sr|ru|en|en_nc ...] [--year=2026]
"""
import collections, json, os, re, sys

OLD_COMMON = {"свети","света","светог","светих","светом","преподобни","преподобна","преподобног","мученик","мученица","мученици","свештеномученик","великомученик","святой","святая","святых","святителя","преподобный","преподобная","saint","holy","venerable","martyr","blessed","righteous"}

def old_words(name): return [w for w in name.lower().split(' ') if len(w) > 3 and w not in OLD_COMMON]
def old_assign(feasts, bios):
    """Port of DayDetailView.findBio: returns {feast_index: bio_index}."""
    out = {}
    if not bios: return out
    if len(bios) == 1:
        for i, f in enumerate(feasts):
            if not f.get('moveable'): out[i] = 0; break
        return out
    for index, feast in enumerate(feasts):
        if feast.get('moveable'): continue
        used = set()
        for i in range(index):
            f = feasts[i]
            if f.get('moveable'): continue
            words = old_words(f['name'])
            for bi, bio in enumerate(bios):
                if bi in used: continue
                bl = bio['title'].lower()
                if any(w in bl for w in words): used.add(bi); break
        words = old_words(feast['name'])
        for bi, bio in enumerate(bios):
            if bi in used: continue
            if any(w in bio['title'].lower() for w in words): out[index] = bi; break
    return out

# ---- new algorithm ----
GENERIC = {
 'sr': """свети света светог светих светом свете светога свето светитељ светитеља преподобни преподобна преподобног преподобне преподобних преподобномученик преподобномученица преподобномученици мученик мученица мученици мученика мученице мученицима великомученик великомученица свештеномученик свештеномученика свештеномученици новомученик новомученици новомученика исповедник исповедници исповедника епископ епископа архиепископ архиепископа митрополит митрополита патријарх патријарха апостол апостола апостоли апостолa пророк пророка чудотворац чудотворца блажени блажена праведни праведна кнез кнеза краљ краља цар цара царица царице презвитер презвитера ђакон ђакона игуман игумана игуманија монах монаха монахиња пустињак столпник јуродиви нови нова велики велика други друга трећи спомен пренос преноса моштију мошти сабор обретење икона иконе пресвете богородице богородица господа господње господњег христа христов христових ради њима њим три два шест седам десет пет четири седамдесет седамдесеторице оци отаца отац мати мајка дете деца деце свих остали остале других другим који које који цариградски печерски српски римски јерусалимски антиохијски кипарски солунски александријски грузијски московски новгородски синајски атонски светогорски египатски палестински хиландарски студенички ученик ученика ученици брат брата сестра сестре син сина кћи вериге часне часних архимандрит архимандрита схимник схимонах старац старца подвижник подвижника анахорет епископи девица девице девојака девојке жена људи војник војника војници св ii iii иже успеније успења рођење зачеће часне часних ризе главе руке""".split(),
 'ru': """святой святая святых святителя свт свтт сщмч сщмчч прп прпп прмч прмчч прмц прмцц мч мчч мц мцц исп блгв блж прав прор ап апп вмч вмц равноап сщисп прписп новомч новомчч пресвитера пресвитеров епископа епископов архиепископа митрополита патриарха игумена игумении иеромонаха иеродиакона диакона архимандрита архидиакона священника монаха монахини инока послушника мощей мощи обретение перенесение собор попразднство предпразднство отдание память святых преподобных мучеников мучениц новомучеников исповедников иже ним ними его иных других прочих всех день дня икона иконы божией матери пресвятой богородицы господня господа христа ради чудотворца чудотворцев затворника юродивого князя княгини царя царицы кн блгвв печерского печерских дальних ближних пещерах киевского московского новгородского константинопольского александрийского римского иерусалимского антиохийского афонского египетского персидских всея руси великого нового первого второго пресв прес отца отцов апостола апостолов пророка пророков девы дев жен мужей воинов св сщ мц рождество зачатие успение положение честных ризы главы""".split(),
 'en': """the and of with new venerable martyr martyrs hieromartyr hieromartyrs holy bishop bishops priest priests abbot abbess relics monk monks nun nuns archbishop confessor confessors virgin mother father icon great monastery caves wonderworker god theotokos translation uncovering patriarch synaxis metropolitan sts saints all who apostle apostles blessed righteous prince princess venerables disciple disciples hermit hermits prophet prophets fool for christ those his her him our most saint deacon deacons emperor empress king queen elder abbot commemoration sunday before after feast forefeast afterfeast leavetaking those with him her them icons mother wife daughter son brother brothers sister sisters companions soldiers thousand hundred others martyred child children 
 constantinople kiev athos egypt rome alexandria serbia moscow novgorod georgia palestine gaul antioch caesarea thessalonica nicomedia cyprus persia sinai jerusalem russia greece bulgaria romania wales ireland england scotland britain italy spain africa asia syria armenia st nativity conception dormition placing honorable robe head hands seventy twelve""".split(),
}
GENERIC['en_nc'] = GENERIC['en']
# The app uses one list for all locales (BioMatcher.generic); do the same here.
_ALL = set().union(*GENERIC.values())
GENERIC = {loc: _ALL for loc in GENERIC}

def tokens(s, loc):
    out = []
    for raw in re.findall(r'\w+', s):
        t = raw.lower()
        if t.isdigit() or t[0].isdigit(): continue
        if len(t) < 2: continue
        if len(t) == 2 and not raw[0].isupper(): continue
        out.append(t)
    return out

def significant(s, loc):
    return [t for t in tokens(s, loc) if t not in GENERIC[loc]]

def osa_distance(a, b):
    """Optimal string alignment distance (Levenshtein + adjacent transposition)."""
    la, lb = len(a), len(b)
    d = [[0]*(lb+1) for _ in range(la+1)]
    for i in range(la+1): d[i][0] = i
    for j in range(lb+1): d[0][j] = j
    for i in range(1, la+1):
        for j in range(1, lb+1):
            cost = 0 if a[i-1] == b[j-1] else 1
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
            if i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:
                d[i][j] = min(d[i][j], d[i-2][j-2]+1)
    return d[la][lb]

def tok_match(a, b):
    """3 = same word, 2 = same word inflected/misspelt, 1 = weak (needs a unique candidate)."""
    if a == b: return 3
    n, m = min(len(a), len(b)), max(len(a), len(b))
    if n >= 5 and a[:5] == b[:5] and m - n <= 3: return 2
    if n >= 5 and m - n <= 2:
        dist = osa_distance(a, b)
        if dist <= 1:
            # A single substitution inside a short name (Матија/Марија) is a different
            # name; a dropped/added/swapped letter or a change in the last two letters is
            # inflection or a typo (Тедот/Теодот, Петар/Петра, Патрокло/Патрокле).
            if m != n or a[:-2] == b[:-2] or n >= 8: return 2
            return 0
        if dist <= 2 and n >= 8: return 2
    if n >= 4 and a[:4] == b[:4] and m - n <= 4: return 1
    if 3 <= n <= 4 and m - n <= 1 and a[:2] == b[:2] and osa_distance(a, b) <= 1: return 1
    return 0

def score(ft, bt):
    return sum(max((tok_match(f, b) for b in bt), default=0) for f in ft)

def new_assign(feasts, bios, loc, single_fallback=True):
    out = {}
    if not bios: return out
    fixed = [i for i, f in enumerate(feasts) if not f.get('moveable')]
    fs = {i: significant(feasts[i]['name'], loc) for i in fixed}
    fa = {i: set(tokens(feasts[i]['name'], loc)) for i in fixed}
    bs = [significant(b['title'], loc) for b in bios]
    ba = [set(tokens(b['title'], loc)) for b in bios]
    def pair_score(i, j):
        if fs[i]:
            s = score(fs[i], bs[j])
            # Names that differ only in generic words ("Сабор светих дванаест апостола" vs
            # "Сабор светих славних апостола") still qualify as a weak candidate.
            return s if s else (1 if len(fa[i] & ba[j]) >= 3 else 0)
        # No distinguishing word (e.g. "Сабор Пресвете Богородице"): the whole name must be inside the title.
        return 2 if fa[i] and fa[i] <= ba[j] else 0
    sc = {(i, j): pair_score(i, j) for i in fixed for j in range(len(bios))}
    used_f, used_b = set(), set()
    for s, i, j in sorted(((s, i, j) for (i, j), s in sc.items()), key=lambda p: (-p[0], p[1], p[2])):
        if s < 2: break
        if i in used_f or j in used_b: continue
        out[i] = j; used_f.add(i); used_b.add(j)
    for i in fixed:                      # weak matches only when there is exactly one candidate
        if i in used_f: continue
        cands = [j for j in range(len(bios)) if j not in used_b and sc[(i, j)] >= 1]
        if len(cands) == 1:
            out[i] = cands[0]; used_f.add(i); used_b.add(cands[0])
    if single_fallback and not out and len(bios) == 1:   # legacy single-bio day: first fixed feast
        for i in fixed: out[i] = 0; break
    return out

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def run(loc, show=40, year=2026):
    d = json.load(open(os.path.join(BASE, 'data', 'output', f'calendar_{loc}_{year}.json')))['days']
    tot = old_m = new_m = changed = 0
    diffs, leftovers = [], []
    for k in sorted(d):
        feasts = d[k]['feasts']; bios = d[k].get('saintBios') or []
        if not bios: continue
        o = old_assign(feasts, bios); n = new_assign(feasts, bios, loc)
        fixed = [i for i, f in enumerate(feasts) if not f.get('moveable')]
        tot += len(fixed); old_m += len(o); new_m += len(n)
        for i in fixed:
            if o.get(i) != n.get(i):
                changed += 1
                diffs.append((k, feasts[i]['name'][:48], bios[o[i]]['title'][:40] if i in o else '—', bios[n[i]]['title'][:40] if i in n else '—'))
        unb = [bios[j]['title'][:38] for j in range(len(bios)) if j not in n.values()]
        unf = [feasts[i]['name'][:38] for i in fixed if i not in n]
        if unb and unf: leftovers.append((k, unf, unb))
    print(f"=== {loc}: fixed feasts on days with bios {tot}; matched old {old_m}, new {new_m}; assignments changed {changed}; days with unmatched feast+bio {len(leftovers)}")
    for x in diffs[:show]: print("  DIFF", x)
    for x in leftovers[:show]: print("  LEFT", x)

if __name__ == '__main__':
    year = int(next((a.split('=')[1] for a in sys.argv[1:] if a.startswith('--year=')), 2026))
    locs = [a for a in sys.argv[1:] if not a.startswith('--')] or ['sr', 'ru', 'en', 'en_nc']
    for loc in locs:
        run(loc, year=year)
