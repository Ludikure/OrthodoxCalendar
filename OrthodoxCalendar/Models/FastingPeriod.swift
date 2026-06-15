import Foundation

/// A day's place within a named fasting season (Great Lent, Nativity Fast, etc.).
/// `dayIndex` is 1-based; `total` is the length of the contiguous run.
struct FastingPeriodInfo: Equatable, Sendable {
    let code: String
    let start: String          // gregorianDate "yyyy-MM-dd"
    let end: String
    let dayIndex: Int
    let total: Int
    /// False when the run touches the edge of the available data, so its true
    /// start/end (and index/total) may extend beyond what we loaded — e.g. the
    /// Nativity Fast spanning Dec into next year's file. Callers then show the
    /// season name only, not a misleading "Day X of Y".
    let complete: Bool
}

/// Resolves the named fasting seasons carried by `CalendarDay.fastingPeriod`.
///
/// The data tags days with snake_case codes (`great_lent`, …) while the
/// localization bundle keys its display names by the canonical English label,
/// so we bridge the two here. Mirrors the Android implementation.
enum FastingPeriods {

    /// Data code -> canonical key used in `LocalizationBundle.fastingPeriodNames`.
    private static let codeToKey: [String: String] = [
        "great_lent": "Great Lent",
        "apostles_fast": "Apostles' Fast",
        "dormition_fast": "Dormition Fast",
        "nativity_fast": "Nativity Fast"
    ]

    static func displayName(_ code: String, names: [String: String]) -> String {
        let key = codeToKey[code]
            ?? code.split(separator: "_").map { $0.capitalized }.joined(separator: " ")
        return names[key] ?? key
    }

    /// Localized "Day X of Y" label.
    static func dayLabel(_ language: AppLanguage, index: Int, total: Int) -> String {
        switch language {
        case .sr: return "Дан \(index) од \(total)"
        case .ru: return "День \(index) из \(total)"
        case .en, .en_nc: return "Day \(index) of \(total)"
        }
    }

    /// Compact "23 Feb – 11 Apr" range, using the localized month names.
    static func dateRange(_ info: FastingPeriodInfo, months: [String]) -> String {
        func fmt(_ iso: String) -> String {
            let parts = iso.split(separator: "-")
            guard parts.count == 3, let m = Int(parts[1]), let d = Int(parts[2]) else { return "" }
            let name = (m >= 1 && m <= months.count) ? String(months[m - 1].prefix(3)) : ""
            return "\(d) \(name)"
        }
        return "\(fmt(info.start)) – \(fmt(info.end))"
    }

    /// Maps each in-season day (by `gregorianDate`) to the contiguous run it sits
    /// in. `days` should be the widest range available (a full year, plus the
    /// neighbour when a season straddles the year boundary), in any order; runs
    /// are broken by a gap in dates or a change of period code.
    static func computeSpans(_ days: [CalendarDay]) -> [String: FastingPeriodInfo] {
        let allDates = days.map { $0.gregorianDate }
        let minDate = allDates.min()
        let maxDate = allDates.max()

        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        fmt.calendar = cal
        fmt.timeZone = cal.timeZone

        let sorted = days.filter { $0.fastingPeriod != nil }
            .sorted { $0.gregorianDate < $1.gregorianDate }
        var result: [String: FastingPeriodInfo] = [:]
        var i = 0
        while i < sorted.count {
            let code = sorted[i].fastingPeriod!
            var j = i
            while j + 1 < sorted.count {
                let next = sorted[j + 1]
                let consecutive: Bool = {
                    guard let cur = fmt.date(from: sorted[j].gregorianDate),
                          let nxt = fmt.date(from: next.gregorianDate) else { return false }
                    return cal.dateComponents([.day], from: cur, to: nxt).day == 1
                }()
                if next.fastingPeriod == code && consecutive { j += 1 } else { break }
            }
            let run = Array(sorted[i...j])
            let start = run.first!.gregorianDate
            let end = run.last!.gregorianDate
            let complete = start != minDate && end != maxDate
            for (idx, d) in run.enumerated() {
                result[d.gregorianDate] = FastingPeriodInfo(
                    code: code, start: start, end: end,
                    dayIndex: idx + 1, total: run.count, complete: complete
                )
            }
            i = j + 1
        }
        return result
    }
}
