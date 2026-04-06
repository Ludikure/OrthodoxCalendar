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
                    .font(.title3.weight(.bold))
                    .foregroundStyle(day.isSunday ? AppColors.crimson : .primary)

                Text(dayOfWeekAbbrev)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(day.isSunday ? AppColors.crimson : .secondary)

                Text("\(day.julianDay)")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
            }
            .frame(width: 44)

            // Main content
            VStack(alignment: .leading, spacing: 3) {
                // Great feast badge
                if isGreatFeast {
                    Text("✦ \(greatFeastLabel)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(AppColors.crimson)
                        .textCase(.uppercase)
                        .tracking(0.8)
                }

                // Primary text
                descriptionView

                // Expanded content
                if isExpanded {
                    expandedContent
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Fasting badge
            fastingBadge
                .padding(.leading, 6)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, isExpanded ? 12 : 8)
        .background(rowBackground)
        .overlay(
            RoundedRectangle(cornerRadius: 0)
                .fill(AppColors.gold.opacity(highlightOpacity))
        )
        .onChange(of: isExpanded) {
            if isExpanded {
                // Gold highlight pulse
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
        case .en: return "Great Feast"
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

    // MARK: - Description

    @ViewBuilder
    private var descriptionView: some View {
        let primaryName = day.primaryFeast?.name ?? ""
        let secondaryNames = day.secondaryFeasts.map(\.name)
        let tertiaryNames = day.tertiaryFeasts.map(\.name)

        if isBold || isGreatFeast {
            VStack(alignment: .leading, spacing: 2) {
                if !primaryName.isEmpty {
                    Text(primaryName)
                        .font(.subheadline.weight(isBold ? .bold : .regular))
                        .foregroundStyle(isRed ? AppColors.crimson : .primary)
                        .lineLimit(isExpanded ? nil : 2)
                }

                if !secondaryNames.isEmpty {
                    Text(secondaryNames.joined(separator: "; "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(isExpanded ? nil : 1)
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 1) {
                let allNames = ([primaryName] + secondaryNames + tertiaryNames).filter { !$0.isEmpty }
                let text = allNames.joined(separator: "; ")
                if !text.isEmpty {
                    Text(text)
                        .font(.subheadline)
                        .lineLimit(isExpanded ? nil : 2)
                }
            }
        }
    }

    // MARK: - Expanded Content

    @ViewBuilder
    private var expandedContent: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Fasting detail
            if !day.fasting.explanation.isEmpty {
                Label(day.fasting.explanation, systemImage: "leaf")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            // Reflection
            if let reflection = day.reflection, !reflection.text.isEmpty {
                Text(reflection.text)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(4)
            }

            // Readings summary
            if !day.readings.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "book")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(day.readings.map { "\($0.book): \($0.reference)" }.joined(separator: " • "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
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
        .padding(.top, 4)
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
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .background(bg)
        .clipShape(Capsule())
    }

    private var fastingStyle: (String, Color, Color) {
        let icon = day.fasting.icon
        let fastType = day.fasting.type.lowercased()
        if fastType == "strict" || fastType == "dryeating" {
            return (icon.isEmpty ? "🚫" : icon, Color.purple, Color.purple.opacity(0.1))
        } else if fastType == "hotwithoutoil" || fastType == "water" {
            return (icon.isEmpty ? "💧" : icon, Color.blue, Color.blue.opacity(0.08))
        } else if fastType == "hotwithoil" || fastType == "oil" {
            return (icon.isEmpty ? "🫒" : icon, Color.yellow.opacity(0.8), Color.yellow.opacity(0.08))
        } else if fastType == "fish" {
            return (icon.isEmpty ? "🐟" : icon, Color.teal, Color.teal.opacity(0.08))
        } else {
            return (icon.isEmpty ? "✓" : icon, Color.green, Color.green.opacity(0.08))
        }
    }

    private var moreLabel: String {
        switch localization.language {
        case .sr: return "Детаљи"
        case .ru: return "Подробнее"
        case .en: return "Details"
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
