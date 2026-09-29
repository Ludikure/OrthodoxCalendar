import Foundation

/// When to ask for an App Store rating.
///
/// People open this app to check one day, often daily, so launches alone say
/// little; distinct days of use say the app has earned a place. We ask once the
/// app has been opened on `requiredDays` separate days, at most once per app
/// version, and start counting again after each ask. StoreKit decides whether
/// the prompt actually appears (at most three times a year), so a request here
/// is a hint, never a guarantee.
struct ReviewPrompt {
    static let requiredDays = 5

    private let defaults: UserDefaults
    private let version: String

    private enum Key {
        static let lastActiveDay = "reviewPrompt.lastActiveDay"
        static let activeDays = "reviewPrompt.activeDays"
        static let promptedVersion = "reviewPrompt.promptedVersion"
    }

    init(defaults: UserDefaults = .standard,
         version: String = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0") {
        self.defaults = defaults
        self.version = version
    }

    var activeDays: Int { defaults.integer(forKey: Key.activeDays) }

    /// Counts `date`'s calendar day as a day of use; a second call on the same
    /// day counts nothing.
    func recordActive(on date: Date = Date()) {
        let day = DateKeys.key(from: date)
        guard defaults.string(forKey: Key.lastActiveDay) != day else { return }
        defaults.set(day, forKey: Key.lastActiveDay)
        defaults.set(activeDays + 1, forKey: Key.activeDays)
    }

    var shouldPrompt: Bool {
        activeDays >= Self.requiredDays
            && defaults.string(forKey: Key.promptedVersion) != version
    }

    /// Call right after requesting the review.
    func markPrompted() {
        defaults.set(version, forKey: Key.promptedVersion)
        defaults.set(0, forKey: Key.activeDays)
    }
}
