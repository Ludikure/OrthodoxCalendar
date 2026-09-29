import Foundation
import SwiftUI

/// The user's name day (именины), their friends', and how to be reminded.
///
/// Russian only: the views show none of this in other languages and
/// `NameDayReminders` schedules nothing there — just as slavas are Serbian
/// only, so the two never meet on one screen. Kept on the device in
/// UserDefaults as one JSON value.
@MainActor @Observable
final class NameDayStore {
    struct Settings: Codable, Equatable {
        var mine: NameDayChoice?
        var friends: [FriendNameDay] = []
        var remindOnDay = true
        var remindFriends = true
        var remindFriendsDayBefore = false
        /// Let new martyrs decide an automatic name day (azbyka.ru leaves them
        /// out unless asked). A saint chosen by hand is never restricted.
        var includeNewMartyrs = false
        /// Minutes after midnight the reminders fire at.
        var reminderMinutes = 9 * 60
    }

    private static let defaultsKey = "imeniny.settings"
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

    /// What a calendar row shows for `day`, or nil when no name day falls on it.
    func mark(for day: CalendarDay) -> NameDayMark? {
        var mark = NameDayMark()
        if let mine = settings.mine, mine.matches(day) { mark.isMine = true }
        for friend in settings.friends where friend.nameDay.matches(day) {
            mark.friendLines.append("\(friend.displayName) · \(friend.nameDay.churchName)")
        }
        return mark.isEmpty ? nil : mark
    }

    /// The user's next name day and how many days away it is (0 = today).
    func countdown(from now: Date = Date()) -> (nameDay: NameDayChoice, date: Date, days: Int)? {
        guard let mine = settings.mine, let date = mine.nextOccurrence(onOrAfter: now) else { return nil }
        let today = ChurchDates.startOfDay(now)
        let days = ChurchDates.calendar.dateComponents([.day], from: today, to: date).day ?? 0
        return (mine, date, days)
    }
}
