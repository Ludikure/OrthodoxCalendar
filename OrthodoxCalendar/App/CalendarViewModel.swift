import Foundation
import SwiftUI

@MainActor @Observable
final class CalendarViewModel {
    var currentMonth: Int
    var currentYear: Int

    var daysInMonth: [DayInfo] = []
    var selectedDay: DayInfo?

    var scrollToTodayTrigger = false
    var isLoading = false
    var errorMessage: String?

    private let apiService = OrthocalService()
    private var localizationManager: LocalizationManager
    private var mergeEngine: MergeEngine

    init(localizationManager: LocalizationManager) {
        let calendar = Calendar(identifier: .gregorian)
        let now = Date()
        self.currentMonth = calendar.component(.month, from: now)
        self.currentYear = calendar.component(.year, from: now)
        self.localizationManager = localizationManager
        self.mergeEngine = MergeEngine(localization: localizationManager.bundle)
    }

    func loadMonth() async {
        isLoading = true
        errorMessage = nil
        mergeEngine = MergeEngine(localization: localizationManager.bundle)

        do {
            let apiDays = try await apiService.fetchMonth(year: currentYear, month: currentMonth)
            daysInMonth = apiDays.map { apiDay in
                let date = makeDate(year: apiDay.year, month: apiDay.month, day: apiDay.day)
                return mergeEngine.buildDayInfo(apiDay: apiDay, date: date)
            }
        } catch {
            let fallback = OfflineFallbackEngine(localization: localizationManager.bundle)
            daysInMonth = buildOfflineMonth(fallback: fallback)
            errorMessage = error.localizedDescription
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

    func startBackgroundPrefetch() async {
        await apiService.prefetchYear(year: currentYear, priorityMonth: currentMonth)
    }

    private func buildOfflineMonth(fallback: OfflineFallbackEngine) -> [DayInfo] {
        let calendar = Calendar(identifier: .gregorian)
        var components = DateComponents()
        components.year = currentYear
        components.month = currentMonth
        guard let date = calendar.date(from: components),
              let range = calendar.range(of: .day, in: .month, for: date) else {
            return []
        }
        return range.map { day in
            components.day = day
            let d = calendar.date(from: components)!
            return fallback.buildDayInfo(for: d)
        }
    }

    private func makeDate(year: Int, month: Int, day: Int) -> Date {
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = day
        return Calendar(identifier: .gregorian).date(from: components) ?? Date()
    }
}
