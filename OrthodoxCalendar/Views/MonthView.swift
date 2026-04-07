import SwiftUI

struct MonthListView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(viewModel.daysInMonth) { day in
                        NavigationLink {
                            DayDetailView(day: day)
                        } label: {
                            DayRowView(day: day)
                        }
                        .buttonStyle(.plain)

                        Rectangle()
                            .fill(AppColors.warmBorder)
                            .frame(height: 1)
                    }
                }
                .id(viewModel.loadedLocale)
                .background(AppColors.cardBg)
                .shadow(color: AppColors.darkText.opacity(0.06), radius: 6, y: 2)
            }
            .background(AppColors.warmBg)
            .onAppear {
                scrollToToday(proxy: proxy)
            }
            .onChange(of: viewModel.daysInMonth.count) {
                scrollToToday(proxy: proxy)
            }
            .onChange(of: viewModel.scrollToTodayTrigger) {
                scrollToToday(proxy: proxy)
            }
            .onChange(of: viewModel.scrollToDay) {
                if let day = viewModel.scrollToDay {
                    scrollToDay(day, proxy: proxy)
                    viewModel.scrollToDay = nil
                }
            }
        }
    }

    private func scrollToToday(proxy: ScrollViewProxy) {
        let calendar = Calendar(identifier: .gregorian)
        if let todayDay = viewModel.daysInMonth.first(where: {
            guard let date = $0.date else { return false }
            return calendar.isDateInToday(date)
        }) {
            withAnimation {
                proxy.scrollTo(todayDay.id, anchor: .center)
            }
        }
    }

    private func scrollToDay(_ dayNum: Int, proxy: ScrollViewProxy) {
        if let target = viewModel.daysInMonth.first(where: { $0.gregorianDay == dayNum }) {
            withAnimation {
                proxy.scrollTo(target.id, anchor: .center)
            }
        }
    }
}
