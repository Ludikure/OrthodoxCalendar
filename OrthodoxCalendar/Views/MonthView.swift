import SwiftUI

struct MonthListView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var vm = viewModel

        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(viewModel.daysInMonth) { day in
                        DayRowView(
                            day: day,
                            isExpanded: viewModel.expandedDay?.id == day.id
                        )
                        .id(day.id)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            withAnimation(.easeInOut(duration: 0.25)) {
                                if viewModel.expandedDay?.id == day.id {
                                    viewModel.expandedDay = nil
                                } else {
                                    viewModel.expandedDay = day
                                }
                            }
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
        let today = Date()
        if let todayDay = viewModel.daysInMonth.first(where: {
            guard let date = $0.date else { return false }
            return calendar.isDateInToday(date)
        }) {
            withAnimation {
                proxy.scrollTo(todayDay.id, anchor: .center)
            }
        }
    }
}
