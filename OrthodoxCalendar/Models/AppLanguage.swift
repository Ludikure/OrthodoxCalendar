import Foundation

enum AppLanguage: String, CaseIterable, Codable, Identifiable {
    case sr = "sr"
    case ru = "ru"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .sr: return "Српски"
        case .ru: return "Русский"
        }
    }
}
