import Foundation

// MARK: - Top-level calendar file wrapper

struct CalendarFile: Codable, Sendable {
    let year: Int
    let locale: String
    let generatedBy: String
    let days: [String: CalendarDay]
}

// MARK: - CalendarDay

struct CalendarDay: Codable, Identifiable, Hashable, Sendable {
    static func == (lhs: CalendarDay, rhs: CalendarDay) -> Bool { lhs.gregorianDate == rhs.gregorianDate }
    func hash(into hasher: inout Hasher) { hasher.combine(gregorianDate) }
    let gregorianDate: String          // "2026-01-07"
    let julianDate: String             // "12-25"
    let dayOfWeek: Int                 // Python convention: 0=Mon..6=Sun
    let paschaDistance: Int
    let feasts: [Feast]
    let liturgicalPeriod: String?
    let weekLabel: String?
    let greatFeast: String?
    let fasting: FastingInfo
    let readings: [ScriptureReading]
    let reflection: Reflection?
    let fastingPeriod: String?
    let isFastFreeWeek: Bool

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
        Self.dateFormatter.date(from: gregorianDate)
    }

    private static let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter
    }()
}

// MARK: - Feast

struct Feast: Codable, Sendable {
    let name: String
    let importance: String             // "great", "bold", "normal"
    let displayRole: String            // "primary", "secondary", "tertiary"
    let type: String                   // "feast", "saint", "martyr", "venerable", etc.
    let isSlava: Bool
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
        liturgicalContext = try container.decodeIfPresent(String.self, forKey: .liturgicalContext)
        position = try container.decodeIfPresent(Int.self, forKey: .position)
        serbianSaint = try container.decodeIfPresent(Bool.self, forKey: .serbianSaint)
    }

    private enum CodingKeys: String, CodingKey {
        case name, importance, displayRole, type, isSlava, liturgicalContext, position, serbianSaint
    }

    /// Convenience initializer for building from API data (bridge)
    init(name: String, importance: String, role: String) {
        self.name = name
        self.importance = importance
        self.displayRole = role
        self.type = "saint"
        self.isSlava = false
        self.liturgicalContext = nil
        self.position = nil
        self.serbianSaint = nil
    }
}

// MARK: - FastingInfo

struct FastingInfo: Codable, Sendable {
    let type: String                   // "free", "fish", "dryEating", "hotWithOil", etc.
    let label: String
    let explanation: String
    let abbrev: String
    let icon: String
}

// MARK: - ScriptureReading

struct ScriptureReading: Codable, Sendable {
    let type: String                   // "apostol", "gospel", "ot"
    let book: String?
    let title: String?
    let reference: String?
    let zachalo: Int?
    let text: String?                  // Full scripture text
    let service: String?               // "Јутрења", "Литургија", etc.

    /// Best available display string for this reading
    var displayReference: String {
        reference ?? title ?? book ?? type
    }
}

// MARK: - Reflection

struct Reflection: Codable, Sendable {
    let source: String
    let text: String
}
