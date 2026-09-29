import Foundation
import WidgetKit

/// Builds the widgets' snapshot from loaded calendar days. Pure, so the tests
/// run it against a bundled year.
enum WidgetSnapshotBuilder {
    /// How many days before the slava the countdown shows; the month banner's
    /// window (`SlavaStore.bannerDays`).
    static let slavaWindow = 30
    /// Secondary commemorations kept per day, and the length each is cut to.
    static let maxSecondary = 3
    static let maxSecondaryLength = 90

    /// `WidgetSnapshot.dayCount` consecutive days starting on `start`'s day,
    /// taken from `days` (keyed by `gregorianDate`). Stops at the first day
    /// `days` does not have; nil if it does not have `start` itself.
    static func build(days: [String: CalendarDay], from start: Date, language: AppLanguage,
                      ui: UILabels, mySlava: SlavaDay?, now: Date = Date()) -> WidgetSnapshot? {
        let cal = ChurchDates.calendar
        let first = ChurchDates.startOfDay(start)
        var out: [WidgetSnapshot.Day] = []
        for offset in 0..<WidgetSnapshot.dayCount {
            guard let date = cal.date(byAdding: .day, value: offset, to: first),
                  let day = days[DateKeys.key(from: date)] else { break }
            out.append(entry(day, date: date, language: language, ui: ui, mySlava: mySlava))
        }
        guard !out.isEmpty else { return nil }
        return WidgetSnapshot(language: language.rawValue, generatedAt: now, days: out)
    }

    private static func entry(_ day: CalendarDay, date: Date, language: AppLanguage,
                              ui: UILabels, mySlava: SlavaDay?) -> WidgetSnapshot.Day {
        let weekdays = ui.daysOfWeekFull
        let weekday = weekdays.indices.contains(day.weekdayIndex) ? weekdays[day.weekdayIndex] : ""
        let primary = day.primaryFeast?.name ?? day.feasts.first?.name ?? ""
        let secondary = (day.secondaryFeasts + day.tertiaryFeasts)
            .map(\.name)
            .filter { !$0.isEmpty && $0 != primary }
            .prefix(maxSecondary)
            .map(shorten)
        return WidgetSnapshot.Day(
            date: day.gregorianDate,
            weekday: weekday,
            dateLabel: ui.dayAndMonth(day.gregorianDay, day.gregorianMonth),
            primary: primary,
            secondary: Array(secondary),
            isGreatFeast: day.isGreatFeast,
            fastingType: day.fasting.type,
            fastingLabel: day.fasting.label,
            fastingAbbrev: day.fasting.abbrev ?? "",
            slava: slava(on: date, language: language, mine: mySlava)
        )
    }

    /// The user's slava counted from `date`, within the banner's window.
    /// Serbian only, as everywhere else in the app.
    private static func slava(on date: Date, language: AppLanguage, mine: SlavaDay?) -> WidgetSnapshot.Slava? {
        guard language == .sr, let mine, let next = mine.nextOccurrence(onOrAfter: date),
              let days = ChurchDates.calendar.dateComponents([.day], from: date, to: next).day,
              days <= slavaWindow else { return nil }
        return WidgetSnapshot.Slava(name: mine.name, daysUntil: days)
    }

    private static func shorten(_ name: String) -> String {
        guard name.count > maxSecondaryLength else { return name }
        return String(name.prefix(maxSecondaryLength - 1)).trimmingCharacters(in: .whitespaces) + "…"
    }
}

/// Keeps the widgets' snapshot current: rebuilt at launch, on return to the
/// foreground, when the language or the slava changes, and when the current
/// year finishes loading. Reads years from `CalendarRepository` without the
/// network, so it never downloads anything the calendar has not.
@MainActor
enum WidgetSync {
    private static var task: Task<Void, Never>?

    static func refresh(language: AppLanguage, ui: UILabels, mySlava: SlavaDay?) {
        task?.cancel()
        task = Task {
            let now = Date()
            let cal = ChurchDates.calendar
            let year = cal.component(.year, from: now)
            let locale = language.rawValue
            guard let file = try? await CalendarRepository.shared.load(locale: locale, year: year,
                                                                       allowNetwork: false) else { return }
            var days: [String: CalendarDay] = [:]
            for day in file.days.values { days[day.gregorianDate] = day }
            // Late December: the snapshot runs into next year.
            if let last = cal.date(byAdding: .day, value: WidgetSnapshot.dayCount - 1, to: now),
               cal.component(.year, from: last) != year,
               let next = try? await CalendarRepository.shared.load(locale: locale, year: year + 1,
                                                                    allowNetwork: false) {
                for day in next.days.values { days[day.gregorianDate] = day }
            }
            guard !Task.isCancelled,
                  let snapshot = WidgetSnapshotBuilder.build(days: days, from: now, language: language,
                                                             ui: ui, mySlava: mySlava, now: now) else { return }
            // Unchanged content: leave the widgets alone.
            if let old = WidgetSnapshot.read(), old.language == snapshot.language, old.days == snapshot.days {
                return
            }
            do {
                try snapshot.write()
                WidgetCenter.shared.reloadAllTimelines()
            } catch {
                // No App Group container (entitlement missing): nothing to show.
            }
        }
    }
}
