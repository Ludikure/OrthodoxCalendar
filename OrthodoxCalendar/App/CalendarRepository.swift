import Foundation

/// Loads a year of calendar data for a given locale, resolving in order:
///   1. in-memory cache (avoid re-decoding)
///   2. app bundle (the current + next year ship bundled — see project.yml)
///   3. on-disk cache (a year fetched earlier, kept for offline use)
///   4. network (the Cloudflare Worker backed by R2)
///
/// Network results are persisted to the Caches directory so that a year stays
/// available offline once it has been viewed. Because the current year is always
/// bundled, "today" never depends on the network.
actor CalendarRepository {
    static let shared = CalendarRepository()

    /// Public API base. Mirrors the bundle data via R2.
    private let baseURL = URL(string: "https://orthodox-calendar-api.ludikure.workers.dev")!

    private var memoryCache: [String: CalendarFile] = [:]
    /// Per-locale deduped bio text pool (bios_<locale>.json), loaded lazily.
    private var biosCache: [String: [String: String]] = [:]

    enum LoadError: Error {
        case offline      // no/failed connection and nothing cached
        case notFound     // server has no data for this locale/year
    }

    private func fileKey(_ locale: String, _ year: Int) -> String {
        "calendar_\(locale)_\(year)"
    }

    /// Resolve a year, fetching and caching from the network only when it is
    /// neither bundled nor already on disk.
    func load(locale: String, year: Int) async throws -> CalendarFile {
        let key = fileKey(locale, year)

        if let cached = memoryCache[key] { return cached }

        if let file = decode(data: bundleData(key)) ?? decode(data: diskData(key)) {
            let resolved = resolveBios(file, locale: locale)
            memoryCache[key] = resolved
            return resolved
        }

        let file = resolveBios(try await fetch(locale: locale, year: year, key: key), locale: locale)
        memoryCache[key] = file
        return file
    }

    /// Fills `SaintBio.text` from the per-locale pool for deduped bundled data.
    /// No-op for API-streamed data (bios already carry text, no `ref`).
    private func resolveBios(_ file: CalendarFile, locale: String) -> CalendarFile {
        let needs = file.days.values.contains { ($0.saintBios ?? []).contains { $0.ref != nil } }
        if !needs { return file }
        let pool = biosPool(locale)
        var days = file.days
        for (key, var day) in days {
            guard let bios = day.saintBios, bios.contains(where: { $0.ref != nil }) else { continue }
            day.saintBios = bios.map { b in
                guard let ref = b.ref, b.text.isEmpty else { return b }
                return SaintBio(title: b.title, text: pool[ref] ?? "", ref: ref)
            }
            days[key] = day
        }
        return CalendarFile(year: file.year, locale: file.locale, generatedBy: file.generatedBy, days: days)
    }

    private func biosPool(_ locale: String) -> [String: String] {
        if let cached = biosCache[locale] { return cached }
        let pool: [String: String] = {
            guard let url = Bundle.main.url(forResource: "bios_\(locale)", withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let map = try? JSONDecoder().decode([String: String].self, from: data) else { return [:] }
            return map
        }()
        biosCache[locale] = pool
        return pool
    }

    // MARK: - Sources

    private func bundleData(_ key: String) -> Data? {
        guard let url = Bundle.main.url(forResource: key, withExtension: "json") else { return nil }
        return try? Data(contentsOf: url)
    }

    private func diskData(_ key: String) -> Data? {
        try? Data(contentsOf: diskURL(key))
    }

    private func fetch(locale: String, year: Int, key: String) async throws -> CalendarFile {
        let url = baseURL.appending(path: "api/\(locale)/\(year)")
        // Generous timeout: the Russian year files are ~50 MB and can take a
        // while to stream over slow mobile connections.
        var request = URLRequest(url: url)
        request.timeoutInterval = 60
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw LoadError.offline
        }

        guard let http = response as? HTTPURLResponse else { throw LoadError.offline }
        guard http.statusCode == 200 else { throw LoadError.notFound }
        guard let file = decode(data: data) else { throw LoadError.notFound }

        // Persist the raw bytes for offline reuse; failure here is non-fatal.
        try? data.write(to: diskURL(key), options: .atomic)
        return file
    }

    // MARK: - Disk cache

    private var cacheDirectory: URL {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        let dir = base.appendingPathComponent("calendar", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private func diskURL(_ key: String) -> URL {
        cacheDirectory.appendingPathComponent("\(key).json")
    }

    private func decode(data: Data?) -> CalendarFile? {
        guard let data else { return nil }
        return try? JSONDecoder().decode(CalendarFile.self, from: data)
    }
}
