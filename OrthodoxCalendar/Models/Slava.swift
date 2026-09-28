import Foundation

/// When a slava falls: on a fixed church (Julian) date, or a set number of days
/// from Pascha. Stored this way — never as a civil date — so it lands on the
/// right day in every year, bundled or downloaded, without touching the data.
enum SlavaAnchor: Codable, Hashable, Sendable {
    case julian(month: Int, day: Int)
    case pascha(offset: Int)
}

/// A slava a family keeps: what people call it ("Никољдан"), the saint or
/// feast it honours, and when it falls.
struct SlavaDay: Codable, Hashable, Identifiable, Sendable {
    let name: String
    let saint: String
    let anchor: SlavaAnchor

    init(_ name: String, _ saint: String, _ anchor: SlavaAnchor) {
        self.name = name
        self.saint = saint
        self.anchor = anchor
    }

    var id: String {
        switch anchor {
        case .julian(let m, let d): return String(format: "j%02d-%02d:", m, d) + name
        case .pascha(let o): return "p\(o):" + name
        }
    }

    var isMoveable: Bool {
        if case .pascha = anchor { return true }
        return false
    }

    /// Whether `day` is this slava. Reads the church date and Pascha distance
    /// the data already carries, so it agrees with the calendar on screen.
    func matches(_ day: CalendarDay) -> Bool {
        switch anchor {
        case .pascha(let offset):
            return day.paschaDistance == offset
        case .julian(let m, let d):
            let key = String(format: "%02d-%02d", m, d)
            if day.julianDate == key { return true }
            // Julian February 29 only exists every fourth year; in the others
            // its commemorations are kept on the 28th.
            if m == 2, d == 29, day.julianDate == "02-28",
               let year = Int(day.gregorianDate.prefix(4)), !ChurchDates.isJulianLeap(year) {
                return true
            }
            return false
        }
    }

    /// The first day this slava falls on, on or after `start`'s day.
    func nextOccurrence(onOrAfter start: Date) -> Date? {
        let from = ChurchDates.startOfDay(start)
        let year = ChurchDates.calendar.component(.year, from: from)
        for y in (year - 1)...(year + 1) {
            guard let date = occurrence(churchYear: y), date >= from else { continue }
            return date
        }
        return nil
    }

    /// This slava's date in church year `year` (Pascha's year, or the Julian
    /// year of a fixed date — Christmas of Julian 2026 is 7 January 2027).
    func occurrence(churchYear year: Int) -> Date? {
        switch anchor {
        case .pascha(let offset):
            guard let pascha = Paschalion.pascha(year: year) else { return nil }
            return ChurchDates.calendar.date(byAdding: .day, value: offset, to: pascha)
        case .julian(let m, let d):
            return ChurchDates.gregorian(fromJulianYear: year, month: m, day: d)
        }
    }
}

/// Another family's slava, so the user doesn't miss the ones they visit.
struct FriendSlava: Codable, Hashable, Identifiable, Sendable {
    var id = UUID()
    var person: String
    var slava: SlavaDay
}

/// What a calendar row shows about slavas on its day.
struct SlavaMark: Equatable, Sendable {
    /// The user's own slava falls here.
    var isMine = false
    /// "Андрејевдан · слава Петровића", one per friend whose slava falls here.
    var friendLines: [String] = []

    var isEmpty: Bool { !isMine && friendLines.isEmpty }
}
