import Foundation

/// Builds degraded DayInfo from local data when API cache is empty and offline.
/// Provides: feast names, feast types, fasting periods. No readings or saints.
struct OfflineFallbackEngine {
    let localization: LocalizationBundle

    func buildDayInfo(for date: Date) -> DayInfo {
        let calendar = Calendar(identifier: .gregorian)
        let year = calendar.component(.year, from: date)

        var info = DayInfo(gregorianDate: date)
        info.julianDateString = JulianConverter.julianDisplayString(from: date)

        // Weekday (0=Sun convention matching API)
        let weekdayComponent = calendar.component(.weekday, from: date) // 1=Sun..7=Sat
        info.weekday = weekdayComponent - 1

        // Julian day
        let (_, julDay) = JulianConverter.julianComponents(from: date)
        info.julianDay = julDay

        // Compute pascha distance
        if let paschaDate = PaschaCalculator.pascha(for: year) {
            let distance = calendar.dateComponents([.day], from: paschaDate, to: date).day ?? 0
            info.paschaDistance = distance
            info.feastType = feastTypeFromDistance(distance)

            // Try to identify moveable feasts by distance
            if let moveableName = moveableFeastName(distance: distance) {
                if let localName = localization.feastNames[moveableName] {
                    info.displayName = localName
                } else {
                    info.displayName = moveableName
                }
            }
        }

        // Check for fixed feasts (extra feasts by Julian date)
        let (julMonth, _) = JulianConverter.julianComponents(from: date)
        for extra in localization.extraFeasts {
            if extra.julianMonth == julMonth && extra.julianDay == julDay {
                let extraType = FeastType(rawValue: extra.type)
                let extraRank = extraType?.rank ?? 0
                let currentRank = info.feastType?.rank ?? 0

                if extraRank > currentRank {
                    info.displayName = extra.name
                    info.feastType = extraType
                }
                info.extraFeastName = extra.name
                info.extraFeastDescription = extra.description
            }
        }

        // Fasting — derive from pascha distance
        info.fastLevelDesc = fastingStatus(paschaDistance: info.paschaDistance, date: date)

        return info
    }

    // MARK: - Moveable Feasts by Pascha Distance

    private func moveableFeastName(distance: Int) -> String? {
        let moveableFeasts: [Int: String] = [
            -49: "Sunday of the Publican and the Pharisee",
            -42: "Sunday of the Prodigal Son",
            -35: "Meatfare Sunday",
            -28: "Cheesefare Sunday",
            -48: "Clean Monday",
            -8:  "Lazarus Saturday",
            -7:  "Palm Sunday",
            -6:  "Great and Holy Monday",
            -5:  "Great and Holy Tuesday",
            -4:  "Great and Holy Wednesday",
            -3:  "Great and Holy Thursday",
            -2:  "Great and Holy Friday",
            -1:  "Great and Holy Saturday",
             0:  "Holy Pascha",
             1:  "Bright Monday",
             2:  "Bright Tuesday",
             3:  "Bright Wednesday",
             4:  "Bright Thursday",
             5:  "Bright Friday",
             6:  "Bright Saturday",
             7:  "Thomas Sunday",
            14:  "Sunday of the Myrrhbearing Women",
            24:  "Mid-Pentecost",
            39:  "Ascension of our Lord",
            49:  "Pentecost",
            50:  "Monday of the Holy Spirit",
            56:  "All Saints"
        ]
        return moveableFeasts[distance]
    }

    private func feastTypeFromDistance(_ distance: Int) -> FeastType? {
        if distance == 0 { return .pascha }
        if distance >= -7 && distance <= -1 { return .holyWeek }
        if distance >= 1 && distance <= 6 { return .bright }
        return nil
    }

    /// Simplified fasting derivation from pascha distance and calendar date
    private func fastingStatus(paschaDistance: Int?, date: Date) -> String {
        let calendar = Calendar(identifier: .gregorian)
        let month = calendar.component(.month, from: date)
        let day = calendar.component(.day, from: date)

        // Bright Week — fast free
        if let pd = paschaDistance, pd >= 0, pd <= 6 {
            return localization.ui.fastingTypes["fastFree"] ?? "Fast-Free"
        }

        // Great Lent: pascha distance -48 to -1
        if let pd = paschaDistance, pd >= -48, pd <= -1 {
            let periodName = localization.fastingPeriodNames["Great Lent"] ?? "Great Lent"
            return periodName
        }

        // Apostles' Fast: Monday after All Saints (pd 57) to June 28 (Julian) = July 11 (Gregorian)
        if let pd = paschaDistance, pd >= 57 {
            if month < 7 || (month == 7 && day <= 11) {
                let periodName = localization.fastingPeriodNames["Apostles' Fast"] ?? "Apostles' Fast"
                return periodName
            }
        }

        // Dormition Fast: August 14-27 (Gregorian = August 1-14 Julian)
        if month == 8, day >= 14, day <= 27 {
            let periodName = localization.fastingPeriodNames["Dormition Fast"] ?? "Dormition Fast"
            return periodName
        }

        // Nativity Fast: November 28 - January 6 (Gregorian)
        if (month == 11 && day >= 28) || month == 12 || (month == 1 && day <= 6) {
            let periodName = localization.fastingPeriodNames["Nativity Fast"] ?? "Nativity Fast"
            return periodName
        }

        // Wednesday and Friday fasting (simplified)
        let weekday = calendar.component(.weekday, from: date)
        if weekday == 4 || weekday == 6 { // Wed = 4, Fri = 6
            return localization.ui.fastingTypes["strict"] ?? "Fast Day"
        }

        return localization.ui.fastingTypes["noFast"] ?? "No Fast"
    }
}
