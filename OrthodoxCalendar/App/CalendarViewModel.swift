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
    var showSearch = false
    var showDatePicker = false
    var isLoading = false
    var errorMessage: String?
    private(set) var loadedLocale: String = ""

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
        isLoading = true
        errorMessage = nil

        let filename = "calendar_\(locale)_\(year)"
        guard let url = Bundle.main.url(forResource: filename, withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let file = try? JSONDecoder().decode(CalendarFile.self, from: data) else {
            errorMessage = "No data for \(locale) \(year)"
            daysInMonth = []
            isLoading = false
            return
        }

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
