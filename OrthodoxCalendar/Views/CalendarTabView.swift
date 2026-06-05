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
                    viewMode: $vm.viewMode,
                    daysCount: viewModel.daysInMonth.count,
                    localization: localization,
                    onMonthTap: { viewModel.showDatePicker = true }
                )

                // Calendar content
                ZStack {
                    if viewModel.viewMode == .grid {
                        CalendarGridView()
                    } else {
                        MonthListView()
                    }

                    // Loading / offline states for years fetched on demand.
                    if viewModel.daysInMonth.isEmpty {
                        if viewModel.isLoading {
                            ProgressView(localization.ui.loadingLabel ?? "Loading…")
                                .tint(AppColors.crimson)
                        } else if viewModel.errorMessage != nil {
                            CalendarLoadFailureView(
                                message: localization.ui.offlineMessage
                                    ?? "Couldn't load data. Check your connection.",
                                onRetry: { viewModel.loadMonth() }
                            )
                        }
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .background(AppColors.warmBg)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(localization.ui.todayLabel) {
                        Haptics.medium()
                        viewModel.goToToday()
                    }
                    .font(.subheadline)
                    .foregroundStyle(AppColors.mutedText)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 16) {
                        Button {
                            Haptics.light()
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

// MARK: - Load failure (offline / missing data for an on-demand year)

struct CalendarLoadFailureView: View {
    let message: String
    let onRetry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.slash")
                .font(.largeTitle)
                .foregroundStyle(AppColors.mutedText)
            Text(message)
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(AppColors.mutedText)
                .padding(.horizontal, 32)
            Button {
                Haptics.light()
                onRetry()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.title3)
                    .foregroundStyle(AppColors.crimson)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.warmBg)
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
        case .en, .en_nc: return "Orthodox Church Calendar"
        }
    }
}
