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
            UserDefaults.standard.set(language.rawValue, forKey: AppLanguage.defaultsKey)
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
        let saved = UserDefaults.standard.string(forKey: AppLanguage.defaultsKey)
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

    /// The month on its own, as a month header shows it. After a day number use
    /// `dayAndMonth`, which declines the month where the language does.
    func localizedMonthName(_ month: Int) -> String {
        guard month >= 1, month <= 12 else { return "" }
        return bundle.ui.months[month - 1]
    }

    func dayAndMonth(_ day: Int, _ month: Int) -> String {
        bundle.ui.dayAndMonth(day, month)
    }

    func localizedDayOfWeek(_ weekday: Int) -> String {
        guard weekday >= 0, weekday <= 6 else { return "" }
        return bundle.ui.daysOfWeek[weekday]
    }

}
