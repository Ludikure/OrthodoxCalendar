import Foundation

enum AppLanguage: String, CaseIterable, Codable, Identifiable {
    case sr = "sr"
    case ru = "ru"
    case en = "en"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .sr: return "Српски"
        case .ru: return "Русский"
        case .en: return "English"
        }
    }
}
