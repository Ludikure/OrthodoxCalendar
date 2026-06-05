import Foundation
import SwiftUI

@MainActor @Observable
final class CalendarViewModel {
    static let minYear = 2024
    static let maxYear = 2030

    var currentMonth: Int
    var currentYear: Int
    var daysInMonth: [CalendarDay] = []
    var selectedDay: CalendarDay?
    var scrollToTodayTrigger = false
    var scrollToDay: Int? = nil
    var navigateToDay: Int? = nil
    var viewMode: ViewMode = .list
    var showSearch = false

    enum ViewMode { case list, grid }
    var showDatePicker = false
    var isLoading = false
    var errorMessage: String?
    /// True when the failure was a connectivity problem (vs. data genuinely absent).
    var isOffline = false
    private(set) var loadedLocale: String = ""
    /// The full year file currently loaded, reused for search across the same year.
    private(set) var loadedFile: CalendarFile?

    private var loadTask: Task<Void, Never>?

    init() {
        let cal = Calendar(identifier: .gregorian)
        let now = Date()
        self.currentMonth = cal.component(.month, from: now)
        self.currentYear = cal.component(.year, from: now)
    }

    func loadMonth() {
        let locale = UserDefaults.standard.string(forKey: "appLanguage") ?? "sr"
        loadData(locale: locale, month: currentMonth, year: currentYear)
    }

    func forceReload(locale: String) {
        loadData(locale: locale, month: currentMonth, year: currentYear)
    }

    private func loadData(locale: String, month: Int, year: Int) {
        // A year that is already loaded (bundled or cached in memory) resolves on
        // the first await without flashing a spinner; only an uncached year that
        // needs a network fetch shows the loading state.
        loadTask?.cancel()
        isLoading = true
        errorMessage = nil
        isOffline = false

        loadTask = Task { [weak self] in
            do {
                let file = try await CalendarRepository.shared.load(locale: locale, year: year)
                guard let self, !Task.isCancelled else { return }
                self.apply(file: file, locale: locale, month: month)
            } catch {
                guard let self, !Task.isCancelled else { return }
                self.isOffline = (error as? CalendarRepository.LoadError) == .offline
                self.errorMessage = "Unable to load \(year)"
                self.daysInMonth = []
                self.loadedFile = nil
                self.isLoading = false
            }
        }
    }

    private func apply(file: CalendarFile, locale: String, month: Int) {
        loadedFile = file
        let prefix = String(format: "%02d-", month)
        daysInMonth = file.days
            .filter { $0.key.hasPrefix(prefix) }
            .sorted { $0.key < $1.key }
            .map { $0.value }
        loadedLocale = locale
        isLoading = false
    }

    func goToToday() {
        let cal = Calendar(identifier: .gregorian)
        let now = Date()
        currentMonth = cal.component(.month, from: now)
        currentYear = cal.component(.year, from: now)
        scrollToTodayTrigger.toggle()
    }
}
