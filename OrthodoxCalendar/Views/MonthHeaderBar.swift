import SwiftUI

struct MonthHeaderBar: View {
    @Binding var currentMonth: Int
    @Binding var currentYear: Int
    @Binding var viewMode: CalendarViewModel.ViewMode
    let daysCount: Int
    let localization: LocalizationManager
    var onMonthTap: (() -> Void)? = nil

    private let headerColor = Color(red: 0.478, green: 0.106, blue: 0.106)

    var body: some View {
        HStack(spacing: 0) {
            // Previous month
            Button {
                Haptics.selection()
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
                Haptics.light()
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

            // View mode toggle
            HStack(spacing: 2) {
                Button {
                    Haptics.selection()
                    withAnimation(.easeInOut(duration: 0.2)) { viewMode = .list }
                } label: {
                    Image(systemName: "list.bullet")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(viewMode == .list ? AppColors.headerBg : .white.opacity(0.5))
                        .padding(6)
                        .background(viewMode == .list ? AppColors.goldAccent : Color.clear)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
                Button {
                    Haptics.selection()
                    withAnimation(.easeInOut(duration: 0.2)) { viewMode = .grid }
                } label: {
                    Image(systemName: "square.grid.3x3")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(viewMode == .grid ? AppColors.headerBg : .white.opacity(0.5))
                        .padding(6)
                        .background(viewMode == .grid ? AppColors.goldAccent : Color.clear)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
            }
            .padding(.trailing, 8)

            // Next month
            Button {
                Haptics.selection()
                goToNextMonth()
            } label: {
                Image(systemName: "chevron.right")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 8)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 14)
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
