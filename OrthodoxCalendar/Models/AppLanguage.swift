import Foundation

enum AppLanguage: String, CaseIterable, Codable, Identifiable {
    /// The UserDefaults key the selected language is stored under. Four files
    /// spelled this literal out; one of them drifting would silently reset the
    /// user's language on launch.
    static let defaultsKey = "appLanguage"

    case sr = "sr"
    case ru = "ru"
    case en = "en"
    case en_nc = "en_nc"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .sr: return "Српски"
        case .ru: return "Русский"
        case .en, .en_nc: return "English"
        }
    }

    /// Whose calendar each option follows, under its name in the picker and
    /// under the app title. Two English calendars already exist and a Greek
    /// one may follow, so the language alone no longer says which it is.
    var churchName: String {
        switch self {
        case .sr: return "Српска Православна Црква (СПЦ)"
        case .ru: return "Русская Православная Церковь (РПЦ)"
        case .en: return "ROCOR · Old Calendar"
        case .en_nc: return "OCA · New Calendar"
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
