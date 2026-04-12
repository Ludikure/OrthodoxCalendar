import Foundation

enum AppLanguage: String, CaseIterable, Codable, Identifiable {
    case sr = "sr"
    case ru = "ru"
    case en = "en"
    case en_nc = "en_nc"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .sr: return "Српски"
        case .ru: return "Русский"
        case .en: return "English (Old Calendar)"
        case .en_nc: return "English (New Calendar)"
        }
    }

    /// The localization file to load (en_nc shares en.json)
    var localizationFile: String {
        switch self {
        case .en_nc: return "en"
        default: return rawValue
        }
    }
}
