import Foundation
import UserNotifications

/// Local notifications for name days: the morning of the user's own, and on
/// the day (optionally also the day before) of each friend's.
///
/// Same scheduling as `SlavaReminders`: rebuilt from scratch whenever the
/// settings or the language change and when the app comes to the foreground,
/// for the next two occurrences of each name day. Only the Russian calendar
/// shows name days, so any other language clears them.
enum NameDayReminders {
    private static let prefix = "imeniny."

    @MainActor private static var last: Task<Void, Never>?

    /// Queues a reschedule behind any still running.
    @MainActor static func update(_ settings: NameDayStore.Settings, language: AppLanguage) {
        let previous = last
        last = Task {
            await previous?.value
            await reschedule(settings, language: language)
        }
    }

    static func reschedule(_ settings: NameDayStore.Settings, language: AppLanguage) async {
        let center = UNUserNotificationCenter.current()
        let pending = await center.pendingNotificationRequests()
        center.removePendingNotificationRequests(
            withIdentifiers: pending.map(\.identifier).filter { $0.hasPrefix(prefix) })

        guard language == .ru else { return }
        let status = await center.notificationSettings().authorizationStatus
        guard status == .authorized || status == .provisional else { return }

        let now = Date()
        var requests: [UNNotificationRequest] = []

        if let mine = settings.mine, settings.remindOnDay {
            for date in nextTwo(mine, after: now) {
                guard let fire = fireDate(date, daysBefore: 0, minutes: settings.reminderMinutes),
                      fire > now else { continue }
                requests.append(request("mine.day", date, fire, title: "С днём ангела!",
                                        body: "Сегодня ваши именины — память: \(mine.title)."))
            }
        }

        for friend in settings.friends {
            for date in nextTwo(friend.nameDay, after: now) {
                let who = friend.displayName
                if settings.remindFriends,
                   let fire = fireDate(date, daysBefore: 0, minutes: settings.reminderMinutes), fire > now {
                    requests.append(request("friend.\(friend.id.uuidString).day", date, fire,
                                            title: "Сегодня именины: \(who)",
                                            body: "\(friend.nameDay.churchName) — не забудьте поздравить."))
                }
                if settings.remindFriendsDayBefore,
                   let fire = fireDate(date, daysBefore: 1, minutes: settings.reminderMinutes), fire > now {
                    requests.append(request("friend.\(friend.id.uuidString).eve", date, fire,
                                            title: "Завтра именины: \(who)",
                                            body: "\(friend.nameDay.churchName), \(longDate(date))."))
                }
            }
        }

        // iOS keeps at most 64 pending local notifications; the soonest matter most.
        for r in requests.sorted(by: fireOrder).prefix(60) {
            try? await center.add(r)
        }
    }

    // MARK: - Helpers

    private static func nextTwo(_ nameDay: NameDayChoice, after now: Date) -> [Date] {
        guard let first = nameDay.nextOccurrence(onOrAfter: now) else { return [] }
        let dayAfter = ChurchDates.calendar.date(byAdding: .day, value: 1, to: first) ?? first
        return [first] + [nameDay.nextOccurrence(onOrAfter: dayAfter)].compactMap { $0 }
    }

    private static func fireDate(_ day: Date, daysBefore: Int, minutes: Int) -> Date? {
        let cal = ChurchDates.calendar
        guard let base = cal.date(byAdding: .day, value: -daysBefore, to: cal.startOfDay(for: day)) else { return nil }
        return cal.date(byAdding: .minute, value: minutes, to: base)
    }

    private static func request(_ kind: String, _ date: Date, _ fire: Date,
                                title: String, body: String) -> UNNotificationRequest {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        let comps = ChurchDates.calendar.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
        let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)
        let id = prefix + kind + "." + DateKeys.key(from: date)
        return UNNotificationRequest(identifier: id, content: content, trigger: trigger)
    }

    private static func fireOrder(_ a: UNNotificationRequest, _ b: UNNotificationRequest) -> Bool {
        let da = (a.trigger as? UNCalendarNotificationTrigger)?.nextTriggerDate() ?? .distantFuture
        let db = (b.trigger as? UNCalendarNotificationTrigger)?.nextTriggerDate() ?? .distantFuture
        return da < db
    }

    /// "четверг, 25 января".
    static func longDate(_ date: Date) -> String {
        let c = ChurchDates.calendar.dateComponents([.weekday, .month, .day], from: date)
        let weekday = weekdays[((c.weekday ?? 1) - 1) % 7]
        return "\(weekday), \(c.day ?? 1) \(monthsGenitive[((c.month ?? 1) - 1) % 12])"
    }

    static let monthsGenitive = ["января", "февраля", "марта", "апреля", "мая", "июня",
                                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    /// Sunday first, like `Calendar.component(.weekday)` minus one.
    static let weekdays = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
}
