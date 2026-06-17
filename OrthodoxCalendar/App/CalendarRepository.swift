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
            memoryCache[key] = file
            return file
        }

        let file = try await fetch(locale: locale, year: year, key: key)
        memoryCache[key] = file
        return file
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
