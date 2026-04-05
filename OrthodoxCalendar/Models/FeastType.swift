import Foundation

enum FeastType: String, Codable, Comparable, Sendable {
    case pascha
    case great
    case holyWeek
    case major
    case bright
    case minor

    var rank: Int {
        switch self {
        case .pascha:   return 10
        case .great:    return 8
        case .holyWeek: return 7
        case .major:    return 6
        case .bright:   return 5
        case .minor:    return 3
        }
    }

    static func < (lhs: FeastType, rhs: FeastType) -> Bool {
        lhs.rank < rhs.rank
    }

    /// Map API feast_level integer to FeastType
    static func from(apiLevel: Int, paschaDistance: Int) -> FeastType? {
        // Holy Week: pascha_distance -7..-1
        if paschaDistance >= -7 && paschaDistance <= -1 {
            return .holyWeek
        }
        // Bright Week: pascha_distance 0..6
        if paschaDistance >= 0 && paschaDistance <= 6 {
            if paschaDistance == 0 { return .pascha }
            return .bright
        }
        switch apiLevel {
        case 7...8: return .great
        case 5...6: return .major
        case 3...4: return .minor
        default:    return nil
        }
    }
}
