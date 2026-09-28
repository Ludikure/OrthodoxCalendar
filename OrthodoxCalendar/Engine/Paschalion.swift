import Foundation

/// Orthodox Pascha for a year, computed rather than read from the data.
///
/// The calendar screens take Pascha from the year files (`paschaDistance`),
/// but slava reminders are scheduled for years that may not be loaded — or
/// even downloaded — so a moveable slava (Lazarus Saturday, Spasovdan) needs
/// its date without them. `SlavaTests` checks this against every bundled year.
enum Paschalion {
    /// Pascha in the civil (Gregorian) calendar: Meeus's Julian algorithm plus
    /// the 13-day offset, which holds from 1900-03-01 to 2100-02-28 — the whole
    /// span the app serves (2024–2099).
    static func pascha(year: Int) -> Date? {
        let a = year % 4, b = year % 7, c = year % 19
        let d = (19 * c + 15) % 30
        let e = (2 * a + 4 * b - d + 34) % 7
        let month = (d + e + 114) / 31
        let day = (d + e + 114) % 31 + 1
        return ChurchDates.gregorian(fromJulianYear: year, month: month, day: day)
    }
}

/// Julian ↔ civil date conversion for 1900–2099, where the offset is 13 days.
enum ChurchDates {
    static let calendar: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = .current
        return cal
    }()

    static func isJulianLeap(_ year: Int) -> Bool { year % 4 == 0 }

    /// The civil date of Julian `year-month-day`. Julian February 29 in a
    /// year without one is kept on February 28, as the Church does.
    static func gregorian(fromJulianYear year: Int, month: Int, day: Int) -> Date? {
        let d = (month == 2 && day == 29 && !isJulianLeap(year)) ? 28 : day
        guard let labels = calendar.date(from: DateComponents(year: year, month: month, day: d)) else {
            return nil
        }
        return calendar.date(byAdding: .day, value: 13, to: labels)
    }

    /// The Julian month and day of a civil date.
    static func julian(from date: Date) -> (month: Int, day: Int) {
        let shifted = calendar.date(byAdding: .day, value: -13, to: date) ?? date
        let c = calendar.dateComponents([.month, .day], from: shifted)
        return (c.month ?? 1, c.day ?? 1)
    }

    /// Midnight at the start of `date`'s day.
    static func startOfDay(_ date: Date) -> Date { calendar.startOfDay(for: date) }
}
