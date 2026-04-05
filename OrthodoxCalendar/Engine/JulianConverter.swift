import Foundation

enum JulianConverter {
    /// Julian-to-Gregorian offset for years 1900–2099
    static let offset = 13

    /// Returns the Julian month and day for a given Gregorian date
    static func julianComponents(from date: Date) -> (month: Int, day: Int) {
        let calendar = Calendar(identifier: .gregorian)
        guard let julian = calendar.date(byAdding: .day, value: -offset, to: date) else {
            return (0, 0)
        }
        return (calendar.component(.month, from: julian), calendar.component(.day, from: julian))
    }

    /// Formatted Julian date string "dd/MM"
    static func julianDisplayString(from date: Date) -> String {
        let (month, day) = julianComponents(from: date)
        return String(format: "%02d/%02d", day, month)
    }

    /// Convert Julian month/day to Gregorian Date for a given year
    static func gregorianDate(julianMonth: Int, julianDay: Int, year: Int) -> Date? {
        var components = DateComponents()
        components.year = year
        components.month = julianMonth
        components.day = julianDay + offset
        let calendar = Calendar(identifier: .gregorian)
        return calendar.date(from: components)
    }
}
