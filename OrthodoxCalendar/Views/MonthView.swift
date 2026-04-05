import SwiftUI

struct MonthListView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(viewModel.daysInMonth) { dayInfo in
                        DayRowView(dayInfo: dayInfo)
                            .id(dayInfo.gregorianDate)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                viewModel.selectedDay = dayInfo
                            }

                        Divider()
                            .foregroundStyle(.secondary.opacity(0.3))
                    }
                }
            }
            .onAppear {
                scrollToToday(proxy: proxy)
            }
            .onChange(of: viewModel.daysInMonth.count) {
                scrollToToday(proxy: proxy)
            }
            .onChange(of: viewModel.scrollToTodayTrigger) {
                scrollToToday(proxy: proxy)
            }
        }
    }

    private func scrollToToday(proxy: ScrollViewProxy) {
        let calendar = Calendar(identifier: .gregorian)
        if let today = viewModel.daysInMonth.first(where: { calendar.isDateInToday($0.gregorianDate) }) {
            withAnimation {
                proxy.scrollTo(today.gregorianDate, anchor: .center)
            }
        }
    }
}
