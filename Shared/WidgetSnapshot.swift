import Foundation

/// What the widgets show, written by the app into the shared App Group
/// container and read by the widget extension.
///
/// The extension never opens a year file: a resolved year is tens of MB and a
/// widget gets about 30 MB in all. The app, which has the year loaded anyway,
/// writes the next few weeks here — a few kilobytes of already-localized
/// strings — and the widget only picks the entry for the day it is drawing.
/// Compiled into both the app and the widget target.
struct WidgetSnapshot: Codable, Equatable, Sendable {
    static let appGroup = "group.com.orthodox.calendar"
    static let fileName = "widget_snapshot.json"
    /// How many days the app writes ahead. The widget schedules a week of
    /// entries; the rest keeps it right when the app is not opened for a while.
    static let dayCount = 21
    /// Bumped when the format changes incompatibly; an older file is ignored.
    static let currentVersion = 1

    var version = WidgetSnapshot.currentVersion
    /// `AppLanguage` raw value: sr, ru, en, en_nc.
    let language: String
    let generatedAt: Date
    /// Consecutive days, first one the day the snapshot was written.
    let days: [Day]

    struct Day: Codable, Equatable, Sendable {
        /// `yyyy-MM-dd`, as `DateKeys` writes it.
        let date: String
        /// "Недеља", "Sunday".
        let weekday: String
        /// "27 септембар", "27 сентября".
        let dateLabel: String
        let primary: String
        /// Secondary and tertiary commemorations, a few, each kept short.
        let secondary: [String]
        let isGreatFeast: Bool
        let fastingType: String
        let fastingLabel: String
        let fastingAbbrev: String
        /// The user's slava within the countdown window, counted from this day
        /// (0 = this day is the slava). Serbian only.
        let slava: Slava?
    }

    struct Slava: Codable, Equatable, Sendable {
        let name: String
        let daysUntil: Int
    }

    /// The entry for `key` (`yyyy-MM-dd`), or nil when the snapshot does not
    /// reach that day — the widget then asks the user to open the app instead
    /// of showing another day's saints.
    func day(for key: String) -> Day? {
        days.first { $0.date == key }
    }

    // MARK: - Storage

    static var fileURL: URL? {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: appGroup)?
            .appendingPathComponent(fileName)
    }

    static func read(from url: URL? = WidgetSnapshot.fileURL) -> WidgetSnapshot? {
        guard let url, let data = try? Data(contentsOf: url),
              let snapshot = try? decoder.decode(WidgetSnapshot.self, from: data),
              snapshot.version == currentVersion else { return nil }
        return snapshot
    }

    func write(to url: URL? = WidgetSnapshot.fileURL) throws {
        guard let url else { throw CocoaError(.fileNoSuchFile) }
        try Self.encoder.encode(self).write(to: url, options: .atomic)
    }

    private static var encoder: JSONEncoder {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }

    private static var decoder: JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }
}

/// "за 12 дана", with Serbian's plural forms: 1 дан, 2–4 дана, 5+ дана
/// (21 дан, 22 дана, but 11–14 дана). The slava banner and the widget share it.
enum SlavaCountdownText {
    static func label(_ days: Int) -> String {
        switch days {
        case 0: return "Срећна слава!"
        case 1: return "сутра"
        default:
            let word = (days % 10 == 1 && days % 100 != 11) ? "дан" : "дана"
            return "за \(days) \(word)"
        }
    }
}
