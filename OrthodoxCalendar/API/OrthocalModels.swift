import Foundation

/// Matches the actual orthocal.info API response shape.
/// Many fields can be null in the API — all collections use custom decoding
/// to treat null as empty arrays.
struct OrthocalDay: Codable, Sendable {
    let paschaDistance: Int
    let julianDayNumber: Int
    let year: Int
    let month: Int
    let day: Int
    let weekday: Int
    let tone: Int
    let titles: [String]
    let summaryTitle: String
    let feastLevel: Int
    let feastLevelDescription: String
    let feasts: [String]
    let fastLevel: Int
    let fastLevelDesc: String
    let fastException: Int
    let fastExceptionDesc: String
    let saints: [String]
    let serviceNotes: [String]
    let readings: [OrthocalReading]
    let stories: [OrthocalStory]

    enum CodingKeys: String, CodingKey {
        case paschaDistance = "pascha_distance"
        case julianDayNumber = "julian_day_number"
        case year, month, day, weekday, tone
        case titles
        case summaryTitle = "summary_title"
        case feastLevel = "feast_level"
        case feastLevelDescription = "feast_level_description"
        case feasts
        case fastLevel = "fast_level"
        case fastLevelDesc = "fast_level_desc"
        case fastException = "fast_exception"
        case fastExceptionDesc = "fast_exception_desc"
        case saints
        case serviceNotes = "service_notes"
        case readings, stories
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        paschaDistance = try c.decode(Int.self, forKey: .paschaDistance)
        julianDayNumber = try c.decode(Int.self, forKey: .julianDayNumber)
        year = try c.decode(Int.self, forKey: .year)
        month = try c.decode(Int.self, forKey: .month)
        day = try c.decode(Int.self, forKey: .day)
        weekday = try c.decode(Int.self, forKey: .weekday)
        tone = try c.decode(Int.self, forKey: .tone)
        titles = (try? c.decode([String].self, forKey: .titles)) ?? []
        summaryTitle = (try? c.decode(String.self, forKey: .summaryTitle)) ?? ""
        feastLevel = try c.decode(Int.self, forKey: .feastLevel)
        feastLevelDescription = (try? c.decode(String.self, forKey: .feastLevelDescription)) ?? ""
        feasts = (try? c.decode([String].self, forKey: .feasts)) ?? []
        fastLevel = try c.decode(Int.self, forKey: .fastLevel)
        fastLevelDesc = (try? c.decode(String.self, forKey: .fastLevelDesc)) ?? ""
        fastException = try c.decode(Int.self, forKey: .fastException)
        fastExceptionDesc = (try? c.decode(String.self, forKey: .fastExceptionDesc)) ?? ""
        saints = (try? c.decode([String].self, forKey: .saints)) ?? []
        serviceNotes = (try? c.decode([String].self, forKey: .serviceNotes)) ?? []
        readings = (try? c.decode([OrthocalReading].self, forKey: .readings)) ?? []
        stories = (try? c.decode([OrthocalStory].self, forKey: .stories)) ?? []
    }
}

struct OrthocalReading: Codable, Identifiable, Sendable {
    var id: String { "\(source)-\(display)" }

    let source: String
    let book: String
    let description: String
    let display: String
    let shortDisplay: String
    let passage: [OrthocalVerse]

    enum CodingKeys: String, CodingKey {
        case source, book, description, display
        case shortDisplay = "short_display"
        case passage
    }
}

struct OrthocalVerse: Codable, Sendable {
    let book: String
    let chapter: Int
    let verse: Int
    let content: String
    let paragraphStart: Bool

    enum CodingKeys: String, CodingKey {
        case book, chapter, verse, content
        case paragraphStart = "paragraph_start"
    }
}

struct OrthocalStory: Codable, Identifiable, Sendable {
    var id: String { title }

    let title: String
    let story: String
}
