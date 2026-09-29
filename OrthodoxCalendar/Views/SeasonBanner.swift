import SwiftUI

/// Banner under the month bar (list & grid views). Its first row is the
/// fasting season — name, date range and, for today, "Day X of Y" — and its
/// second, in the 30 days before the user's slava (Serbian) or name day
/// (Russian — the two never meet), a countdown to it. Either
/// row can be absent; with both, they share one card under a thin rule, so a
/// slava inside a fast (Никољдан always is) never hides the fast and costs
/// the list one short row instead of a second banner.
struct SeasonBanner: View {
    let period: FastingPeriodInfo?
    /// "Day X of Y" is only meaningful for *today*. When the banner is a month
    /// overview (browsing a season that isn't currently active), the focal day is
    /// not today, so its index would be an arbitrary position in the run — hide it
    /// and show the date range alone.
    var showsDayIndex: Bool = true
    var slava: SlavaCountdown? = nil
    var onSlavaTap: () -> Void = {}
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let period {
                periodRow(period)
            }
            if period != nil, slava != nil {
                AppColors.bannerDivider
                    .frame(height: 1)
                    .padding(.horizontal, 14)
            }
            if let slava {
                Button(action: onSlavaTap) { slavaRow(slava) }
                    .buttonStyle(.plain)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(AppColors.bannerBg)
        )
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
    }

    private func periodRow(_ period: FastingPeriodInfo) -> some View {
        HStack(spacing: 10) {
            Text("⛪")
                .font(.system(size: 16))
            VStack(alignment: .leading, spacing: 1) {
                Text(FastingPeriods.displayName(period.code, names: localization.bundle.fastingPeriodNames))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(AppColors.bannerTitle)
                // Date range only when the run is fully known (a season truncated at
                // the data boundary would mislead); the "Day X of Y" suffix only when
                // it refers to today.
                if period.complete {
                    // After a day number Russian takes the genitive: "15 мар – 1 мая".
                    let range = FastingPeriods.dateRange(period, months: localization.ui.monthsGenitive ?? localization.ui.months)
                    let text = showsDayIndex
                        ? "\(range)  ·  \(FastingPeriods.dayLabel(localization.language, index: period.dayIndex, total: period.total))"
                        : range
                    Text(text)
                        .font(.system(size: 12))
                        .foregroundStyle(AppColors.bannerSubtext)
                }
            }
            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }

    private func slavaRow(_ slava: SlavaCountdown) -> some View {
        let isNameDay = slava.kind == .nameDay
        let today = isNameDay ? "Сегодня" : "Данас"
        let suffix = isNameDay ? "ваши именины" : "ваша слава"
        return HStack(spacing: 10) {
            Group {
                if isNameDay {
                    Image(systemName: NameDayText.icon)
                        .foregroundStyle(AppColors.slavaGold)
                } else {
                    Text("🕯")
                }
            }
            .font(.system(size: 16))
            // "Никољдан — ваша слава" when it fits; a long name ("Покров
            // Пресвете Богородице") keeps the name and drops the suffix.
            ViewThatFits(in: .horizontal) {
                slavaTitle(slava.days == 0 ? "\(today): \(slava.name) — \(suffix)" : "\(slava.name) — \(suffix)")
                slavaTitle(slava.days == 0 ? "\(today): \(slava.name)" : slava.name)
                slavaTitle(slava.name, lines: 2)
            }
            Spacer(minLength: 6)
            Text(isNameDay ? NameDayText.countdown(slava.days) : Self.countdownLabel(slava.days))
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(AppColors.slavaGold)
                .padding(.horizontal, 9)
                .padding(.vertical, 4)
                .background(Capsule().fill(AppColors.cardBg))
                .overlay(Capsule().stroke(AppColors.gold, lineWidth: 1))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityHint(isNameDay ? "Открывает день именин" : "Отвара дан славе")
    }

    private func slavaTitle(_ text: String, lines: Int = 1) -> some View {
        Text(text)
            .font(.system(size: 14, weight: .bold, design: .serif))
            .foregroundStyle(AppColors.bannerTitle)
            .lineLimit(lines)
            .fixedSize(horizontal: false, vertical: true)
    }

    /// "за 12 дана"; shared with the widget (`SlavaCountdownText`).
    nonisolated static func countdownLabel(_ days: Int) -> String {
        SlavaCountdownText.label(days)
    }
}

/// The user's next slava — or, in Russian, name day — as the banner shows it.
struct SlavaCountdown: Equatable {
    enum Kind: Equatable { case slava, nameDay }
    let name: String
    let date: Date
    let days: Int
    var kind: Kind = .slava
}
