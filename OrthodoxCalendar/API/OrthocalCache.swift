import Foundation

/// File-based cache: one JSON file per month at
/// ~/Library/Caches/OrthodoxCalendar/{year}/{month}.json
actor OrthocalCache {
    private let fileManager = FileManager.default
    private let decoder = JSONDecoder()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.outputFormatting = .prettyPrinted
        return e
    }()

    /// In-memory cache for the current session
    private var memoryCache: [String: [Int: OrthocalDay]] = [:]

    // MARK: - Public

    func load(year: Int, month: Int, day: Int) -> OrthocalDay? {
        let key = monthKey(year: year, month: month)
        if let monthData = memoryCache[key], let dayData = monthData[day] {
            return dayData
        }
        let monthData = loadMonthFromDisk(year: year, month: month)
        if !monthData.isEmpty {
            memoryCache[key] = monthData
        }
        return monthData[day]
    }

    func loadMonth(year: Int, month: Int) -> [OrthocalDay] {
        let key = monthKey(year: year, month: month)
        if let cached = memoryCache[key] {
            return cached.values.sorted { $0.day < $1.day }
        }
        let monthData = loadMonthFromDisk(year: year, month: month)
        if !monthData.isEmpty {
            memoryCache[key] = monthData
        }
        return monthData.values.sorted { $0.day < $1.day }
    }

    func save(_ day: OrthocalDay, year: Int, month: Int, day dayNum: Int) {
        let key = monthKey(year: year, month: month)
        if memoryCache[key] == nil {
            memoryCache[key] = loadMonthFromDisk(year: year, month: month)
        }
        memoryCache[key]?[dayNum] = day
        saveMonthToDisk(year: year, month: month)
    }

    func clearAll() {
        memoryCache.removeAll()
        if let cacheDir = cacheDirectory() {
            try? fileManager.removeItem(at: cacheDir)
        }
    }

    // MARK: - Disk I/O

    private func loadMonthFromDisk(year: Int, month: Int) -> [Int: OrthocalDay] {
        guard let url = monthFileURL(year: year, month: month),
              let data = try? Data(contentsOf: url),
              let days = try? decoder.decode([OrthocalDay].self, from: data) else {
            return [:]
        }
        var dict: [Int: OrthocalDay] = [:]
        for d in days { dict[d.day] = d }
        return dict
    }

    private func saveMonthToDisk(year: Int, month: Int) {
        guard let url = monthFileURL(year: year, month: month),
              let days = memoryCache[monthKey(year: year, month: month)] else { return }

        let sorted = days.values.sorted { $0.day < $1.day }
        guard let data = try? encoder.encode(sorted) else { return }

        let dir = url.deletingLastPathComponent()
        try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        try? data.write(to: url, options: .atomic)
    }

    // MARK: - Paths

    private func cacheDirectory() -> URL? {
        fileManager.urls(for: .cachesDirectory, in: .userDomainMask)
            .first?
            .appendingPathComponent("OrthodoxCalendar", isDirectory: true)
    }

    private func monthFileURL(year: Int, month: Int) -> URL? {
        cacheDirectory()?
            .appendingPathComponent("\(year)", isDirectory: true)
            .appendingPathComponent("\(String(format: "%02d", month)).json")
    }

    private func monthKey(year: Int, month: Int) -> String {
        "\(year)-\(String(format: "%02d", month))"
    }
}
