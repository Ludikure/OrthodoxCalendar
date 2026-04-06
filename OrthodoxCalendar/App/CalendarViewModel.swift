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
    var showSearch = false
    var isLoading = false
    var errorMessage: String?

    /// Cached English search index: (month, day, description)
    var englishSearchIndex: [(month: Int, day: Int, text: String)] = []

    private let apiService = OrthocalService()
    private let dataManager = CalendarDataManager()
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

        let locale = localizationManager.language.rawValue

        // Try bundled JSON data first
        let hasBundledData = await dataManager.hasData(year: currentYear, locale: locale)
        if hasBundledData {
            do {
                daysInMonth = try await dataManager.daysForMonth(
                    year: currentYear,
                    month: currentMonth,
                    locale: locale
                )
                isLoading = false
                return
            } catch {
                // Fall through to API-based loading
                errorMessage = error.localizedDescription
            }
        }

        // Fallback: API-based loading (for English locale or years without bundled data)
        mergeEngine = MergeEngine(localization: localizationManager.bundle)
        do {
            let apiDays = try await apiService.fetchMonth(year: currentYear, month: currentMonth)
            daysInMonth = apiDays.enumerated().map { (index, apiDay) in
                let date = makeDate(year: currentYear, month: currentMonth, day: index + 1)
                let dayInfo = mergeEngine.buildDayInfo(apiDay: apiDay, date: date)
                return Self.calendarDay(from: dayInfo)
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
        await buildEnglishSearchIndex()
    }

    func buildEnglishSearchIndex() async {
        var index: [(month: Int, day: Int, text: String)] = []

        // Try bundled English data first
        let hasBundledEnglish = await dataManager.hasData(year: currentYear, locale: "en")
        if hasBundledEnglish {
            do {
                let allDays = try await dataManager.allDays(year: currentYear, locale: "en")
                for day in allDays {
                    var parts: [String] = []
                    for feast in day.feasts {
                        parts.append(feast.name)
                    }
                    let text = parts.joined(separator: "; ")
                    if !text.isEmpty {
                        index.append((month: day.gregorianMonth, day: day.gregorianDay, text: text))
                    }
                }
                englishSearchIndex = index
                return
            } catch {
                // Fall through to API
            }
        }

        // Fallback: API-based index
        for month in 1...12 {
            do {
                let days = try await apiService.fetchMonth(year: currentYear, month: month)
                for (i, apiDay) in days.enumerated() {
                    let day = i + 1
                    var parts: [String] = []
                    parts.append(contentsOf: apiDay.titles)
                    parts.append(contentsOf: apiDay.feasts)
                    parts.append(contentsOf: apiDay.saints)
                    let text = parts.joined(separator: "; ")
                    if !text.isEmpty {
                        index.append((month: month, day: day, text: text))
                    }
                }
            } catch {}
        }
        englishSearchIndex = index
    }

    // MARK: - Private Helpers

    private func buildOfflineMonth(fallback: OfflineFallbackEngine) -> [CalendarDay] {
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
            let dayInfo = fallback.buildDayInfo(for: d)
            return Self.calendarDay(from: dayInfo)
        }
    }

    private func makeDate(year: Int, month: Int, day: Int) -> Date {
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = day
        return Calendar(identifier: .gregorian).date(from: components) ?? Date()
    }

    // MARK: - DayInfo → CalendarDay Conversion (for API fallback path)

    /// Converts a legacy DayInfo to the new CalendarDay model.
    /// Used only when bundled JSON data is unavailable and the API fallback is used.
    private static func calendarDay(from info: DayInfo) -> CalendarDay {
        let calendar = Calendar(identifier: .gregorian)
        let year = calendar.component(.year, from: info.gregorianDate)
        let month = calendar.component(.month, from: info.gregorianDate)
        let day = calendar.component(.day, from: info.gregorianDate)
        let gregorianDateStr = String(format: "%04d-%02d-%02d", year, month, day)

        // Convert weekday from DayInfo convention (0=Sun..6=Sat) to Python convention (0=Mon..6=Sun)
        // DayInfo: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
        // Python:  0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        let pythonDayOfWeek = info.weekday == 0 ? 6 : info.weekday - 1

        // Convert julianDateString from DayInfo "DD/MM" format to CalendarDay "MM-DD" format
        let julianDateStr: String = {
            let parts = info.julianDateString.split(separator: "/")
            if parts.count == 2, let dd = parts.first, let mm = parts.last {
                return "\(mm)-\(dd)"
            }
            return info.julianDateString
        }()

        // Build feasts array from DayInfo
        var feasts: [Feast] = []
        if !info.displayName.isEmpty {
            let importance: String
            if let ft = info.feastType {
                switch ft {
                case .pascha, .great: importance = "great"
                default: importance = ft.rank >= FeastType.major.rank ? "bold" : "normal"
                }
            } else {
                importance = "normal"
            }
            // Create a synthetic Feast via JSON round-trip
            let feastDict: [String: Any] = [
                "name": info.displayName,
                "importance": importance,
                "displayRole": "primary",
                "type": "feast",
                "isSlava": false
            ]
            if let data = try? JSONSerialization.data(withJSONObject: feastDict),
               let feast = try? JSONDecoder().decode(Feast.self, from: data) {
                feasts.append(feast)
            }
        }

        // Build fasting info
        let fastingDict: [String: Any] = [
            "type": info.fastLevel == 0 ? "free" : "strict",
            "label": info.fastLevelDesc,
            "explanation": info.fastExceptionDesc,
            "abbrev": info.fastingAbbrev,
            "icon": ""
        ]
        let fastingInfo: FastingInfo
        if let data = try? JSONSerialization.data(withJSONObject: fastingDict),
           let decoded = try? JSONDecoder().decode(FastingInfo.self, from: data) {
            fastingInfo = decoded
        } else {
            fastingInfo = FastingInfo(type: "free", label: "", explanation: "", abbrev: "", icon: "")
        }

        // Build readings
        var readings: [ScriptureReading] = []
        for r in info.readings {
            let readingDict: [String: Any] = [
                "type": r.book.lowercased().contains("gospel") ? "gospel" : "apostol",
                "book": r.book,
                "reference": r.display,
                "title": r.source
            ]
            if let data = try? JSONSerialization.data(withJSONObject: readingDict),
               let reading = try? JSONDecoder().decode(ScriptureReading.self, from: data) {
                readings.append(reading)
            }
        }

        // Build great feast marker
        let greatFeast: String? = {
            if let ft = info.feastType, ft == .pascha || ft == .great {
                return info.displayName
            }
            return nil
        }()

        // Build reflection from local data if available
        let reflection: Reflection? = {
            if !info.localDescription.isEmpty {
                return Reflection(source: "local", text: info.localDescription)
            }
            return nil
        }()

        // Use JSON round-trip to construct CalendarDay (since all fields are let)
        let calendarDayDict: [String: Any] = [
            "gregorianDate": gregorianDateStr,
            "julianDate": julianDateStr,
            "dayOfWeek": pythonDayOfWeek,
            "paschaDistance": info.paschaDistance ?? 0,
            "feasts": feasts.map { feast -> [String: Any] in
                var d: [String: Any] = [
                    "name": feast.name,
                    "importance": feast.importance,
                    "displayRole": feast.displayRole,
                    "type": feast.type,
                    "isSlava": feast.isSlava
                ]
                if let ctx = feast.liturgicalContext { d["liturgicalContext"] = ctx }
                return d
            },
            "fasting": [
                "type": fastingInfo.type,
                "label": fastingInfo.label,
                "explanation": fastingInfo.explanation,
                "abbrev": fastingInfo.abbrev,
                "icon": fastingInfo.icon
            ],
            "readings": readings.map { r -> [String: Any] in
                var d: [String: Any] = [
                    "type": r.type,
                    "book": r.book,
                    "reference": r.reference
                ]
                if let t = r.title { d["title"] = t }
                if let z = r.zachalo { d["zachalo"] = z }
                return d
            },
            "isFastFreeWeek": false
        ]

        if let data = try? JSONSerialization.data(withJSONObject: calendarDayDict),
           let calendarDay = try? JSONDecoder().decode(CalendarDay.self, from: data) {
            return calendarDay
        }

        // Last resort: minimal CalendarDay
        let minimalDict: [String: Any] = [
            "gregorianDate": gregorianDateStr,
            "julianDate": julianDateStr,
            "dayOfWeek": pythonDayOfWeek,
            "paschaDistance": 0,
            "feasts": [] as [[String: Any]],
            "fasting": ["type": "free", "label": "", "explanation": "", "abbrev": "", "icon": ""],
            "readings": [] as [[String: Any]],
            "isFastFreeWeek": false
        ]
        let data = try! JSONSerialization.data(withJSONObject: minimalDict)
        return try! JSONDecoder().decode(CalendarDay.self, from: data)
    }
}
