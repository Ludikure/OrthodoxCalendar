import SwiftUI

struct DayRowView: View, Equatable {
    let day: CalendarDay
    let isToday: Bool

    @Environment(LocalizationManager.self) private var localization

    init(day: CalendarDay, isToday: Bool = false) {
        self.day = day
        self.isToday = isToday
    }

    nonisolated static func == (lhs: DayRowView, rhs: DayRowView) -> Bool {
        lhs.day == rhs.day && lhs.isToday == rhs.isToday
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
                    .foregroundStyle(isToday ? .white : (day.isSunday ? AppColors.crimson : AppColors.darkText))
                    .frame(width: 34, height: 34)
                    .background {
                        if isToday {
                            Circle()
                                .fill(AppColors.crimson)
                        }
                    }

                Text(dayOfWeekAbbrev)
                    .font(.caption2.weight(.semibold))
                    .tracking(0.5)
                    .foregroundStyle(isToday ? AppColors.crimson : (day.isSunday ? AppColors.crimson : AppColors.mutedText))

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
        case .en, .en_nc: return "Great Feast"
        }
    }

    private var rowBackground: some View {
        Group {
            if isToday {
                AppColors.crimson.opacity(0.08)
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
            Text(day.fasting.abbrev ?? "")
                .font(.system(size: 10, weight: .semibold))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(bg)
        .clipShape(Capsule())
    }

    private var fastingStyle: (String, Color, Color) {
        let t = day.fasting.type.lowercased()
        if t == "totalabstinence" {
            return ("🚫", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if t == "dryeating" {
            return ("🍞", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if t.contains("nooil") {
            return ("💧", AppColors.fastWater, AppColors.fastWaterBg)
        } else if t.contains("oil") {
            return ("🫒", AppColors.fastOil, AppColors.fastOilBg)
        } else if t.contains("fish") || t.contains("roe") {
            return ("🐟", AppColors.fastFish, AppColors.fastFishBg)
        } else {
            return ("✓", AppColors.fastFree, AppColors.fastFreeBg)
        }
    }
}
