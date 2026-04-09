import SwiftUI

struct CalendarTabView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var vm = viewModel

        NavigationStack {
            VStack(spacing: 0) {
                // Two-line title header
                CalendarTitle(localization: localization)

                // Month header bar (dark brown)
                MonthHeaderBar(
                    currentMonth: $vm.currentMonth,
                    currentYear: $vm.currentYear,
                    daysCount: viewModel.daysInMonth.count,
                    localization: localization,
                    onMonthTap: { viewModel.showDatePicker = true }
                )

                // Day list
                MonthListView()
            }
            .background(AppColors.warmBg)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(localization.ui.todayLabel) {
                        viewModel.goToToday()
                    }
                    .font(.subheadline)
                    .foregroundStyle(AppColors.mutedText)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 16) {
                        Button {
                            viewModel.showSearch = true
                        } label: {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(AppColors.mutedText)
                        }
                        NavigationLink {
                            SettingsView(onLanguageChanged: { locale in
                                viewModel.forceReload(locale: locale)
                            })
                        } label: {
                            Image(systemName: "gearshape")
                                .foregroundStyle(AppColors.mutedText)
                        }
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $vm.selectedDay) { day in
                NavigationStack {
                    DayDetailView(day: day)
                }
            }
            .sheet(isPresented: $vm.showSearch) {
                SaintSearchView()
            }
            .sheet(isPresented: $vm.showDatePicker) {
                DatePickerSheet(currentMonth: viewModel.currentMonth, currentYear: viewModel.currentYear)
                    .presentationDetents([.medium, .large])
            }
            .onChange(of: viewModel.navigateToDay) {
                if let dayNum = viewModel.navigateToDay {
                    // Wait for month data to load, then navigate to detail
                    Task {
                        // Give loadMonth time to complete
                        try? await Task.sleep(for: .milliseconds(300))
                        if let target = viewModel.daysInMonth.first(where: { $0.gregorianDay == dayNum }) {
                            viewModel.selectedDay = target
                        }
                        viewModel.navigateToDay = nil
                    }
                }
            }
        }
    }
}

// MARK: - Title (two-line: app title + church subtitle)

struct CalendarTitle: View {
    let localization: LocalizationManager

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Text("✝")
                    .foregroundStyle(AppColors.crimson)
                Text(localization.ui.appTitle)
                    .font(.system(.title2, design: .serif).weight(.bold))
                    .foregroundStyle(AppColors.darkText)
            }

            Text(churchSubtitle)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundStyle(AppColors.mutedText)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 8)
        .background(AppColors.warmBg)
    }

    private var churchSubtitle: String {
        switch localization.language {
        case .sr: return "Српска Православна Црква"
        case .ru: return "Русская Православная Церковь"
        case .en: return "Orthodox Church Calendar"
        }
    }
}
