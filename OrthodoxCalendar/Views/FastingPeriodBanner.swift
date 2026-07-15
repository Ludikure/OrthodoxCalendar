import SwiftUI

/// Season banner shown under the month bar (list & grid views): the fasting
/// period's name, its date range, and the focal day's position within it.
struct FastingPeriodBanner: View {
    let period: FastingPeriodInfo
    /// "Day X of Y" is only meaningful for *today*. When the banner is a month
    /// overview (browsing a season that isn't currently active), the focal day is
    /// not today, so its index would be an arbitrary position in the run — hide it
    /// and show the date range alone.
    var showsDayIndex: Bool = true
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
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
                    let range = FastingPeriods.dateRange(period, months: localization.ui.months)
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
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(AppColors.bannerBg)
        )
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
    }
}
