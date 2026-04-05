import Foundation

actor OrthocalService {
    private let baseURL = "https://orthocal.info/api/gregorian"
    private let cache = OrthocalCache()
    private let session: URLSession
    private let decoder: JSONDecoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 15
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)
        self.decoder = JSONDecoder()
    }

    // MARK: - Public API

    /// Fetch an entire month in a single request, serving from cache when available
    func fetchMonth(year: Int, month: Int) async throws -> [OrthocalDay] {
        let daysInMonth = daysIn(month: month, year: year)

        // Check cache first
        let cached = await cache.loadMonth(year: year, month: month)
        if cached.count == daysInMonth {
            return cached
        }

        // Fetch entire month in one request
        let url = URL(string: "\(baseURL)/\(year)/\(month)/")!
        let (data, response) = try await session.data(from: url)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw OrthocalError.invalidResponse
        }

        let days = try decoder.decode([OrthocalDay].self, from: data)

        // Cache all days
        for day in days {
            await cache.save(day, year: year, month: month, day: day.day)
        }

        return days.sorted { $0.day < $1.day }
    }

    /// Fetch a single day (for detail view stories, etc.)
    func fetchDay(year: Int, month: Int, day: Int) async throws -> OrthocalDay {
        if let cached = await cache.load(year: year, month: month, day: day) {
            return cached
        }
        let url = URL(string: "\(baseURL)/\(year)/\(month)/\(day)/")!
        let (data, response) = try await session.data(from: url)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw OrthocalError.invalidResponse
        }

        let result = try decoder.decode(OrthocalDay.self, from: data)
        await cache.save(result, year: year, month: month, day: day)
        return result
    }

    /// Smart prefetch: current month first, then adjacent, then rest in background
    func prefetchYear(year: Int, priorityMonth: Int) async {
        let priorityMonths = Set([
            priorityMonth,
            priorityMonth > 1 ? priorityMonth - 1 : 12,
            priorityMonth < 12 ? priorityMonth + 1 : 1
        ])

        for m in priorityMonths.sorted() {
            do { _ = try await fetchMonth(year: year, month: m) } catch {}
        }

        for m in 1...12 where !priorityMonths.contains(m) {
            do { _ = try await fetchMonth(year: year, month: m) } catch {}
        }
    }

    private func daysIn(month: Int, year: Int) -> Int {
        var components = DateComponents()
        components.year = year
        components.month = month
        let calendar = Calendar(identifier: .gregorian)
        guard let date = calendar.date(from: components),
              let range = calendar.range(of: .day, in: .month, for: date) else {
            return 30
        }
        return range.count
    }
}

enum OrthocalError: Error, LocalizedError {
    case invalidResponse
    case noData

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Invalid response from orthocal.info"
        case .noData: return "No data available"
        }
    }
}
