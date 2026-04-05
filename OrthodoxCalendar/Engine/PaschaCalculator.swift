import Foundation

enum PaschaCalculator {
    /// Compute the Gregorian date of Pascha for a given year
    /// Uses the Meeus Julian algorithm + Julian-to-Gregorian offset
    static func pascha(for year: Int) -> Date? {
        let a = year % 19
        let b = year % 4
        let c = year % 7
        let d = (19 * a + 15) % 30
        let e = (2 * b + 4 * c + 6 * d + 6) % 7

        let julianMonth: Int
        let julianDay: Int
        if d + e < 10 {
            julianMonth = 3
            julianDay = 22 + d + e
        } else {
            julianMonth = 4
            julianDay = d + e - 9
        }

        // Convert Julian date to Gregorian
        var components = DateComponents()
        components.year = year
        components.month = julianMonth
        components.day = julianDay + JulianConverter.offset
        return Calendar(identifier: .gregorian).date(from: components)
    }

    /// Distance in days from Pascha for a given date
    static func paschaDistance(for date: Date, year: Int) -> Int? {
        guard let pascha = pascha(for: year) else { return nil }
        let calendar = Calendar(identifier: .gregorian)
        return calendar.dateComponents([.day], from: pascha, to: date).day
    }
}
