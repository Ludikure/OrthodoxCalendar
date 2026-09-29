import Foundation

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
