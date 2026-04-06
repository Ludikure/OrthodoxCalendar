import SwiftUI

struct MonthHeaderBar: View {
    @Binding var currentMonth: Int
    @Binding var currentYear: Int
    let daysCount: Int
    let localization: LocalizationManager
    var onMonthTap: (() -> Void)? = nil

    private let headerColor = AppColors.headerBg

    var body: some View {
        HStack(spacing: 0) {
            // Previous month
            Button {
                goToPreviousMonth()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 8)

            Spacer()

            // Month name (tappable for date picker)
            Button {
                onMonthTap?()
            } label: {
                HStack(spacing: 6) {
                    Text(localization.localizedMonthName(currentMonth))
                        .font(.system(.subheadline, design: .serif).weight(.bold))
                        .foregroundStyle(.white)
                    Text(String(currentYear))
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.7))
                }
            }

            Spacer()

            // Next month
            Button {
                goToNextMonth()
            } label: {
                Image(systemName: "chevron.right")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 8)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 10)
        .background(headerColor)
    }

    private func goToPreviousMonth() {
        if currentMonth == 1 {
            currentMonth = 12
            currentYear -= 1
        } else {
            currentMonth -= 1
        }
    }

    private func goToNextMonth() {
        if currentMonth == 12 {
            currentMonth = 1
            currentYear += 1
        } else {
            currentMonth += 1
        }
    }
}
