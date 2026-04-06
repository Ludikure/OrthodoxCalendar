import Foundation

/// Loads and serves new-format calendar data from bundled JSON files.
/// Thread-safe via actor isolation.
actor CalendarDataManager {

    // MARK: - Types

    enum DataError: Error, LocalizedError {
        case fileNotFound(locale: String, year: Int)
        case decodingFailed(underlying: Error)

        var errorDescription: String? {
            switch self {
            case .fileNotFound(let locale, let year):
                return "Calendar data not found for \(locale) \(year)"
            case .decodingFailed(let error):
                return "Failed to decode calendar data: \(error.localizedDescription)"
            }
        }
    }

    // MARK: - State

    /// Cache keyed by "locale_year", e.g. "sr_2026"
    private var cache: [String: CalendarFile] = [:]

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        return d
    }()

    // MARK: - Public API

    /// Returns all CalendarDay entries for the given month, sorted by day.
    func daysForMonth(year: Int, month: Int, locale: String) throws -> [CalendarDay] {
        let file = try loadCalendarFile(year: year, locale: locale)
        let monthPrefix = String(format: "%02d-", month)
        return file.days
            .filter { $0.key.hasPrefix(monthPrefix) }
            .sorted { $0.key < $1.key }
            .map { $0.value }
    }

    /// Returns a single CalendarDay for a specific date, if available.
    func day(year: Int, month: Int, day: Int, locale: String) throws -> CalendarDay? {
        let file = try loadCalendarFile(year: year, locale: locale)
        let key = String(format: "%02d-%02d", month, day)
        return file.days[key]
    }

    /// Returns all days in the calendar year.
    func allDays(year: Int, locale: String) throws -> [CalendarDay] {
        let file = try loadCalendarFile(year: year, locale: locale)
        return file.days
            .sorted { $0.key < $1.key }
            .map { $0.value }
    }

    /// Check whether bundled data exists for a given year/locale.
    func hasData(year: Int, locale: String) -> Bool {
        let filename = "calendar_\(locale)_\(year)"
        let found = Bundle.main.url(forResource: filename, withExtension: "json") != nil
        #if DEBUG
        print("[CalendarDataManager] hasData(\(filename).json) = \(found)")
        #endif
        return found
    }

    /// Clear cache (e.g. on memory warning).
    func clearCache() {
        cache.removeAll()
    }

    // MARK: - Private

    private func loadCalendarFile(year: Int, locale: String) throws -> CalendarFile {
        let cacheKey = "\(locale)_\(year)"
        if let cached = cache[cacheKey] {
            return cached
        }

        let filename = "calendar_\(locale)_\(year)"
        guard let url = Bundle.main.url(forResource: filename, withExtension: "json") else {
            throw DataError.fileNotFound(locale: locale, year: year)
        }

        do {
            let data = try Data(contentsOf: url)
            let file = try decoder.decode(CalendarFile.self, from: data)
            cache[cacheKey] = file
            return file
        } catch let error as DecodingError {
            throw DataError.decodingFailed(underlying: error)
        }
    }
}
