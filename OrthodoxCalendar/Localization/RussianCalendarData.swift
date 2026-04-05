import Foundation

/// Russian saints data, reusable across all years.
/// Fixed saints keyed by Julian MM-DD, moveable feasts keyed by pascha distance.
struct RussianCalendarData: Sendable {
    static let shared = RussianCalendarData()

    let fixedByJulianDate: [String: RussianDayEntry]
    let moveableByPaschaDistance: [String: RussianDayEntry]

    private init() {
        guard let url = Bundle.main.url(forResource: "ru_saints_map", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let parsed = try? JSONDecoder().decode(RussianSaintsMap.self, from: data) else {
            self.fixedByJulianDate = [:]
            self.moveableByPaschaDistance = [:]
            return
        }
        self.fixedByJulianDate = parsed.fixedByJulianDate
        self.moveableByPaschaDistance = parsed.moveableByPaschaDistance
    }

    func entry(gregorianDate: Date, paschaDistance: Int?) -> RussianDayEntry? {
        if let pd = paschaDistance, let entry = moveableByPaschaDistance[String(pd)] {
            return entry
        }
        let julian = gregorianDate.addingTimeInterval(-13 * 86400)
        let cal = Calendar(identifier: .gregorian)
        let m = cal.component(.month, from: julian)
        let d = cal.component(.day, from: julian)
        let key = String(format: "%02d-%02d", m, d)
        return fixedByJulianDate[key]
    }
}

struct RussianSaintsMap: Codable {
    let source: String
    let fixedByJulianDate: [String: RussianDayEntry]
    let moveableByPaschaDistance: [String: RussianDayEntry]
}

struct RussianDayEntry: Codable, Sendable {
    let description: String
    let fasting: String
    let isMajorFeast: Bool
    let fastingFull: String?
    let prayer: String?
    let liturgicalNote: String?
}
