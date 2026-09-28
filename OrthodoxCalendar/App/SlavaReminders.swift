import Foundation
import UserNotifications

/// Local notifications for slavas: a week before and on the morning of the
/// user's own, and the day before each friend's.
///
/// Rescheduled from scratch whenever the settings or the language change and
/// when the app comes to the foreground, for the next two occurrences of each
/// slava — so a reminder still fires a year on if the app isn't opened. Only
/// the Serbian calendar shows slavas, so any other language clears them.
enum SlavaReminders {
    private static let prefix = "slava."

    static func requestAuthorization() async {
        _ = try? await UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound])
    }

    @MainActor private static var last: Task<Void, Never>?

    /// Queues a reschedule behind any still running, so two quick settings
    /// changes can't interleave one's removal with the other's additions.
    @MainActor static func update(_ settings: SlavaStore.Settings, language: AppLanguage) {
        let previous = last
        last = Task {
            await previous?.value
            await reschedule(settings, language: language)
        }
    }

    static func reschedule(_ settings: SlavaStore.Settings, language: AppLanguage) async {
        let center = UNUserNotificationCenter.current()
        let pending = await center.pendingNotificationRequests()
        center.removePendingNotificationRequests(
            withIdentifiers: pending.map(\.identifier).filter { $0.hasPrefix(prefix) })

        guard language == .sr else { return }
        let status = await center.notificationSettings().authorizationStatus
        guard status == .authorized || status == .provisional else { return }

        let now = Date()
        var requests: [UNNotificationRequest] = []

        if let mine = settings.mine {
            for date in nextTwo(mine, after: now) {
                let table = await tableLine(on: date)
                if settings.remindWeekBefore,
                   let fire = fireDate(date, daysBefore: 7, minutes: settings.reminderMinutes), fire > now {
                    var body = "Жито, колач и свећа. Позовите свештеника за освећење водице."
                    if let table { body += " " + table }
                    requests.append(request("mine.week", date, fire,
                                            title: "\(mine.name) за 7 дана", body: body))
                }
                if settings.remindOnDay,
                   let fire = fireDate(date, daysBefore: 0, minutes: settings.reminderMinutes), fire > now {
                    var body = "Данас је \(mine.name)."
                    if let table { body += " " + table }
                    requests.append(request("mine.day", date, fire, title: "Срећна слава!", body: body))
                }
            }
        }

        if settings.remindFriends {
            for friend in settings.friends {
                for date in nextTwo(friend.slava, after: now) {
                    guard let fire = fireDate(date, daysBefore: 1, minutes: settings.reminderMinutes),
                          fire > now else { continue }
                    requests.append(request("friend.\(friend.id.uuidString)", date, fire,
                                            title: "Сутра: слава — \(friend.person)",
                                            body: "\(friend.slava.name), \(longDate(date))."))
                }
            }
        }

        // iOS keeps at most 64 pending local notifications; the soonest matter most.
        for r in requests.sorted(by: fireOrder).prefix(60) {
            try? await center.add(r)
        }
    }

    // MARK: - Helpers

    private static func nextTwo(_ slava: SlavaDay, after now: Date) -> [Date] {
        guard let first = slava.nextOccurrence(onOrAfter: now) else { return [] }
        let dayAfter = ChurchDates.calendar.date(byAdding: .day, value: 1, to: first) ?? first
        return [first] + [slava.nextOccurrence(onOrAfter: dayAfter)].compactMap { $0 }
    }

    private static func fireDate(_ day: Date, daysBefore: Int, minutes: Int) -> Date? {
        let cal = ChurchDates.calendar
        guard let base = cal.date(byAdding: .day, value: -daysBefore, to: cal.startOfDay(for: day)) else { return nil }
        return cal.date(byAdding: .minute, value: minutes, to: base)
    }

    private static func request(_ kind: String, _ slavaDate: Date, _ fire: Date,
                                title: String, body: String) -> UNNotificationRequest {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        let comps = ChurchDates.calendar.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
        let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: false)
        let id = prefix + kind + "." + DateKeys.key(from: slavaDate)
        return UNNotificationRequest(identifier: id, content: content, trigger: trigger)
    }

    private static func fireOrder(_ a: UNNotificationRequest, _ b: UNNotificationRequest) -> Bool {
        let da = (a.trigger as? UNCalendarNotificationTrigger)?.nextTriggerDate() ?? .distantFuture
        let db = (b.trigger as? UNCalendarNotificationTrigger)?.nextTriggerDate() ?? .distantFuture
        return da < db
    }

    /// The fasting rule for the slava table, from a year already on the device
    /// (never a download just to word a reminder).
    private static func tableLine(on date: Date) async -> String? {
        let key = DateKeys.key(from: date)
        guard let year = Int(key.prefix(4)),
              let file = try? await CalendarRepository.shared.load(locale: "sr", year: year, allowNetwork: false),
              let day = file.days[String(key.dropFirst(5))] else { return nil }
        return SlavaText.table(day.fasting.type)
    }

    private static func longDate(_ date: Date) -> String {
        let c = ChurchDates.calendar.dateComponents([.weekday, .month, .day], from: date)
        let weekday = SlavaText.weekdays[((c.weekday ?? 1) - 1) % 7]
        return "\(weekday) \(c.day ?? 1). \(SlavaText.months[((c.month ?? 1) - 1) % 12])"
    }
}

/// Serbian wording shared by the slava views and the reminders.
enum SlavaText {
    static let months = ["јануар", "фебруар", "март", "април", "мај", "јун",
                         "јул", "август", "септембар", "октобар", "новембар", "децембар"]
    /// Indexed like `Calendar.component(.weekday)` minus one: Sunday first.
    static let weekdays = ["недеља", "понедељак", "уторак", "среда", "четвртак", "петак", "субота"]

    /// What the slava table may hold, from the day's fasting level.
    static func table(_ fastingType: String) -> String {
        switch fastingType {
        case "free": return "Трпеза је мрсна."
        case "fish", "fishRoe": return "Трпеза је посна — риба је дозвољена."
        case "hotWithOil": return "Трпеза је посна — на уљу, без рибе."
        case "hotNoOil": return "Трпеза је посна — на води, без уља."
        default: return "Трпеза је посна — строги пост."
        }
    }
}
