import StoreKit
import SwiftUI

struct CalendarTabView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization
    @Environment(SlavaStore.self) private var slavaStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.requestReview) private var requestReview

    private var todayString: String { DateKeys.today }

    /// The season to show in the banner, and whether its "Day X of Y" is about
    /// today. When today is in the viewed month the banner reflects *today's*
    /// status: its season if we're in one, otherwise nothing — we must not fall
    /// back to a fast that has already ended (or not yet begun) elsewhere in the
    /// month, which would show e.g. "Day 24 of 34" of the Apostles' Fast days
    /// after it ended. When browsing another month we show that month's season as
    /// an overview (name + range, no day index — there is no "current day" there).
    private var focal: (period: FastingPeriodInfo, isToday: Bool)? {
        let today = todayString
        if viewModel.daysInMonth.contains(where: { $0.gregorianDate == today }) {
            guard let p = viewModel.fastingPeriods[today] else { return nil }
            return (p, true)
        }
        if let first = viewModel.daysInMonth.first(where: { viewModel.fastingPeriods[$0.gregorianDate] != nil }),
           let p = viewModel.fastingPeriods[first.gregorianDate] {
            return (p, false)
        }
        return nil
    }

    /// The countdown row for the banner: Serbian only, from 30 days before the
    /// user's slava, and only while the month on screen holds today or the
    /// slava itself — browsing March in December shouldn't count down to
    /// Nikoljdan.
    private var slavaCountdown: SlavaCountdown? {
        guard localization.language == .sr,
              let next = slavaStore.countdown(),
              next.days <= SlavaStore.bannerDays else { return nil }
        let cal = ChurchDates.calendar
        let shown = { (d: Date) in
            cal.component(.year, from: d) == viewModel.currentYear
                && cal.component(.month, from: d) == viewModel.currentMonth
        }
        guard shown(Date()) || shown(next.date) else { return nil }
        return SlavaCountdown(name: next.slava.name, date: next.date, days: next.days)
    }

    private func openSlava(_ countdown: SlavaCountdown) {
        Haptics.light()
        viewModel.open(dateKey: DateKeys.key(from: countdown.date))
    }

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

                // Season banner when the viewed month touches a fasting season
                // (see `focal`) or the user's slava is near (see
                // `slavaCountdown`). Sits above the list with a soft shadow so
                // scrolled rows pass cleanly under it.
                let slava = slavaCountdown
                if focal != nil || slava != nil {
                    SeasonBanner(period: focal?.period, showsDayIndex: focal?.isToday ?? false,
                                 slava: slava, onSlavaTap: { if let slava { openSlava(slava) } })
                        .background(AppColors.warmBg)
                        .shadow(color: .black.opacity(0.06), radius: 4, y: 3)
                        .zIndex(1)
                }

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
                            // Retrying only helps when the load failed on the
                            // network; blaming the connection for a year that
                            // simply has no data sends the user chasing wifi.
                            CalendarLoadFailureView(
                                message: viewModel.isOffline
                                    ? (localization.ui.offlineMessage
                                        ?? "Couldn't load data. Check your connection.")
                                    : noDataMessage(viewModel.currentYear),
                                systemImage: viewModel.isOffline ? "wifi.slash" : "calendar.badge.exclamationmark",
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
                            SettingsView()
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
                // If the month is already the loaded one, open the day now;
                // otherwise apply(file:locale:month:) picks it up when the load
                // lands. Either way there is no timing guess.
                if let dayNum = viewModel.navigateToDay,
                   let target = viewModel.daysInMonth.first(where: { $0.gregorianDay == dayNum }) {
                    viewModel.selectedDay = target
                    viewModel.navigateToDay = nil
                }
            }
            .task(id: scenePhase) {
                // Each return to the foreground counts the day; the ask waits a
                // moment so it never lands on top of the calendar appearing, and
                // skips while a sheet is up so it never interrupts a reading.
                guard scenePhase == .active else { return }
                let prompt = ReviewPrompt()
                prompt.recordActive()
                guard prompt.shouldPrompt else { return }
                try? await Task.sleep(for: .seconds(2))
                guard !Task.isCancelled, viewModel.selectedDay == nil,
                      !viewModel.showSearch, !viewModel.showDatePicker else { return }
                requestReview()
                prompt.markPrompted()
            }
        }
    }

    /// A year the archive does not cover, as opposed to one that failed to
    /// download. Kept here rather than in the shared `ui` strings so the two
    /// apps' localization bundles stay byte-identical.
    private func noDataMessage(_ year: Int) -> String {
        switch localization.language {
        case .sr: return "Нема података за \(year). годину."
        case .ru: return "Нет данных за \(year) год."
        case .en, .en_nc: return "No calendar data for \(year)."
        }
    }
}

// MARK: - Load failure (offline / missing data for an on-demand year)

struct CalendarLoadFailureView: View {
    let message: String
    /// Matches the message: a crossed-out wifi symbol over "no data for 2100"
    /// would be as misleading as the text used to be.
    var systemImage: String = "wifi.slash"
    let onRetry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: systemImage)
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
                Text("☦\u{FE0E}")
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
