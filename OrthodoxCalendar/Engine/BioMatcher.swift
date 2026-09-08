import Foundation

/// Pairs each fixed (non-moveable) feast of a day with the saint biography that
/// belongs to it by comparing the distinguishing words of the feast name with
/// the words of each bio title.
///
/// Rank, place and liturgical words ("свети", "мученик", "прп.", "bishop",
/// "цариградски") carry no identity and are ignored. The remaining words are
/// compared with tolerance for inflection (Вартоломеј/Вартоломеја, Петар/Петра),
/// spelling variants (Јевстатије/Евстатије, Тедот/Теодот) and OCR typos. A bio
/// whose title *is* a feast's name is paired with it first; the rest are assigned
/// best-first across the whole day, and a weak match is accepted only when it is
/// the sole remaining candidate, because a wrong bio is worse than none.
///
/// `scripts/shared/simulate_bio_matching.py` is the reference implementation and
/// runs the same rules over a whole year of data; keep the two (and the Android
/// port) in sync.
enum BioMatcher {

    /// Returns feast index -> bio index for every feast that gets a bio.
    static func assign(feastNames: [String], moveable: [Bool], bioTitles: [String]) -> [Int: Int] {
        guard !bioTitles.isEmpty, feastNames.count == moveable.count else { return [:] }
        let fixed = feastNames.indices.filter { !moveable[$0] }
        let feastAll = feastNames.map { Set(tokens($0)) }
        let feastSig = feastNames.map { significant($0) }
        let bioAll = bioTitles.map { Set(tokens($0)) }
        let bioSig = bioTitles.map { significant($0) }

        func pairScore(_ i: Int, _ j: Int) -> Int {
            if !feastSig[i].isEmpty {
                let s = score(feastSig[i], bioSig[j])
                if s > 0 { return s }
                // Names that differ only in generic words ("Сабор светих дванаест апостола"
                // vs "Сабор светих славних апостола") still qualify as a weak candidate.
                return feastAll[i].intersection(bioAll[j]).count >= 3 ? 1 : 0
            }
            // No distinguishing word at all ("Сабор Пресвете Богородице"): the whole
            // name has to be contained in the title.
            return !feastAll[i].isEmpty && feastAll[i].isSubset(of: bioAll[j]) ? 2 : 0
        }

        var scores: [Int: [Int]] = [:]
        var pairs: [(score: Int, feast: Int, bio: Int)] = []
        for i in fixed {
            scores[i] = bioTitles.indices.map { pairScore(i, $0) }
            for j in bioTitles.indices { pairs.append((scores[i]![j], i, j)) }
        }
        pairs.sort {
            if $0.score != $1.score { return $0.score > $1.score }
            if $0.feast != $1.feast { return $0.feast < $1.feast }
            return $0.bio < $1.bio
        }

        var result: [Int: Int] = [:]
        var usedBios = Set<Int>()
        // A bio whose title *is* a feast's name names that feast and no other.
        // Pair those first: the greedy pass below breaks score ties by position,
        // so on a day with several similar names (three Macarii, "Constantine and
        // Helen" next to "Helen of Dechani") the bio would otherwise go to
        // whichever tying feast comes first. A named bio left over duplicates one
        // already placed — it stays unassigned rather than landing on a stranger.
        let feastWords = feastNames.map { tokens($0) }
        let bioWords = bioTitles.map { tokens($0) }
        let names = Set(feastWords.filter { !$0.isEmpty })
        for (j, title) in bioWords.enumerated() where names.contains(title) {
            if let i = fixed.first(where: { result[$0] == nil && feastWords[$0] == title }) {
                result[i] = j
            }
            usedBios.insert(j)
        }
        for pair in pairs where pair.score >= 2 {
            if result[pair.feast] != nil || usedBios.contains(pair.bio) { continue }
            result[pair.feast] = pair.bio
            usedBios.insert(pair.bio)
        }
        // Weak matches only when there is exactly one candidate left for the feast.
        for i in fixed where result[i] == nil {
            let candidates = bioTitles.indices.filter { !usedBios.contains($0) && scores[i]![$0] >= 1 }
            if candidates.count == 1 {
                result[i] = candidates[0]
                usedBios.insert(candidates[0])
            }
        }
        // Legacy single-bio day (one combined text): show it on the first fixed feast.
        if result.isEmpty, bioTitles.count == 1, !usedBios.contains(0), let first = fixed.first {
            result[first] = 0
        }
        return result
    }

    // MARK: - Words

    /// Lower-cased words of a name. Numbers are dropped; two-letter words count
    /// only when capitalised (a name like "Ор" or a numeral like "II", not "св").
    static func tokens(_ text: String) -> [String] {
        var out: [String] = []
        for raw in text.split(whereSeparator: { !($0.isLetter || $0.isNumber || $0 == "_") }) {
            guard let first = raw.first, !first.isNumber else { continue }
            let count = raw.count
            if count < 2 { continue }
            if count == 2 && !first.isUppercase { continue }
            out.append(raw.lowercased())
        }
        return out
    }

    static func significant(_ text: String) -> [String] {
        tokens(text).filter { !generic.contains($0) }
    }

    /// Sum over the feast's words of the best match among the bio's words.
    static func score(_ feastWords: [String], _ bioWords: [String]) -> Int {
        feastWords.reduce(0) { total, f in
            total + (bioWords.map { tokenMatch(f, $0) }.max() ?? 0)
        }
    }

    /// 3 = same word, 2 = same word inflected or misspelt, 1 = weak (needs a
    /// unique candidate), 0 = different words.
    static func tokenMatch(_ a: String, _ b: String) -> Int {
        if a == b { return 3 }
        let ca = Array(a), cb = Array(b)
        let n = min(ca.count, cb.count), m = max(ca.count, cb.count)
        if n >= 5 && ca.prefix(5) == cb.prefix(5) && m - n <= 3 { return 2 }
        if n >= 5 && m - n <= 2 {
            let dist = osaDistance(ca, cb)
            if dist <= 1 {
                // A single substitution inside a short name (Матија/Марија) is a
                // different name; a dropped, added or swapped letter, or a change in
                // the last two letters, is inflection or a typo (Тедот/Теодот,
                // Петар/Петра, Патрокло/Патрокле).
                if m != n || ca.dropLast(2) == cb.dropLast(2) || n >= 8 { return 2 }
                return 0
            }
            if dist <= 2 && n >= 8 { return 2 }
        }
        if n >= 4 && ca.prefix(4) == cb.prefix(4) && m - n <= 4 { return 1 }
        if n >= 3 && n <= 4 && m - n <= 1 && ca.prefix(2) == cb.prefix(2) && osaDistance(ca, cb) <= 1 { return 1 }
        return 0
    }

    /// Optimal string alignment distance: Levenshtein plus adjacent transposition.
    static func osaDistance(_ a: [Character], _ b: [Character]) -> Int {
        let la = a.count, lb = b.count
        var d = [[Int]](repeating: [Int](repeating: 0, count: lb + 1), count: la + 1)
        for i in 0...la { d[i][0] = i }
        for j in 0...lb { d[0][j] = j }
        if la == 0 || lb == 0 { return max(la, lb) }
        for i in 1...la {
            for j in 1...lb {
                let cost = a[i - 1] == b[j - 1] ? 0 : 1
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
                if i > 1, j > 1, a[i - 1] == b[j - 2], a[i - 2] == b[j - 1] {
                    d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
                }
            }
        }
        return d[la][lb]
    }

    /// Words that name a rank, place, feast type or number rather than a person,
    /// for Serbian, Russian and English titles together.
    static let generic: Set<String> = Set("""
abbess abbot africa after afterfeast alexandria all and antioch apostle apostles archbishop
armenia asia athos before bishop bishops blessed britain brother brothers bulgaria caesarea
caves child children christ commemoration companions conception confessor confessors
constantinople cyprus daughter deacon deacons disciple disciples dormition egypt elder
emperor empress england father feast fool for forefeast gaul georgia god great greece hands
head her hermit hermits hieromartyr hieromartyrs him his holy honorable hundred icon icons
ii iii ireland italy jerusalem kiev king leavetaking martyr martyred martyrs metropolitan
monastery monk monks moscow most mother nativity new nicomedia novgorod nun nuns of others
our palestine patriarch persia placing priest priests prince princess prophet prophets queen
relics righteous robe romania rome russia saint saints scotland serbia seventy sinai sister
sisters soldiers son spain st sts sunday synaxis syria the them theotokos thessalonica those
thousand translation twelve uncovering venerable venerables virgin wales who wife with
wonderworker александрийского александријски анахорет антиохийского антиохијски ап апостол
апостолa апостола апостоли апостолов апп архидиакона архиепископ архиепископа архимандрит
архимандрита атонски афонского блажена блажени блгв блгвв блж ближних богородица богородице
богородицы божией брат брата велика велики великого великомученик великомученица вериге вмц
вмч воинов војник војника војници всех всея второго главе главы господа господня господње
господњег грузијски дальних два дев девица девице девојака девојке девы день десет дете деца
деце диакона дня друга други другим других египатски египетского его епископ епископа
епископи епископов жен жена затворника зачатие зачеће игуман игумана игуманија игумена
игумении иеродиакона иеромонаха иерусалимского иже икона иконе иконы инока иных исп
исповедник исповедника исповедников исповедници киевского кипарски кн кнез кнеза княгини
князя константинопольского које који краљ краља кћи матери мати мајка митрополит митрополита
монах монаха монахини монахиња московски московского мошти моштију мощей мощи мужей мученик
мученика мучеников мучениц мученица мученице мученици мученицима мц мцц мч мчч ним ними нова
новгородски новгородского нови нового новомученик новомученика новомучеников новомученици
новомч новомчч обретение обретење остале остали отац отаца отдание отца отцов оци
палестински память патриарха патријарх патријарха первого перенесение персидских пет
печерски печерских печерского пещерах подвижник подвижника положение попразднство послушника
прав праведна праведни предпразднство презвитер презвитера пренос преноса преподобна
преподобне преподобни преподобних преподобног преподобномученик преподобномученица
преподобномученици преподобных прес пресв пресвете пресвитера пресвитеров пресвятой прмц
прмцц прмч прмчч прор пророк пророка пророков прочих прп прписп прпп пустињак равноап ради
ризе ризы римски римского рождество рођење руке руси сабор св света свете свети светитељ
светитеља светих свето светог светога светогорски светом свештеномученик свештеномученика
свештеномученици свих свт свтт святая святителя святой святых священника седам седамдесет
седамдесеторице сестра сестре син сина синајски собор солунски спомен српски старац старца
столпник студенички схимник схимонах сщ сщисп сщмч сщмчч трећи три успение успеније успења
ученик ученика ученици хиландарски христа христов христових цар цара цариградски царица
царице царицы царя часне часних честных четири чудотворац чудотворца чудотворцев шест
юродивого ђакон ђакона јерусалимски јуродиви људи њим њима
""".split(whereSeparator: \.isWhitespace).map(String.init))
}
