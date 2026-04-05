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
}

struct ExtraFeast: Codable, Sendable {
    let julianMonth: Int
    let julianDay: Int
    let name: String
    let type: String
    let description: String?
}
