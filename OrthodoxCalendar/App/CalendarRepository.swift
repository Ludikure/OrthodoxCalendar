import Foundation

/// Loads a year of calendar data for a given locale from the app bundle.
///
/// All supported years (minYear...maxYear) ship bundled and deduplicated: large
/// text (saint bios + scripture readings) lives in a per-locale `texts_<locale>`
/// pool keyed by content hash, and the calendar files reference it. There is no
/// network path — the app is fully offline. Mirror of Android `CalendarRepository`.
actor CalendarRepository {
    static let shared = CalendarRepository()

    private var memoryCache: [String: CalendarFile] = [:]
    /// Per-locale deduped text pool (texts_<locale>.json), loaded lazily.
    private var textsCache: [String: [String: String]] = [:]

    enum LoadError: Error {
        case offline      // retained for call-site compatibility; never thrown now
        case notFound     // no bundled data for this locale/year
    }

    private func fileKey(_ locale: String, _ year: Int) -> String {
        "calendar_\(locale)_\(year)"
    }

    /// Resolve a year from the bundle (decoded once, cached in memory).
    func load(locale: String, year: Int) async throws -> CalendarFile {
        let key = fileKey(locale, year)
        if let cached = memoryCache[key] { return cached }
        guard let file = decode(data: bundleData(key)) else { throw LoadError.notFound }
        let resolved = resolveText(file, locale: locale)
        memoryCache[key] = resolved
        return resolved
    }

    /// Fills bio + reading text from the per-locale pool for deduped bundled data.
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
