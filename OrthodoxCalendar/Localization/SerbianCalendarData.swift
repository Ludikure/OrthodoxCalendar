import Foundation

/// Serbian saints data, reusable across all years.
/// Fixed saints keyed by Julian MM-DD, moveable feasts keyed by pascha distance.
struct SerbianCalendarData: Sendable {
    static let shared = SerbianCalendarData()

    let fixedByJulianDate: [String: SerbianDayEntry]
    let moveableByPaschaDistance: [String: SerbianDayEntry]

    private init() {
        guard let url = Bundle.main.url(forResource: "sr_saints_map", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let parsed = try? JSONDecoder().decode(SerbianSaintsMap.self, from: data) else {
            self.fixedByJulianDate = [:]
            self.moveableByPaschaDistance = [:]
            return
        }
        self.fixedByJulianDate = parsed.fixedByJulianDate
        self.moveableByPaschaDistance = parsed.moveableByPaschaDistance
    }

    func entry(gregorianDate: Date, paschaDistance: Int?) -> SerbianDayEntry? {
        // 1. Check moveable feasts first (they override fixed saints)
        if let pd = paschaDistance, let entry = moveableByPaschaDistance[String(pd)] {
            return entry
        }
        // 2. Look up by Julian date
        let julian = gregorianDate.addingTimeInterval(-13 * 86400)
        let cal = Calendar(identifier: .gregorian)
        let m = cal.component(.month, from: julian)
        let d = cal.component(.day, from: julian)
        let key = String(format: "%02d-%02d", m, d)
        return fixedByJulianDate[key]
    }
}

struct SerbianSaintsMap: Codable {
    let source: String
    let fixedByJulianDate: [String: SerbianDayEntry]
    let moveableByPaschaDistance: [String: SerbianDayEntry]
}

struct SerbianDayEntry: Codable, Sendable {
    let description: String
    let fasting: String
    let isRed: Bool
    let isBold: Bool
}
