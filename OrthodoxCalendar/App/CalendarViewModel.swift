import Foundation
import SwiftUI

@MainActor @Observable
final class CalendarViewModel {
    var currentMonth: Int
    var currentYear: Int

    var daysInMonth: [CalendarDay] = []
    var selectedDay: CalendarDay?    // For detail sheet (long press)
    var expandedDay: CalendarDay?    // For inline expansion (tap)

    var scrollToTodayTrigger = false
    var scrollToDay: Int? = nil
    var navigateToDay: Int? = nil  // Opens detail view for this day after month loads
    var showSearch = false
    var showDatePicker = false
    var isLoading = false
    var errorMessage: String?

    private let dataManager = CalendarDataManager()
    private var localizationManager: LocalizationManager

    init(localizationManager: LocalizationManager) {
        let calendar = Calendar(identifier: .gregorian)
        let now = Date()
        self.currentMonth = calendar.component(.month, from: now)
        self.currentYear = calendar.component(.year, from: now)
        self.localizationManager = localizationManager
    }

    func loadMonth() async {
        isLoading = true
        errorMessage = nil
        let locale = localizationManager.language.rawValue
        let filename = "calendar_\(locale)_\(currentYear)"

        if let url = Bundle.main.url(forResource: filename, withExtension: "json") {
            do {
                let data = try Data(contentsOf: url)
                let file = try JSONDecoder().decode(CalendarFile.self, from: data)
                let monthPrefix = String(format: "%02d-", currentMonth)
                daysInMonth = file.days
                    .filter { $0.key.hasPrefix(monthPrefix) }
                    .sorted { $0.key < $1.key }
                    .map { $0.value }
            } catch {
                errorMessage = error.localizedDescription
            }
        } else {
            errorMessage = "Calendar data not available for \(currentYear)"
            daysInMonth = []
        }
        isLoading = false
    }

    func goToToday() {
        let calendar = Calendar(identifier: .gregorian)
        let now = Date()
        currentMonth = calendar.component(.month, from: now)
        currentYear = calendar.component(.year, from: now)
        scrollToTodayTrigger.toggle()
    }
}
