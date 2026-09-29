import Foundation

/// Loads a year of calendar data for a given locale.
///
/// Bundled years (the window in `project.yml`'s Localization folder) resolve
/// offline. When the archive has been republished since the bundle was built
/// (`/api/config`'s `dataRevision` above `BundledData.revision`), each bundled
/// year is downloaded once in the background, cached like any other, and
/// preferred over the bundle from then on — see `BundledData`. Years outside
/// the bundle come from the v2
/// archive on the Cloudflare Worker (deduplicated files, 2024-2099) and are
/// cached on disk permanently, so each is downloaded at most once. Large text
/// (saint bios + scripture readings) lives in a per-locale `texts_<locale>`
/// pool keyed by content hash; bundled and downloaded files alike reference
/// it. `/api/config`'s `dataRevision` invalidates the disk cache when the
/// archive is regenerated. Mirror of Android `CalendarRepository`.
actor CalendarRepository {
    static let shared = CalendarRepository()

    private var memoryCache: [String: CalendarFile] = [:]
    /// Most-recent-first keys for `memoryCache`. A fully text-resolved year is
    /// tens of MB, and browsing the archive would otherwise keep every year
    /// visited this session resident.
    private var memoryOrder: [String] = []
    private static let memoryLimit = 3
    /// Per-locale deduped text pool (texts_<locale>.json), loaded lazily.
    private var textsCache: [String: [String: String]] = [:]
    /// Coalesces concurrent loads of the same year (e.g. the visible year and
    /// a season-span neighbour) into one bundle-read or download.
    private var inFlight: [String: Task<CalendarFile, Error>] = [:]
    /// Config revision is checked at most once per app run, and only on the
    /// network path — bundled years never touch the network.
    private var revisionChecked = false
    /// The archive revision `/api/config` reported this run, once checked.
    private var serverRevision: Int?
    /// Bundled years whose newer archive copy is being fetched this run.
    private var refreshing: Set<String> = []

    private static let apiBase = "https://orthodox-calendar-api.ludikure.workers.dev/api/v2"
    private static let revisionKey = "cachedDataRevision"

    enum LoadError: Error {
        case offline      // connectivity problem; retry may succeed
        case notFound     // no data exists for this locale/year
    }

    private func fileKey(_ locale: String, _ year: Int) -> String {
        "calendar_\(locale)_\(year)"
    }

    /// Resolve a year: memory → bundle (or its newer archive copy) → disk
    /// cache → network (cached to disk).
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
            if let bundled = bundleData(key) {
                // A bundled year: its archive copy only when that is newer
                // than the bundle; never a network wait (the refresh runs
                // behind, and the next load picks its result up).
                let cached = newerCopy(key)
                if BundledData.source(bundleRevision: BundledData.revision, cachedRevision: cached?.revision) == .cache,
                   let copy = cached, let file = decode(data: copy.data) {
                    raw = file
                } else if let file = decode(data: bundled) {
                    raw = file
                } else {
                    throw LoadError.notFound
                }
                if allowNetwork { refreshBundledYear(locale: locale, year: year) }
            } else if let file = decode(data: diskData(key)) {
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
            remember(key, resolved)
            return resolved
        }
        if allowNetwork { inFlight[key] = task }
        defer { if allowNetwork { inFlight[key] = nil } }
        return try await task.value
    }

    // MARK: - Newer data for bundled years

    /// Fetches a bundled year from the archive when `/api/config` says the
    /// archive is newer than the bundle and no copy at that revision is on disk.
    /// Runs detached from the load that started it: offline, a failed request
    /// or an unchanged revision leave the bundle in use and say nothing.
    private func refreshBundledYear(locale: String, year: Int) {
        let key = fileKey(locale, year)
        guard refreshing.insert(key).inserted else { return }
        Task {
            defer { refreshing.remove(key) }
            await checkRevisionOnce()
            guard BundledData.shouldDownload(bundleRevision: BundledData.revision,
                                             serverRevision: serverRevision,
                                             cachedRevision: newerCopy(key)?.revision),
                  let revision = serverRevision,
                  let data = try? await fetch(locale: locale, year: year),
                  let file = decode(data: data) else { return }
            writeDiskData(BundledData.cacheName(key, revision: revision), data)
            // Loads from here on get the new copy; a year already in memory
            // is swapped too, so the next month rendered from it is fresh.
            if memoryCache[key] != nil { memoryCache[key] = resolveText(file, locale: locale) }
        }
    }

    /// The archive copy of a bundled year on disk, with the revision it was
    /// downloaded at — the highest if several survived.
    private func newerCopy(_ key: String) -> (data: Data, revision: Int)? {
        let names = (try? FileManager.default.contentsOfDirectory(atPath: Self.cacheDirectory.path)) ?? []
        guard let best = names.compactMap({ BundledData.revision(ofCacheName: $0, key: key) }).max(),
              let data = diskData(BundledData.cacheName(key, revision: best)) else { return nil }
        return (data, best)
    }

    // MARK: - Network

    private func download(locale: String, year: Int) async throws -> Data {
        await checkRevisionOnce()
        return try await fetch(locale: locale, year: year)
    }

    private func fetch(locale: String, year: Int) async throws -> Data {
        guard let url = URL(string: "\(Self.apiBase)/\(locale)/\(year)") else {
            throw LoadError.notFound
        }
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
    /// or a malformed config leaves the cache as is. Archive copies of bundled
    /// years go with the rest, so a bump never leaves an older copy preferred:
    /// until the new one lands the bundle is used, and a copy is taken over
    /// the bundle only when its own revision (in its file name) is newer.
    private func checkRevisionOnce() async {
        guard !revisionChecked else { return }
        revisionChecked = true
        guard let url = URL(string: "https://orthodox-calendar-api.ludikure.workers.dev/api/config"),
              let (data, _) = try? await URLSession.shared.data(from: url),
              let config = try? JSONDecoder().decode(WorkerConfig.self, from: data),
              let revision = config.dataRevision else { return }
        serverRevision = revision
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
                // A ref the shipped pool lacks means there is no biography.
                // Keep the entry with empty text rather than dropping it: the
                // views treat empty text as absent, but BioMatcher counts the
                // day's bios, and shrinking a two-bio day to one can fire its
                // single-bio fallback, which hands the survivor to the first
                // fixed feast without scoring it — a wrong biography is worse
                // than a missing one.
                day.saintBios = bios.map { b in
                    guard let ref = b.ref, b.text.isEmpty else { return b }
                    guard let text = pool[ref], !text.isEmpty else {
                        #if DEBUG
                        print("texts_\(locale): missing ref \(ref) for \(b.title)")
                        #endif
                        return SaintBio(title: b.title, text: "", ref: ref)
                    }
                    return SaintBio(title: b.title, text: text, ref: ref)
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

    /// The pool file a locale resolves against. en and en_nc show the same bios
    /// and the same scripture text, so they share `texts_en.json` — bundling a
    /// second, byte-identical copy cost 8.6 MB.
    private static func poolName(_ locale: String) -> String {
        locale == "en_nc" ? "en" : locale
    }

    /// Records a year as most recently used and evicts the coldest beyond the limit.
    private func remember(_ key: String, _ file: CalendarFile) {
        memoryCache[key] = file
        memoryOrder.removeAll { $0 == key }
        memoryOrder.insert(key, at: 0)
        while memoryOrder.count > Self.memoryLimit, let oldest = memoryOrder.popLast() {
            memoryCache.removeValue(forKey: oldest)
        }
    }

    private func textsPool(_ locale: String) -> [String: String] {
        let name = Self.poolName(locale)
        if let cached = textsCache[name] { return cached }
        let pool: [String: String] = {
            guard let url = Bundle.main.url(forResource: "texts_\(name)", withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let map = try? JSONDecoder().decode([String: String].self, from: data) else { return [:] }
            return map
        }()
        textsCache[name] = pool
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

/// Which copy of a bundled year to open: the bundle, or an archive copy
/// downloaded because the archive was republished after the bundle was built.
///
/// `revision` is the archive `dataRevision` (worker/config.json) the bundled
/// calendar_*.json files were generated for. RELEASE CHECKLIST: when regenerated
/// years are copied into OrthodoxCalendar/Localization/, set it to the
/// `dataRevision` they are published under — otherwise installs of the new
/// version would re-download years their bundle already has.
enum BundledData {
    static let revision = 10

    enum Source: Equatable { case bundle, cache }

    /// The archive copy wins only when it is newer than the bundle: a copy from
    /// before a newer app shipped (its revision at or below the bundle's) is
    /// stale, and none at all means the bundle.
    static func source(bundleRevision: Int, cachedRevision: Int?) -> Source {
        guard let cachedRevision, cachedRevision > bundleRevision else { return .bundle }
        return .cache
    }

    /// Download when the server's archive is newer than the bundle and newer
    /// than any copy already on disk. An unknown server revision (offline, a
    /// bad config) never downloads.
    static func shouldDownload(bundleRevision: Int, serverRevision: Int?, cachedRevision: Int?) -> Bool {
        guard let serverRevision, serverRevision > bundleRevision else { return false }
        return (cachedRevision ?? 0) < serverRevision
    }

    /// Disk-cache key of a bundled year's archive copy: the revision rides in
    /// the name ("calendar_ru_2026.r10"), so no copy is ever mistaken for
    /// another revision's.
    static func cacheName(_ key: String, revision: Int) -> String { "\(key).r\(revision)" }

    /// The revision in `fileName` when it is an archive copy of `key`, else nil.
    static func revision(ofCacheName fileName: String, key: String) -> Int? {
        let prefix = key + ".r", suffix = ".json"
        guard fileName.hasPrefix(prefix), fileName.hasSuffix(suffix) else { return nil }
        return Int(fileName.dropFirst(prefix.count).dropLast(suffix.count))
    }
}
