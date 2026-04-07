import SwiftUI

struct DayRowView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization

    private let calendar = Calendar(identifier: .gregorian)

    private var isToday: Bool {
        guard let date = day.date else { return false }
        return calendar.isDateInToday(date)
    }

    private var dayOfWeekAbbrev: String {
        let abbrevs = localization.bundle.ui.daysOfWeek
        let idx = day.weekdayIndex
        guard idx >= 0, idx < abbrevs.count else { return "" }
        return String(abbrevs[idx].prefix(2))
    }

    private var isGreatFeast: Bool { day.isGreatFeast }
    private var isRed: Bool { day.primaryFeast?.importance == "great" }
    private var isBold: Bool {
        let imp = day.primaryFeast?.importance
        return imp == "bold" || imp == "great"
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            // Day number + weekday column
            VStack(spacing: 2) {
                Text("\(day.gregorianDay)")
                    .font(.system(.title3, design: .serif).weight(.bold))
                    .foregroundStyle(day.isSunday ? AppColors.crimson : AppColors.darkText)

                Text(dayOfWeekAbbrev)
                    .font(.caption2.weight(.semibold))
                    .tracking(0.5)
                    .foregroundStyle(day.isSunday ? AppColors.crimson : AppColors.mutedText)

                Text("\(day.julianDay)")
                    .font(.system(size: 9))
                    .foregroundStyle(AppColors.lightMuted)
            }
            .frame(width: 52)
            .padding(.top, 2)

            // Main content
            VStack(alignment: .leading, spacing: 3) {
                if isGreatFeast {
                    Text("✦ \(greatFeastLabel)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(AppColors.crimson)
                        .textCase(.uppercase)
                        .tracking(1.2)
                }

                // Primary feast name
                if let primaryName = day.primaryFeast?.name, !primaryName.isEmpty {
                    Text(primaryName)
                        .font(.system(.subheadline, design: .serif).weight(isBold ? .bold : .regular))
                        .foregroundStyle(isRed ? Color(red: 0.545, green: 0.102, blue: 0.102) : AppColors.darkText)
                        .lineLimit(2)
                }

                // Secondary feasts
                if let secondaryText = secondaryText {
                    Text(secondaryText)
                        .font(.caption)
                        .foregroundStyle(AppColors.mutedText)
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 8)

            // Fasting badge
            fastingBadge
                .padding(.leading, 6)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(rowBackground)
        .overlay(alignment: .leading) {
            if isGreatFeast {
                Rectangle()
                    .fill(AppColors.crimson)
                    .frame(width: 4)
            }
        }
    }

    // MARK: - Helpers

    private var greatFeastLabel: String {
        switch localization.language {
        case .sr: return "Велики празник"
        case .ru: return "Великий праздник"
        }
    }

    private var rowBackground: some View {
        Group {
            if isToday {
                Color.yellow.opacity(0.12)
            } else if isGreatFeast {
                LinearGradient(colors: [Color(red: 1, green: 0.97, blue: 0.94),
                                        Color(red: 0.99, green: 0.92, blue: 0.82)],
                               startPoint: .leading, endPoint: .trailing)
            } else if day.isSunday {
                AppColors.crimson.opacity(0.04)
            } else {
                Color.clear
            }
        }
    }

    private var secondaryText: String? {
        let all = (day.secondaryFeasts + day.tertiaryFeasts).map(\.name).filter { !$0.isEmpty }
        return all.isEmpty ? nil : all.joined(separator: "; ")
    }

    private var fastingBadge: some View {
        let (icon, color, bg) = fastingStyle
        return HStack(spacing: 3) {
            Text(icon)
                .font(.system(size: 10))
            Text(day.fasting.abbrev)
                .font(.system(size: 10, weight: .semibold))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(bg)
        .clipShape(Capsule())
    }

    private var fastingStyle: (String, Color, Color) {
        let icon = day.fasting.icon
        let t = day.fasting.type.lowercased()
        if t.contains("abstinence") || t.contains("dryeating") || t.contains("dry") {
            return (icon.isEmpty ? "🚫" : icon, AppColors.fastStrict, AppColors.fastStrictBg)
        } else if t.contains("nooil") || t.contains("water") {
            return (icon.isEmpty ? "💧" : icon, AppColors.fastWater, AppColors.fastWaterBg)
        } else if t.contains("oil") {
            return (icon.isEmpty ? "🫒" : icon, AppColors.fastOil, AppColors.fastOilBg)
        } else if t.contains("fish") || t.contains("roe") {
            return (icon.isEmpty ? "🐟" : icon, AppColors.fastFish, AppColors.fastFishBg)
        } else {
            return (icon.isEmpty ? "✓" : icon, AppColors.fastFree, AppColors.fastFreeBg)
        }
    }
}
