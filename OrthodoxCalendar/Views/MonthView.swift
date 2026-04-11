import SwiftUI

struct MonthListView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization
    @State private var todayString = Self.makeTodayString()

    private static func makeTodayString() -> String {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        fmt.calendar = Calendar(identifier: .gregorian)
        return fmt.string(from: Date())
    }

    private func refreshToday() {
        todayString = Self.makeTodayString()
    }

    var body: some View {
        let today = todayString
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(viewModel.daysInMonth) { day in
                        NavigationLink(value: day) {
                            DayRowView(day: day, isToday: day.gregorianDate == today)
                        }
                        .buttonStyle(.plain)

                        AppColors.warmBorder
                            .frame(height: 1)
                    }
                }
                .id(viewModel.loadedLocale)
                .background(AppColors.cardBg)
            }
            .background(AppColors.warmBg)
            .navigationDestination(for: CalendarDay.self) { day in
                DayDetailView(day: day)
            }
            .onAppear {
                refreshToday()
                scrollToToday(proxy: proxy)
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.significantTimeChangeNotification)) { _ in
                refreshToday()
                viewModel.goToToday()
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willEnterForegroundNotification)) { _ in
                refreshToday()
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
