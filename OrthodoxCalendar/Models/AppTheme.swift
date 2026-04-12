import SwiftUI

enum AppTheme: String, CaseIterable, Identifiable, Codable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .light:  return .light
        case .dark:   return .dark
        }
    }

    func displayName(for language: AppLanguage) -> String {
        switch self {
        case .system:
            switch language {
            case .sr: return "Системски"
            case .ru: return "Системная"
            case .en, .en_nc: return "System"
            }
        case .light:
            switch language {
            case .sr: return "Светла"
            case .ru: return "Светлая"
            case .en, .en_nc: return "Light"
            }
        case .dark:
            switch language {
            case .sr: return "Тамна"
            case .ru: return "Тёмная"
            case .en, .en_nc: return "Dark"
            }
        }
    }

    static func sectionTitle(for language: AppLanguage) -> String {
        switch language {
        case .sr: return "Тема"
        case .ru: return "Тема"
        case .en, .en_nc: return "Theme"
        }
    }
}
