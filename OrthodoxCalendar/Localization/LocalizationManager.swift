import Foundation
import SwiftUI

/// English New Testament translation choice. The Old Testament is always the
/// Septuagint (Brenton), so this only affects NT readings.
enum BibleTranslation: String, CaseIterable, Identifiable {
    case kjv
    case web

    var id: String { rawValue }
    var displayName: String {
        switch self {
        case .kjv: return "King James Version"
        case .web: return "World English Bible"
        }
    }
}

@MainActor @Observable
final class LocalizationManager {
    private(set) var bundle: LocalizationBundle
    var language: AppLanguage {
        didSet {
            bundle = Self.loadBundle(for: language)
            UserDefaults.standard.set(language.rawValue, forKey: "appLanguage")
        }
    }

    var theme: AppTheme {
        didSet {
            UserDefaults.standard.set(theme.rawValue, forKey: "appTheme")
        }
    }

    /// English NT translation (KJV/WEB). Affects English locales only.
    var bibleTranslation: BibleTranslation {
        didSet {
            UserDefaults.standard.set(bibleTranslation.rawValue, forKey: "bibleTranslation")
        }
    }

    init() {
        let saved = UserDefaults.standard.string(forKey: "appLanguage")
            .flatMap(AppLanguage.init(rawValue:)) ?? .sr
        self.language = saved
        self.bundle = Self.loadBundle(for: saved)
        self.theme = UserDefaults.standard.string(forKey: "appTheme")
            .flatMap(AppTheme.init(rawValue:)) ?? .system
        self.bibleTranslation = UserDefaults.standard.string(forKey: "bibleTranslation")
            .flatMap(BibleTranslation.init(rawValue:)) ?? .kjv
    }

    private static func loadBundle(for language: AppLanguage) -> LocalizationBundle {
        guard let url = Bundle.main.url(forResource: language.localizationFile, withExtension: "json",
                                         subdirectory: nil),
              let data = try? Data(contentsOf: url),
              let bundle = try? JSONDecoder().decode(LocalizationBundle.self, from: data) else {
            // Fallback to Serbian if the requested locale file is missing
            if language != .sr,
               let fallbackUrl = Bundle.main.url(forResource: "sr", withExtension: "json"),
               let fallbackData = try? Data(contentsOf: fallbackUrl),
               let fallbackBundle = try? JSONDecoder().decode(LocalizationBundle.self, from: fallbackData) {
                return fallbackBundle
            }
            fatalError("Missing localization file: \(language.localizationFile).json")
        }
        return bundle
    }

    // MARK: - Convenience

    var ui: UILabels { bundle.ui }

    func localizedMonthName(_ month: Int) -> String {
        guard month >= 1, month <= 12 else { return "" }
        return bundle.ui.months[month - 1]
    }

    func localizedDayOfWeek(_ weekday: Int) -> String {
        guard weekday >= 0, weekday <= 6 else { return "" }
        return bundle.ui.daysOfWeek[weekday]
    }

    func localizedFastingDesc(_ apiDesc: String) -> String {
        // Map API fasting descriptions to localized versions
        let mapping: [(key: String, uiKey: String)] = [
            ("No Fast", "noFast"),
            ("Fast Free", "fastFree"),
            ("Strict Fast", "strict"),
            ("Fish Allowed", "fish"),
            ("Oil Allowed", "oil"),
            ("Wine Allowed", "wine"),
            ("Fast Day", "strict")
        ]
        for (apiKey, uiKey) in mapping {
            if apiDesc.contains(apiKey), let localized = bundle.ui.fastingTypes[uiKey] {
                return localized
            }
        }
        return apiDesc
    }
}
