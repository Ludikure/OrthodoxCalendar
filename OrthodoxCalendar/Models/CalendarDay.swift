import Foundation

// MARK: - Top-level calendar file wrapper

struct CalendarFile: Codable, Sendable {
    let year: Int
    let locale: String
    let generatedBy: String
    let days: [String: CalendarDay]
}

// MARK: - CalendarDay

struct CalendarDay: Codable, Identifiable, Equatable, Hashable, Sendable {
    let gregorianDate: String          // "2026-01-07"
    let julianDate: String             // "12-25"
    let dayOfWeek: Int                 // Python convention: 0=Mon..6=Sun
    let paschaDistance: Int
    let feasts: [Feast]
    let liturgicalPeriod: String?
    let weekLabel: String?
    let greatFeast: String?
    let fasting: FastingInfo
    var readings: [ScriptureReading]
    let reflection: Reflection?
    var saintBios: [SaintBio]?
    let fastingPeriod: String?
    let isFastFreeWeek: Bool?

    // MARK: - Identifiable

    var id: String { gregorianDate }

    // MARK: - Computed Properties

    /// The primary feast for this day (first feast with displayRole "primary")
    var primaryFeast: Feast? {
        feasts.first { $0.displayRole == "primary" }
    }

    /// Secondary feasts (displayRole == "secondary")
    var secondaryFeasts: [Feast] {
        feasts.filter { $0.displayRole == "secondary" }
    }

    /// Tertiary feasts (displayRole == "tertiary")
    var tertiaryFeasts: [Feast] {
        feasts.filter { $0.displayRole == "tertiary" }
    }

    /// Whether this day is a Sunday (Python convention: 6=Sun)
    var isSunday: Bool {
        dayOfWeek == 6
    }

    /// Whether this day is a Saturday (Python convention: 5=Sat)
    var isSaturday: Bool {
        dayOfWeek == 5
    }

    /// Converts Python weekday (0=Mon..6=Sun) to localization array index (0=Sun..6=Sat)
    var weekdayIndex: Int {
        (dayOfWeek + 1) % 7
    }

    /// The day number extracted from julianDate string "MM-DD"
    var julianDay: Int {
        guard let lastDash = julianDate.lastIndex(of: "-") else { return 0 }
        let dayString = julianDate[julianDate.index(after: lastDash)...]
        return Int(dayString) ?? 0
    }

    /// The day-of-month number extracted from gregorianDate
    var gregorianDay: Int {
        guard let lastDash = gregorianDate.lastIndex(of: "-") else { return 0 }
        let dayString = gregorianDate[gregorianDate.index(after: lastDash)...]
        return Int(dayString) ?? 0
    }

    /// The month number extracted from gregorianDate
    var gregorianMonth: Int {
        let parts = gregorianDate.split(separator: "-")
        guard parts.count >= 2 else { return 0 }
        return Int(parts[1]) ?? 0
    }

    /// Whether this day has a great feast
    var isGreatFeast: Bool {
        greatFeast != nil
    }

    /// Parsed Date from gregorianDate string
    var date: Date? {
        DateKeys.date(from: gregorianDate)
    }

    // MARK: - Hashable (use gregorianDate as unique key for navigation)

    func hash(into hasher: inout Hasher) {
        hasher.combine(gregorianDate)
    }
}

/// The `yyyy-MM-dd` / `MM-dd` keys the calendar JSON is indexed by.
///
/// Locale and numbering system are pinned to `en_US_POSIX` deliberately. A
/// locale-aware formatter follows the user's numbering system: on a device set
/// to ar_SA or fa_IR (or any "use Arabic-Indic digits" preference) it renders
/// `٢٠٢٦-٠٩-٠٩`, and with a Thai Buddhist calendar `2569-09-09`. Those strings
/// never equal the ASCII keys in the data files, so "today" silently stops
/// matching — no highlight, no auto-scroll, and the fasting banner loses its
/// "Day X of Y". The formatter is shared rather than rebuilt per view
/// evaluation (DateFormatter construction is expensive and these are read in
/// `body`).
enum DateKeys {
    /// Implementation detail: pinned formatter shared by `key(from:)` and
    /// `date(from:)`. Read it in tests to assert the pinning, never mutate it —
    /// it is one shared instance serving every caller in the process.
    static let formatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = .current
        return formatter
    }()

    /// Today's key in the user's timezone, ASCII digits.
    static var today: String { key(from: Date()) }

    /// The `yyyy-MM-dd` key for `date`, in the user's timezone.
    static func key(from date: Date) -> String { formatter.string(from: date) }

    /// The date a `yyyy-MM-dd` key refers to, or nil if it is not one.
    static func date(from key: String) -> Date? { formatter.date(from: key) }

    /// The calendar day after `cur`. Compared in one fixed timezone so a
    /// daylight-saving boundary cannot turn a 23-hour day into a gap that splits
    /// a fasting season in two.
    static func isConsecutive(_ cur: String, _ next: String) -> Bool {
        guard let a = utcFormatter.date(from: cur), let b = utcFormatter.date(from: next) else {
            return false
        }
        return utcCalendar.dateComponents([.day], from: a, to: b).day == 1
    }

    private static let utcCalendar: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0) ?? .current
        return cal
    }()

    private static let utcFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.calendar = utcCalendar
        formatter.timeZone = utcCalendar.timeZone
        return formatter
    }()
}

// MARK: - Feast

struct Feast: Codable, Equatable, Sendable {
    static func == (lhs: Feast, rhs: Feast) -> Bool {
        lhs.name == rhs.name && lhs.importance == rhs.importance && lhs.displayRole == rhs.displayRole
    }
    let name: String
    let importance: String             // "great", "bold", "normal"
    let displayRole: String            // "primary", "secondary", "tertiary"
    let type: String                   // "feast", "saint", "martyr", "venerable", etc.
    let isSlava: Bool
    let moveable: Bool
    let description: String?
    let liturgicalContext: String?

    // Optional fields present in the JSON
    let position: Int?
    let serbianSaint: Bool?

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try container.decode(String.self, forKey: .name)
        importance = try container.decode(String.self, forKey: .importance)
        displayRole = try container.decode(String.self, forKey: .displayRole)
        type = try container.decode(String.self, forKey: .type)
        isSlava = try container.decodeIfPresent(Bool.self, forKey: .isSlava) ?? false
        moveable = try container.decodeIfPresent(Bool.self, forKey: .moveable) ?? false
        description = try container.decodeIfPresent(String.self, forKey: .description)
        liturgicalContext = try container.decodeIfPresent(String.self, forKey: .liturgicalContext)
        position = try container.decodeIfPresent(Int.self, forKey: .position)
        serbianSaint = try container.decodeIfPresent(Bool.self, forKey: .serbianSaint)
    }

    private enum CodingKeys: String, CodingKey {
        case name, importance, displayRole, type, isSlava, moveable, description, liturgicalContext, position, serbianSaint
    }

    /// Convenience initializer for building from API data (bridge)
    init(name: String, importance: String, role: String) {
        self.name = name
        self.importance = importance
        self.displayRole = role
        self.type = "saint"
        self.isSlava = false
        self.moveable = false
        self.description = nil
        self.liturgicalContext = nil
        self.position = nil
        self.serbianSaint = nil
    }
}

// MARK: - FastingInfo

struct FastingInfo: Codable, Equatable, Sendable {
    let type: String                   // "free", "fish", "dryEating", "hotWithOil", etc.
    let label: String
    let explanation: String
    let abbrev: String?
    let icon: String?
}

// MARK: - ScriptureReading

struct ScriptureReading: Codable, Equatable, Sendable {
    let type: String                   // "apostol", "gospel", "ot"
    let book: String?
    let title: String?
    let reference: String?
    let zachalo: Int?
    var text: String?                  // Full scripture text (KJV NT / Brenton OT for English)
    var textWeb: String?               // Alternate NT text (World English Bible), English only
    let service: String?               // "Јутрења", "Литургија", etc.
    // The lectionary slot this reading came from ("Vespers", "8th Matins Gospel")
    // and, for a commemoration reading, whose it is ("Theotokos", "Forerunner").
    // Both are written by the pipeline in English because they come from the
    // lectionary tables. Modelled so the schema this repo shares with the Android
    // port is complete rather than silently truncated on decode; `service` is
    // still what the card shows here, while Android translates `source` to fill
    // the same slot for the readings that have no `service` (see PARITY.md in
    // the Android repo, Ludikure/OrthodoxCalendarAndroid — it is not bundled here).
    let source: String?
    let desc: String?
    // Deduped bundled data: text/textWeb live in the texts_<locale> pool, keyed here.
    let textRef: String?
    let textWebRef: String?

    /// Best available display string for this reading
    var displayReference: String {
        reference ?? title ?? book ?? type
    }

    /// Scripture text for the chosen English NT translation (OT/non-English ignore it).
    func text(for translation: BibleTranslation) -> String? {
        if translation == .web, let web = textWeb { return web }
        return text
    }
}

// MARK: - Reflection

struct Reflection: Codable, Equatable, Sendable {
    let source: String
    let text: String
}

// MARK: - Saint Biography

struct SaintBio: Codable, Equatable, Sendable {
    let title: String
    /// Empty in deduped bundled data; filled from the bios_<locale> pool via `ref`.
    /// Always present in API-streamed data.
    var text: String
    /// Content hash into bios_<locale>.json (deduped bundled files only).
    let ref: String?

    init(title: String, text: String, ref: String? = nil) {
        self.title = title
        self.text = text
        self.ref = ref
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = try c.decode(String.self, forKey: .title)
        text = try c.decodeIfPresent(String.self, forKey: .text) ?? ""
        ref = try c.decodeIfPresent(String.self, forKey: .ref)
    }

    private enum CodingKeys: String, CodingKey { case title, text, ref }
}
