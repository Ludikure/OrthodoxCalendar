import SwiftUI

struct DayRowView: View {
    let day: CalendarDay
    let isExpanded: Bool
    @Environment(LocalizationManager.self) private var localization
    @State private var highlightOpacity: Double = 0

    private let calendar = Calendar(identifier: .gregorian)

    private var isToday: Bool {
        guard let date = day.date else { return false }
        return calendar.isDateInToday(date)
    }

    /// Two-letter weekday abbreviation to avoid ambiguity
    private var dayOfWeekAbbrev: String {
        let abbrevs = localization.bundle.ui.daysOfWeek
        let idx = day.weekdayIndex
        guard idx >= 0, idx < abbrevs.count else { return "" }
        return String(abbrevs[idx].prefix(2))
    }

    private var isGreatFeast: Bool {
        day.isGreatFeast
    }

    private var isRed: Bool {
        day.primaryFeast?.importance == "great"
    }

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
                // Great feast badge
                if isGreatFeast {
                    Text("✦ \(greatFeastLabel)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(AppColors.crimson)
                        .textCase(.uppercase)
                        .tracking(1.2)
                }

                // Primary text
                descriptionView

                // Secondary feasts (shown in normal mode too)
                if !isExpanded {
                    if let secondaryText = secondaryText, !secondaryText.isEmpty {
                        Text(secondaryText)
                            .font(.caption)
                            .foregroundStyle(AppColors.mutedText)
                            .lineLimit(1)
                    }
                }

                // Expanded content
                if isExpanded {
                    expandedContent
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 8)

            // Fasting badge
            fastingBadge
                .padding(.leading, 6)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, isExpanded ? 14 : 10)
        .background(rowBackground)
        .overlay(alignment: .leading) {
            // Left red border for great feasts
            if isGreatFeast {
                Rectangle()
                    .fill(AppColors.crimson)
                    .frame(width: 4)
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 0)
                .fill(AppColors.goldAccent.opacity(highlightOpacity))
        )
        .onChange(of: isExpanded) {
            if isExpanded {
                withAnimation(.easeIn(duration: 0.15)) { highlightOpacity = 0.2 }
                withAnimation(.easeOut(duration: 0.6).delay(0.15)) { highlightOpacity = 0 }
            }
        }
    }

    // MARK: - Great Feast Label

    private var greatFeastLabel: String {
        switch localization.language {
        case .sr: return "Велики празник"
        case .ru: return "Великий праздник"
        }
    }

    // MARK: - Row Background

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

    // MARK: - Secondary Text

    private var secondaryText: String? {
        let secondaryNames = day.secondaryFeasts.map(\.name)
        let tertiaryNames = day.tertiaryFeasts.map(\.name)
        let all = (secondaryNames + tertiaryNames).filter { !$0.isEmpty }
        return all.isEmpty ? nil : all.joined(separator: "; ")
    }

    // MARK: - Description

    @ViewBuilder
    private var descriptionView: some View {
        let primaryName = day.primaryFeast?.name ?? ""

        if !primaryName.isEmpty {
            Text(primaryName)
                .font(.system(.subheadline, design: .serif).weight(isBold ? .bold : .regular))
                .foregroundStyle(isRed ? Color(red: 0.545, green: 0.102, blue: 0.102) : AppColors.darkText)
                .lineLimit(isExpanded ? nil : 2)
        }
    }

    // MARK: - Expanded Content

    @ViewBuilder
    private var expandedContent: some View {
        VStack(alignment: .leading, spacing: 8) {
            // All secondary & tertiary feasts
            let secondaryNames = day.secondaryFeasts.map(\.name)
            let tertiaryNames = day.tertiaryFeasts.map(\.name)
            let allSecondary = (secondaryNames + tertiaryNames).filter { !$0.isEmpty }
            if !allSecondary.isEmpty {
                Text(allSecondary.joined(separator: "; "))
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
            }

            // Fasting detail
            if !day.fasting.explanation.isEmpty {
                Label(day.fasting.explanation, systemImage: "leaf")
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
            }

            // Reflection
            if let reflection = day.reflection, !reflection.text.isEmpty {
                Text(reflection.text)
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
                    .lineLimit(4)
            }

            // Readings summary
            if !day.readings.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "book")
                        .font(.caption2)
                        .foregroundStyle(AppColors.mutedText)
                    Text(day.readings.map { "\($0.book): \($0.reference)" }.joined(separator: " • "))
                        .font(.caption)
                        .foregroundStyle(AppColors.mutedText)
                        .lineLimit(2)
                }
            }

            // Detail link
            HStack {
                Spacer()
                NavigationLink {
                    DayDetailScrollView(day: day)
                } label: {
                    Label(moreLabel, systemImage: "chevron.right")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(AppColors.crimson)
                }
            }
        }
        .padding(.top, 6)
        .padding(.top, 2)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(AppColors.warmBorder)
                .frame(height: 1)
                .padding(.horizontal, -8)
        }
    }

    // MARK: - Fasting Badge

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
        let fastType = day.fasting.type.lowercased()
        if fastType == "strict" || fastType == "dryeating" {
            return (icon.isEmpty ? "🚫" : icon, AppColors.fastStrict, AppColors.fastStrictBg)
        } else if fastType == "hotwithoutoil" || fastType == "water" {
            return (icon.isEmpty ? "💧" : icon, AppColors.fastWater, AppColors.fastWaterBg)
        } else if fastType == "hotwithoil" || fastType == "oil" {
            return (icon.isEmpty ? "🫒" : icon, AppColors.fastOil, AppColors.fastOilBg)
        } else if fastType == "fish" {
            return (icon.isEmpty ? "🐟" : icon, AppColors.fastFish, AppColors.fastFishBg)
        } else {
            return (icon.isEmpty ? "✓" : icon, AppColors.fastFree, AppColors.fastFreeBg)
        }
    }

    private var moreLabel: String {
        switch localization.language {
        case .sr: return "Детаљи"
        case .ru: return "Подробнее"
        }
    }
}

// MARK: - Full Detail View (pushed, not sheet)

struct DayDetailScrollView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        DayDetailView(day: day)
    }
}
