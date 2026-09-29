import Foundation
import SwiftUI

/// The user's krsna slava, their friends' slavas, and how to be reminded.
///
/// Serbian only: slava is a Serbian custom, so the views show none of this in
/// other languages and `SlavaReminders` schedules nothing there. Kept on the
/// device in UserDefaults as one JSON value.
@MainActor @Observable
final class SlavaStore {
    struct Settings: Codable, Equatable {
        var mine: SlavaDay?
        var friends: [FriendSlava] = []
        var remindWeekBefore = true
        var remindOnDay = true
        var remindFriends = true
        /// Minutes after midnight the reminders fire at.
        var reminderMinutes = 9 * 60
    }

    private static let defaultsKey = "slava.settings"
    /// How far ahead the month banner starts counting down.
    static let bannerDays = 30

    var settings: Settings {
        didSet {
            guard settings != oldValue else { return }
            if let data = try? JSONEncoder().encode(settings) {
                UserDefaults.standard.set(data, forKey: Self.defaultsKey)
            }
            onChange?()
        }
    }

    /// Called after every change; the app reschedules reminders from it.
    @ObservationIgnored var onChange: (() -> Void)?

    init() {
        if let data = UserDefaults.standard.data(forKey: Self.defaultsKey),
           let saved = try? JSONDecoder().decode(Settings.self, from: data) {
            settings = saved
        } else {
            settings = Settings()
        }
    }

    /// What a calendar row shows for `day`, or nil when no slava falls on it.
    func mark(for day: CalendarDay) -> SlavaMark? {
        var mark = SlavaMark()
        if let mine = settings.mine, mine.matches(day) { mark.isMine = true }
        for friend in settings.friends where friend.slava.matches(day) {
            mark.friendLines.append("\(friend.slava.name) · \(friend.person)")
        }
        return mark.isEmpty ? nil : mark
    }

    /// The user's next slava and how many days away it is (0 = today).
    func countdown(from now: Date = Date()) -> (slava: SlavaDay, date: Date, days: Int)? {
        guard let mine = settings.mine, let date = mine.nextOccurrence(onOrAfter: now) else { return nil }
        let today = ChurchDates.startOfDay(now)
        let days = ChurchDates.calendar.dateComponents([.day], from: today, to: date).day ?? 0
        return (mine, date, days)
    }
}
