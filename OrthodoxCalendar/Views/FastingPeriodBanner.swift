import SwiftUI

/// Season banner shown under the month bar (list & grid views): the fasting
/// period's name, its date range, and the focal day's position within it.
struct FastingPeriodBanner: View {
    let period: FastingPeriodInfo
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        HStack(spacing: 10) {
            Text("⛪")
                .font(.system(size: 16))
            VStack(alignment: .leading, spacing: 1) {
                Text(FastingPeriods.displayName(period.code, names: localization.bundle.fastingPeriodNames))
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(AppColors.bannerTitle)
                // Date range + "Day X of Y" only when the run is fully known
                // (a season truncated at the data boundary would mislead).
                if period.complete {
                    Text("\(FastingPeriods.dateRange(period, months: localization.ui.months))  ·  \(FastingPeriods.dayLabel(localization.language, index: period.dayIndex, total: period.total))")
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
