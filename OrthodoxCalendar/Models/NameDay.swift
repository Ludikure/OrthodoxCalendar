import Foundation

/// A span of church dates and the weekday a moving commemoration keeps inside
/// it: "the Sunday after the Nativity" is Sunday between Julian 26 and 31
/// December. `weekday` follows the data's convention, 0 = Monday … 6 = Sunday
/// (`CalendarDay.dayOfWeek`); `first`/`last` are Julian "MM-DD", inclusive.
struct NameDayWindow: Codable, Hashable, Sendable {
    let weekday: Int
    let first: String
    let last: String
}

/// When a name day falls: a fixed church (Julian) date, a distance from Pascha,
/// or a weekday inside a window of church dates (`scripts/shared/fixed_cycle.py`'s
/// `between` rule). Stored this way, never as a civil date, so it lands on the
/// right day every year — like `SlavaAnchor`, whose arithmetic it reuses.
enum NameDayAnchor: Codable, Hashable, Sendable {
    case julian(month: Int, day: Int)
    case pascha(offset: Int)
    case weekday(windows: [NameDayWindow])

    /// The slava form of a fixed or Pascha-bound anchor: the same date rules.
    private var slava: SlavaDay? {
        switch self {
        case .julian(let m, let d): return SlavaDay("", "", .julian(month: m, day: d))
        case .pascha(let o): return SlavaDay("", "", .pascha(offset: o))
        case .weekday: return nil
        }
    }

    var isMoveable: Bool {
        if case .julian = self { return false }
        return true
    }

    /// Whether `day` is this commemoration, read from the church date, weekday
    /// and Pascha distance the data carries — so it agrees with the calendar.
    func matches(_ day: CalendarDay) -> Bool {
        if let slava { return slava.matches(day) }
        guard case .weekday(let windows) = self else { return false }
        return windows.contains { w in
            day.dayOfWeek == w.weekday && Self.inside(day.julianDate, w)
        }
    }

    private static func inside(_ key: String, _ w: NameDayWindow) -> Bool {
        w.first <= w.last ? (w.first <= key && key <= w.last) : (key >= w.first || key <= w.last)
    }

    /// The date in church year `year` (Pascha's year, or the Julian year of a
    /// fixed date: Julian 29 December 2026 is 11 January 2027).
    func occurrence(churchYear year: Int) -> Date? {
        if let slava { return slava.occurrence(churchYear: year) }
        guard case .weekday(let windows) = self else { return nil }
        let cal = ChurchDates.calendar
        var best: Date?
        for w in windows {
            let (fm, fd) = Self.monthDay(w.first), (lm, ld) = Self.monthDay(w.last)
            guard let start = ChurchDates.gregorian(fromJulianYear: year, month: fm, day: fd),
                  let end = ChurchDates.gregorian(fromJulianYear: w.first <= w.last ? year : year + 1,
                                                  month: lm, day: ld) else { continue }
            // Calendar weekdays run Sunday = 1 … Saturday = 7.
            let target = (w.weekday + 1) % 7 + 1
            var d = start
            while d <= end {
                if cal.component(.weekday, from: d) == target {
                    if best.map({ d < $0 }) ?? true { best = d }
                    break
                }
                guard let next = cal.date(byAdding: .day, value: 1, to: d) else { break }
                d = next
            }
        }
        return best
    }

    /// The first day this falls on, on or after `start`'s day.
    func nextOccurrence(onOrAfter start: Date) -> Date? {
        let from = ChurchDates.startOfDay(start)
        let year = ChurchDates.calendar.component(.year, from: from)
        for y in (year - 1)...(year + 1) {
            guard let date = occurrence(churchYear: y), date >= from else { continue }
            return date
        }
        return nil
    }

    static func monthDay(_ key: String) -> (Int, Int) {
        let parts = key.split(separator: "-").compactMap { Int($0) }
        return parts.count == 2 ? (parts[0], parts[1]) : (1, 1)
    }
}

/// Whose name day it is and which saint's: the name as the person uses it
/// ("Таня"), the church form it maps to ("Татиана"), and the commemoration
/// chosen — found from the birthday or picked by hand.
struct NameDayChoice: Codable, Hashable, Sendable {
    var name: String
    var churchName: String
    var title: String
    var anchor: NameDayAnchor
    /// Civil birthday month and day, when the name day was found from it.
    var birthMonth: Int?
    var birthDay: Int?

    func matches(_ day: CalendarDay) -> Bool { anchor.matches(day) }
    func nextOccurrence(onOrAfter start: Date) -> Date? { anchor.nextOccurrence(onOrAfter: start) }
}

/// A friend's or relative's name day.
struct FriendNameDay: Codable, Hashable, Identifiable, Sendable {
    var id = UUID()
    /// How the user calls them: "мама", "кум Сергей"; the name when empty.
    var person: String
    var nameDay: NameDayChoice

    var displayName: String { person.isEmpty ? nameDay.name : person }
}

/// What a calendar row shows about name days on its day.
struct NameDayMark: Equatable, Sendable {
    var isMine = false
    /// "мама · Галина", one per friend whose name day falls here.
    var friendLines: [String] = []

    var isEmpty: Bool { !isMine && friendLines.isEmpty }
}

/// One name in a day's "Именины" list.
struct DayName: Hashable, Sendable {
    let name: String
    /// A main saint of the day (the source's first paragraph).
    let isMain: Bool
}

/// The Russian name days bundled as `imeniny_ru.json` (generated by
/// `scripts/russian/bundle_imeniny.py` from the azbyka.ru calendar): which
/// names each day keeps, every commemoration of each name, and the civil →
/// church name correspondences ("Иван" → "Иоанн").
struct NameDayCatalog: Sendable {
    struct Commemoration: Hashable, Sendable, Identifiable {
        let name: String
        let anchor: NameDayAnchor
        let title: String
        let isNewMartyr: Bool
        var id: String { "\(name)|\(anchor)|\(title)" }
    }

    /// Church date → (main, other) names; "02-29" holds St John Cassian's.
    let days: [String: [DayName]]
    let pascha: [Int: [DayName]]
    let rules: [(anchor: NameDayAnchor, names: [String])]
    let names: [String: [Commemoration]]
    /// Folded civil or diminutive form → church forms, usual first.
    let civil: [String: [String]]
    /// Folded church name → church name.
    private let churchByFold: [String: String]

    static let shared: NameDayCatalog = {
        guard let url = Bundle.main.url(forResource: "imeniny_ru", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let catalog = NameDayCatalog(data: data) else { return NameDayCatalog.empty }
        return catalog
    }()

    /// How many names a day shows before "и другие".
    static let dayListLimit = 12

    private struct Raw: Decodable {
        struct Rule: Decodable { let w: [[Wire]]; let n: String }
        enum Wire: Decodable {
            case int(Int), string(String)
            init(from decoder: Decoder) throws {
                let c = try decoder.singleValueContainer()
                if let i = try? c.decode(Int.self) { self = .int(i) } else { self = .string(try c.decode(String.self)) }
            }
            var int: Int? { if case .int(let i) = self { return i }; return nil }
            var string: String? { if case .string(let s) = self { return s }; return nil }
        }
        let days: [String: String]
        let pascha: [String: String]
        let rules: [Rule]
        let titles: [String]
        let names: [String: [[Wire]]]
        let civil: [String: [String]]
    }

    private init(days: [String: [DayName]], pascha: [Int: [DayName]],
                 rules: [(anchor: NameDayAnchor, names: [String])],
                 names: [String: [Commemoration]], civil: [String: [String]]) {
        self.days = days
        self.pascha = pascha
        self.rules = rules
        self.names = names
        self.civil = civil
        var fold: [String: String] = [:]
        for name in names.keys { fold[Self.fold(name)] = name }
        churchByFold = fold
    }

    static let empty = NameDayCatalog(days: [:], pascha: [:], rules: [], names: [:], civil: [:])

    init?(data: Data) {
        guard let raw = try? JSONDecoder().decode(Raw.self, from: data) else { return nil }
        func dayNames(_ s: String) -> [DayName] {
            let halves = s.split(separator: ";", omittingEmptySubsequences: false)
            let main = halves.first.map { $0.split(separator: ",").map { DayName(name: String($0), isMain: true) } } ?? []
            let other = halves.count > 1 ? halves[1].split(separator: ",").map { DayName(name: String($0), isMain: false) } : []
            return main + other
        }
        let rules: [(anchor: NameDayAnchor, names: [String])] = raw.rules.map { r in
            let windows = r.w.compactMap { w -> NameDayWindow? in
                guard w.count == 3, let wd = w[0].int, let a = w[1].string, let b = w[2].string else { return nil }
                return NameDayWindow(weekday: wd, first: a, last: b)
            }
            return (.weekday(windows: windows), r.n.split(separator: ",").map(String.init))
        }
        var names: [String: [Commemoration]] = [:]
        for (name, rows) in raw.names {
            names[name] = rows.compactMap { row in
                guard row.count == 3, let a = row[0].string, let t = row[1].int, t < raw.titles.count,
                      let anchor = Self.anchor(a, rules: rules) else { return nil }
                return Commemoration(name: name, anchor: anchor, title: raw.titles[t], isNewMartyr: row[2].int == 1)
            }
        }
        self.init(days: raw.days.mapValues(dayNames),
                  pascha: Dictionary(uniqueKeysWithValues: raw.pascha.compactMap { k, v in Int(k).map { ($0, dayNames(v)) } }),
                  rules: rules, names: names, civil: raw.civil)
    }

    private static func anchor(_ s: String, rules: [(anchor: NameDayAnchor, names: [String])]) -> NameDayAnchor? {
        if s.hasPrefix("P") { return Int(s.dropFirst()).map { .pascha(offset: $0) } }
        if s.hasPrefix("R") {
            guard let i = Int(s.dropFirst()), i < rules.count else { return nil }
            return rules[i].anchor
        }
        let (m, d) = NameDayAnchor.monthDay(s)
        return .julian(month: m, day: d)
    }

    static func fold(_ s: String) -> String {
        s.trimmingCharacters(in: .whitespacesAndNewlines).lowercased().replacingOccurrences(of: "ё", with: "е")
    }

    // MARK: - A day's names

    /// Everyone whose name day `day` is, main saints first, each name once.
    func names(on day: CalendarDay) -> [DayName] {
        var fixed = days[day.julianDate] ?? []
        // Julian February 29 exists every fourth year; otherwise St John
        // Cassian is kept with the 28th.
        if day.julianDate == "02-28", let year = Int(day.gregorianDate.prefix(4)),
           !ChurchDates.isJulianLeap(year) {
            fixed += days["02-29"] ?? []
        }
        let moveable = pascha[day.paschaDistance] ?? []
        let ruled = rules.filter { $0.anchor.matches(day) }
            .flatMap { $0.names.map { DayName(name: $0, isMain: false) } }
        let all = moveable.filter(\.isMain) + fixed.filter(\.isMain)
            + moveable.filter { !$0.isMain } + fixed.filter { !$0.isMain } + ruled
        var seen = Set<String>()
        return all.filter { seen.insert($0.name).inserted }
    }

    /// The first `limit` names to show and how many "и другие" hides.
    static func capped(_ list: [DayName], limit: Int = dayListLimit) -> (shown: [DayName], hidden: Int) {
        // A cap that would hide just one name hides nothing.
        guard list.count > limit + 1 else { return (list, 0) }
        return (Array(list.prefix(limit)), list.count - limit)
    }

    // MARK: - Names

    /// The church forms a name the user types stands for: "Иван" → ["Иоанн"],
    /// "Юрий" → ["Георгий", "Юрий"], a church name itself → [it]. Empty when
    /// no saint by that name is in the calendar.
    func churchForms(for input: String) -> [String] {
        let key = Self.fold(input)
        guard !key.isEmpty else { return [] }
        if let forms = civil[key] { return forms.filter { names[$0] != nil } }
        if let church = churchByFold[key] { return [church] }
        return []
    }

    /// Autocomplete: known civil and church names starting with `prefix`,
    /// each with the church form it stands for.
    func suggestions(_ prefix: String, limit: Int = 8) -> [(name: String, church: String)] {
        let key = Self.fold(prefix)
        guard !key.isEmpty else { return [] }
        var out: [(name: String, church: String)] = []
        var seen = Set<String>()
        for civ in civil.keys.sorted() where civ.hasPrefix(key) {
            guard let church = churchForms(for: civ).first else { continue }
            let display = civ.prefix(1).uppercased() + civ.dropFirst()
            if seen.insert(display).inserted { out.append((display, church)) }
        }
        for (folded, church) in churchByFold.sorted(by: { $0.key < $1.key }) where folded.hasPrefix(key) {
            if seen.insert(church).inserted { out.append((church, church)) }
        }
        // Exact and shorter names first: "Иван" before "Иванна".
        return Array(out.sorted { ($0.name.count, $0.name) < ($1.name.count, $1.name) }.prefix(limit))
    }

    /// Every commemoration of a church name.
    func commemorations(of churchName: String) -> [Commemoration] {
        names[churchName] ?? []
    }

    /// Church names containing `query`, for the manual saint picker.
    func churchNames(matching query: String, limit: Int = 30) -> [String] {
        let key = Self.fold(query)
        guard !key.isEmpty else { return [] }
        let hits = churchByFold.filter { $0.key.contains(key) }
        return hits.sorted { ($0.key.hasPrefix(key) ? 0 : 1, $0.value) < ($1.key.hasPrefix(key) ? 0 : 1, $1.value) }
            .prefix(limit).map(\.value)
    }

    /// The name day by the Church's custom: the first commemoration of the
    /// name on or after the birthday (in `year`), wrapping into the next year.
    /// The first church form with any commemoration decides ("Юрий" → Георгий).
    /// New martyrs count only when asked for, as in azbyka.ru's own name-day
    /// finder ("учитывать новомучеников") — or when a name has no other saint.
    func firstNameDay(churchForms: [String], birthMonth: Int, birthDay: Int, year: Int,
                      includeNewMartyrs: Bool = false) -> (commemoration: Commemoration, date: Date)? {
        // February 29 in a common year counts from March 1.
        guard let birthday = ChurchDates.calendar.date(
            from: DateComponents(year: year, month: birthMonth, day: birthDay)) else { return nil }
        for form in churchForms {
            let all = commemorations(of: form)
            let older = all.filter { !$0.isNewMartyr }
            let candidates = includeNewMartyrs || older.isEmpty ? all : older
            let dated = candidates.compactMap { c in
                c.anchor.nextOccurrence(onOrAfter: birthday).map { (c, $0) }
            }
            if let best = dated.min(by: { $0.1 < $1.1 }) { return (best.0, best.1) }
        }
        return nil
    }
}

/// Russian wording for name days, shared by the views and the reminders.
enum NameDayText {
    static let icon = "gift"

    /// "через 5 дней", with Russian plurals: 1 день, 2–4 дня, 5–20 дней, 21 день.
    static func countdown(_ days: Int) -> String {
        switch days {
        case 0: return "С днём ангела!"
        case 1: return "завтра"
        default: return "через \(days) \(daysWord(days))"
        }
    }

    static func daysWord(_ n: Int) -> String {
        let mod10 = n % 10, mod100 = n % 100
        if mod10 == 1 && mod100 != 11 { return "день" }
        if (2...4).contains(mod10) && !(12...14).contains(mod100) { return "дня" }
        return "дней"
    }
}
