import Foundation

struct LocalizationBundle: Codable, Sendable {
    let language: String
    let displayName: String
    let script: String
    let ui: UILabels
    let feastNames: [String: String]
    let extraFeasts: [ExtraFeast]
    let feastTypeOverrides: [String: String]
    let fastingPeriodNames: [String: String]
}

struct UILabels: Codable, Sendable {
    let appTitle: String
    let months: [String]
    let daysOfWeek: [String]
    let daysOfWeekFull: [String]
    let julianLabel: String
    let fastingLabel: String
    let readingsLabel: String
    let commemorationsLabel: String
    let settingsLabel: String
    let todayLabel: String
    let feastTypes: [String: String]
    let fastingTypes: [String: String]
    // On-demand year loading (optional so older localization files still decode).
    let loadingLabel: String?
    let offlineMessage: String?
    // Forced-update gate.
    let updateRequiredTitle: String?
    let updateRequiredMessage: String?
    let updateButton: String?
    // Month names as they read after a day number ("19 декабря"). Only Russian
    // declines them; where absent, `months` is used as it is.
    let monthsGenitive: [String]?
}

extension UILabels {
    /// A day with its month: "19 декабря", "19 December". Android's
    /// `UILabels.dayAndMonth` is the same function; keep them in step.
    func dayAndMonth(_ day: Int, _ month: Int) -> String {
        let names = monthsGenitive ?? months
        guard month >= 1, month <= names.count else { return "\(day)" }
        return "\(day) \(names[month - 1])"
    }
}

struct ExtraFeast: Codable, Sendable {
    let julianMonth: Int
    let julianDay: Int
    let name: String
    let type: String
    let description: String?
}
