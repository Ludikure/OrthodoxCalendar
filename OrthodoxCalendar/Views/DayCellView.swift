import SwiftUI

struct DayRowView: View {
    let dayInfo: DayInfo
    @Environment(LocalizationManager.self) private var localization

    private let calendar = Calendar(identifier: .gregorian)

    private var isToday: Bool {
        calendar.isDateInToday(dayInfo.gregorianDate)
    }

    private var dayOfWeekAbbrev: String {
        let fullAbbrevs = localization.bundle.ui.daysOfWeek
        guard dayInfo.weekday >= 0, dayInfo.weekday < fullAbbrevs.count else { return "" }
        let abbrev = fullAbbrevs[dayInfo.weekday]
        return String(abbrev.prefix(1))
    }

    private var feastColor: Color {
        guard let type = dayInfo.feastType else { return .primary }
        switch type {
        case .pascha: return AppColors.crimson
        case .great: return AppColors.crimson
        case .holyWeek: return .primary
        case .bright: return AppColors.crimson
        case .major: return AppColors.feastBlue
        case .minor: return .primary
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            Text(dayOfWeekAbbrev)
                .font(.subheadline.weight(dayInfo.isSunday ? .bold : .regular))
                .foregroundStyle(dayInfo.isSunday ? AppColors.crimson : .primary)
                .frame(width: 28, alignment: .center)

            Text("\(dayInfo.gregorianDay)")
                .font(.subheadline.weight(.medium))
                .foregroundStyle(dayInfo.isSunday ? AppColors.crimson : .primary)
                .frame(width: 28, alignment: .center)

            Text("\(dayInfo.julianDay)")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(width: 28, alignment: .center)

            descriptionView
                .frame(maxWidth: .infinity, alignment: .leading)

            Text(dayInfo.fastingAbbrev)
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 40, alignment: .trailing)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 5)
        .background(
            isToday
                ? Color.yellow.opacity(0.12)
                : (dayInfo.isSunday ? AppColors.crimson.opacity(0.03) : Color.clear)
        )
    }

    // MARK: - Description

    @ViewBuilder
    private var descriptionView: some View {
        if !dayInfo.localDescription.isEmpty {
            Text(dayInfo.localDescription)
                .font(dayInfo.localIsBold ? .subheadline.bold() : .subheadline)
                .foregroundStyle(dayInfo.localIsRed ? AppColors.crimson : .primary)
                .lineLimit(3)
        } else if dayInfo.isSignificantFeast {
            VStack(alignment: .leading, spacing: 2) {
                Text(dayInfo.displayName)
                    .font(.subheadline.bold())
                    .foregroundStyle(feastColor)

                if !dayInfo.saints.isEmpty {
                    Text(dayInfo.saints.joined(separator: "; "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
        } else if dayInfo.feastType == .holyWeek {
            VStack(alignment: .leading, spacing: 2) {
                Text(dayInfo.displayName)
                    .font(.subheadline.bold())
                    .foregroundStyle(.primary)

                if !dayInfo.saints.isEmpty {
                    Text(dayInfo.saints.joined(separator: "; "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 1) {
                if !dayInfo.feasts.isEmpty {
                    Text(dayInfo.feasts.joined(separator: "; "))
                        .font(.subheadline)
                        .foregroundStyle(.primary)
                }
                if !dayInfo.saints.isEmpty {
                    Text(dayInfo.saints.joined(separator: "; "))
                        .font(.subheadline)
                        .foregroundStyle(.primary)
                        .lineLimit(3)
                }
                if dayInfo.feasts.isEmpty && dayInfo.saints.isEmpty && !dayInfo.displayName.isEmpty {
                    Text(dayInfo.displayName)
                        .font(.subheadline)
                        .foregroundStyle(.primary)
                }
            }
        }
    }
}
