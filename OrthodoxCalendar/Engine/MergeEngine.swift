import Foundation

struct MergeEngine: Sendable {
    let localization: LocalizationBundle

    /// Merge API response with localization for display
    func buildDayInfo(apiDay: OrthocalDay, date: Date) -> DayInfo {
        var info = DayInfo(gregorianDate: date)
        info.julianDateString = JulianConverter.julianDisplayString(from: date)
        let (_, julDay) = JulianConverter.julianComponents(from: date)
        info.julianDay = julDay
        info.paschaDistance = apiDay.paschaDistance
        info.tone = apiDay.tone
        info.weekday = apiDay.weekday
        info.fastLevel = apiDay.fastLevel
        info.fastException = apiDay.fastException

        // 1. Localize title
        let apiTitle = apiDay.titles.first ?? apiDay.summaryTitle
        if let localName = localization.feastNames[apiTitle] {
            info.displayName = localName
        } else {
            var matched = false
            for title in apiDay.titles {
                if let localName = localization.feastNames[title] {
                    info.displayName = localName
                    matched = true
                    break
                }
            }
            if !matched {
                info.displayName = apiTitle
            }
        }

        // 2. Feast type from API level + pascha distance
        info.feastType = FeastType.from(apiLevel: apiDay.feastLevel, paschaDistance: apiDay.paschaDistance)

        // 3. Check for language-specific feast type overrides
        for (key, override) in localization.feastTypeOverrides {
            let matchesTitle = apiDay.titles.contains { $0.contains(key) }
            let matchesSaint = apiDay.saints.contains { $0.contains(key) }
            let matchesFeast = apiDay.feasts.contains { $0.contains(key) }
            if matchesTitle || matchesSaint || matchesFeast {
                if let overrideType = FeastType(rawValue: override) {
                    if info.feastType == nil || overrideType > info.feastType! {
                        info.feastType = overrideType
                    }
                }
                break
            }
        }

        // 4. Check for extra feasts (language-specific saints not in API)
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

        // 5. Fasting info
        info.fastLevelDesc = localizeFasting(apiDay.fastLevelDesc)
        info.fastExceptionDesc = localizeFastException(apiDay.fastExceptionDesc)
        info.fastingAbbrev = computeFastingAbbrev(
            fastLevel: apiDay.fastLevel,
            fastException: apiDay.fastException,
            fastExceptionDesc: apiDay.fastExceptionDesc,
            paschaDistance: apiDay.paschaDistance
        )

        // 6. Saints, feasts, readings, stories
        info.saints = apiDay.saints
        info.feasts = apiDay.feasts
        info.readings = apiDay.readings
        info.stories = apiDay.stories

        // 7. Overlay localized saints data (works for any year)
        let pd = apiDay.paschaDistance

        if localization.language == "sr" {
            if let srEntry = SerbianCalendarData.shared.entry(gregorianDate: date, paschaDistance: pd) {
                info.localDescription = srEntry.description
                info.localIsRed = srEntry.isRed
                info.localIsBold = srEntry.isBold
                if !srEntry.fasting.isEmpty {
                    info.fastingAbbrev = srEntry.fasting
                    info.localFastingDesc = serbianFastingFull(srEntry.fasting)
                }
            }
        } else if localization.language == "ru" {
            if let ruEntry = RussianCalendarData.shared.entry(gregorianDate: date, paschaDistance: pd) {
                info.localDescription = ruEntry.description
                info.localIsRed = ruEntry.isMajorFeast
                info.localIsBold = ruEntry.isMajorFeast
                if !ruEntry.fasting.isEmpty {
                    info.fastingAbbrev = ruEntry.fasting
                }
                info.localFastingDesc = ruEntry.fastingFull ?? ""
                info.localPrayer = ruEntry.prayer ?? ""
                info.localLiturgicalNote = ruEntry.liturgicalNote ?? ""
            }
        }

        return info
    }

    // MARK: - Fasting

    private func localizeFasting(_ apiDesc: String) -> String {
        let mapping: [(key: String, uiKey: String)] = [
            ("No Fast", "noFast"),
            ("Fast Free", "fastFree"),
            ("Strict Fast", "strict"),
            ("Fish Allowed", "fish"),
            ("Oil Allowed", "oil"),
            ("Wine Allowed", "wine"),
            ("Fast Day", "strict")
        ]
        for (apiKey, uiKey) in mapping {
            if apiDesc.contains(apiKey),
               let localized = localization.ui.fastingTypes[uiKey] {
                return localized
            }
        }
        return apiDesc
    }

    private func localizeFastException(_ apiDesc: String) -> String {
        if apiDesc.isEmpty { return "" }
        let mapping: [(key: String, uiKey: String)] = [
            ("Fast Free", "fastFree"),
            ("Fish Allowed", "fish"),
            ("Oil Allowed", "oil"),
            ("Wine Allowed", "wine"),
            ("No Fast", "noFast")
        ]
        for (apiKey, uiKey) in mapping {
            if apiDesc.contains(apiKey),
               let localized = localization.ui.fastingTypes[uiKey] {
                return localized
            }
        }
        return apiDesc
    }

    /// Short fasting abbreviation for the list view (e.g., "вода", "уље", "риба", "мрс", "*")
    private func computeFastingAbbrev(fastLevel: Int, fastException: Int, fastExceptionDesc: String, paschaDistance: Int) -> String {
        // No fasting
        if fastLevel == 0 || fastExceptionDesc.contains("Fast Free") {
            return localizedFastAbbrev("none")
        }

        // Great Friday — strictest fast
        if paschaDistance == -2 {
            return "*"
        }

        // Check exception for what's allowed
        if fastExceptionDesc.contains("Fish") {
            return localizedFastAbbrev("fish")
        }
        if fastExceptionDesc.contains("Oil") || fastExceptionDesc.contains("Wine") {
            return localizedFastAbbrev("oil")
        }

        // Default strict fast — water only
        return localizedFastAbbrev("water")
    }

    private func localizedFastAbbrev(_ type: String) -> String {
        switch localization.language {
        case "sr":
            switch type {
            case "none": return "мрс"
            case "fish": return "риба"
            case "oil": return "уље"
            case "water": return "вода"
            default: return ""
            }
        case "ru":
            switch type {
            case "none": return "б/п"
            case "fish": return "рыба"
            case "oil": return "масло"
            case "water": return "вода"
            default: return ""
            }
        default: // en
            switch type {
            case "none": return "n/r"
            case "fish": return "fish"
            case "oil": return "oil"
            case "water": return "water"
            default: return ""
            }
        }
    }

    /// Expand Serbian fasting abbreviation to full description
    private func serbianFastingFull(_ abbrev: String) -> String {
        switch abbrev {
        case "мрс":  return "Без поста"
        case "вода": return "Строги пост"
        case "уље":  return "Уље дозвољено"
        case "риба": return "Риба дозвољена"
        case "✱", "*": return "Потпуно уздржавање од хране"
        default: return abbrev
        }
    }
}
