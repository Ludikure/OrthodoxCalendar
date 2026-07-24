import Foundation

/// Loads a year of calendar data for a given locale.
///
/// Bundled years (the window in `project.yml`'s Localization folder) resolve
/// offline, exactly as before. Years outside the bundle come from the v2
/// archive on the Cloudflare Worker (deduplicated files, 2024-2099) and are
/// cached on disk permanently, so each is downloaded at most once. Large text
/// (saint bios + scripture readings) lives in a per-locale `texts_<locale>`
/// pool keyed by content hash; bundled and downloaded files alike reference
/// it. `/api/config`'s `dataRevision` invalidates the disk cache when the
/// archive is regenerated. Mirror of Android `CalendarRepository`.
actor CalendarRepository {
    static let shared = CalendarRepository()

    private var memoryCache: [String: CalendarFile] = [:]
    /// Per-locale deduped text pool (texts_<locale>.json), loaded lazily.
    private var textsCache: [String: [String: String]] = [:]
    /// Coalesces concurrent loads of the same year (e.g. the visible year and
    /// a season-span neighbour) into one bundle-read or download.
    private var inFlight: [String: Task<CalendarFile, Error>] = [:]
    /// Config revision is checked at most once per app run, and only on the
    /// network path — bundled years never touch the network.
    private var revisionChecked = false

    private static let apiBase = "https://orthodox-calendar-api.ludikure.workers.dev/api/v2"
    private static let revisionKey = "cachedDataRevision"

    enum LoadError: Error {
        case offline      // connectivity problem; retry may succeed
        case notFound     // no data exists for this locale/year
    }

    private func fileKey(_ locale: String, _ year: Int) -> String {
        "calendar_\(locale)_\(year)"
    }

    /// Resolve a year: memory → bundle → disk cache → network (cached to disk).
    ///
    /// `allowNetwork: false` stops after the disk cache — used for neighbour
    /// years in season-span computation, which must never block a month render
    /// on a download. Cache-only loads bypass `inFlight` (nothing to coalesce).
    func load(locale: String, year: Int, allowNetwork: Bool = true) async throws -> CalendarFile {
        let key = fileKey(locale, year)
        if let cached = memoryCache[key] { return cached }
        if allowNetwork, let running = inFlight[key] { return try await running.value }

        let task = Task<CalendarFile, Error> {
            let raw: CalendarFile
            if let file = decode(data: bundleData(key)) {
                raw = file
            } else if let file = decode(data: diskData(key)) {
                raw = file
            } else if allowNetwork {
                let data = try await download(locale: locale, year: year)
                guard let file = decode(data: data) else { throw LoadError.notFound }
                writeDiskData(key, data)
                raw = file
            } else {
                throw LoadError.notFound
            }
            let resolved = resolveText(raw, locale: locale)
            memoryCache[key] = resolved
            return resolved
        }
        if allowNetwork { inFlight[key] = task }
        defer { if allowNetwork { inFlight[key] = nil } }
        return try await task.value
    }

    // MARK: - Network

    private func download(locale: String, year: Int) async throws -> Data {
        guard let url = URL(string: "\(Self.apiBase)/\(locale)/\(year)") else {
            throw LoadError.notFound
        }
        await checkRevisionOnce()
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await URLSession.shared.data(from: url)
        } catch {
            throw LoadError.offline
        }
        guard let http = response as? HTTPURLResponse else { throw LoadError.offline }
        switch http.statusCode {
        case 200: return data
        case 404, 400: throw LoadError.notFound
        default: throw LoadError.offline
        }
    }

    /// Drops the disk cache when the server's archive revision moves past the
    /// one our cached files were downloaded under. Fails open: no connectivity
    /// or a malformed config leaves the cache as is.
    private func checkRevisionOnce() async {
        guard !revisionChecked else { return }
        revisionChecked = true
        guard let url = URL(string: "https://orthodox-calendar-api.ludikure.workers.dev/api/config"),
              let (data, _) = try? await URLSession.shared.data(from: url),
              let config = try? JSONDecoder().decode(WorkerConfig.self, from: data),
              let revision = config.dataRevision else { return }
        let stored = UserDefaults.standard.integer(forKey: Self.revisionKey)
        if stored != 0 && stored != revision {
            try? FileManager.default.removeItem(at: Self.cacheDirectory)
        }
        UserDefaults.standard.set(revision, forKey: Self.revisionKey)
    }

    private struct WorkerConfig: Decodable {
        let dataRevision: Int?
    }

    // MARK: - Disk cache

    private static let cacheDirectory: URL = {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("CalendarCache", isDirectory: true)
    }()

    private func diskData(_ key: String) -> Data? {
        try? Data(contentsOf: Self.cacheDirectory.appendingPathComponent("\(key).json"))
    }

    private func writeDiskData(_ key: String, _ data: Data) {
        let fm = FileManager.default
        var dir = Self.cacheDirectory
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
        // Re-downloadable data: keep it out of iCloud/iTunes backups.
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? dir.setResourceValues(values)
        try? data.write(to: dir.appendingPathComponent("\(key).json"), options: .atomic)
    }

    // MARK: - Text pool resolution

    /// Fills bio + reading text from the per-locale pool for deduped data.
    private func resolveText(_ file: CalendarFile, locale: String) -> CalendarFile {
        let needs = file.days.values.contains { d in
            (d.saintBios ?? []).contains { $0.ref != nil } ||
                d.readings.contains { $0.textRef != nil || $0.textWebRef != nil }
        }
        if !needs { return file }
        let pool = textsPool(locale)
        var days = file.days
        for (key, var day) in days {
            if let bios = day.saintBios {
                day.saintBios = bios.map { b in
                    guard let ref = b.ref, b.text.isEmpty else { return b }
                    return SaintBio(title: b.title, text: pool[ref] ?? "", ref: ref)
                }
            }
            day.readings = day.readings.map { r in
                var out = r
                if let ref = r.textRef, r.text == nil { out.text = pool[ref] }
                if let ref = r.textWebRef, r.textWeb == nil { out.textWeb = pool[ref] }
                return out
            }
            days[key] = day
        }
        return CalendarFile(year: file.year, locale: file.locale, generatedBy: file.generatedBy, days: days)
    }

    private func textsPool(_ locale: String) -> [String: String] {
        if let cached = textsCache[locale] { return cached }
        let pool: [String: String] = {
            guard let url = Bundle.main.url(forResource: "texts_\(locale)", withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let map = try? JSONDecoder().decode([String: String].self, from: data) else { return [:] }
            return map
        }()
        textsCache[locale] = pool
        return pool
    }

    private func bundleData(_ key: String) -> Data? {
        guard let url = Bundle.main.url(forResource: key, withExtension: "json") else { return nil }
        return try? Data(contentsOf: url)
    }

    private func decode(data: Data?) -> CalendarFile? {
        guard let data else { return nil }
        return try? JSONDecoder().decode(CalendarFile.self, from: data)
    }
}
