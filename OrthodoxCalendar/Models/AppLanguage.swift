import Foundation

enum AppLanguage: String, CaseIterable, Codable, Identifiable {
    case sr = "sr"
    case en = "en"
    case ru = "ru"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .sr: return "Српски"
        case .en: return "English"
        case .ru: return "Русский"
        }
    }
}
