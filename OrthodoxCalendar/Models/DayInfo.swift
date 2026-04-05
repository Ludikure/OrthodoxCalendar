import Foundation

struct DayInfo: Identifiable, Sendable {
    var id: Date { gregorianDate }

    let gregorianDate: Date
    var julianDateString: String = ""
    var julianDay: Int = 0

    // Display (localized)
    var displayName: String = ""
    var feastType: FeastType?
    var extraFeastName: String?
    var extraFeastDescription: String?

    // Fasting
    var fastLevelDesc: String = ""
    var fastExceptionDesc: String = ""
    var fastingAbbrev: String = ""
    var fastLevel: Int = 0
    var fastException: Int = 0

    // Liturgical
    var tone: Int?
    var paschaDistance: Int?
    var weekday: Int = 0 // 0=Sun, 1=Mon..6=Sat (API convention)

    // Scraped localized data (from crkvenikalendar.rs / days.pravoslavie.ru)
    var localDescription: String = ""
    var localIsRed: Bool = false
    var localIsBold: Bool = false
    var localFastingDesc: String = ""
    var localPrayer: String = ""
    var localLiturgicalNote: String = ""

    // API data (English, pass-through)
    var saints: [String] = []
    var feasts: [String] = []
    var readings: [OrthocalReading] = []
    var stories: [OrthocalStory] = []

    // MARK: - Computed

    var gregorianDay: Int {
        Calendar(identifier: .gregorian).component(.day, from: gregorianDate)
    }

    var isSunday: Bool {
        weekday == 0
    }

    /// Whether this day has a significant feast to show in bold
    var isSignificantFeast: Bool {
        guard let type = feastType else { return false }
        return type.rank >= FeastType.major.rank
    }
}
