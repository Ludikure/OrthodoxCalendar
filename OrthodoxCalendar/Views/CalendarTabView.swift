import SwiftUI

struct CalendarTabView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var vm = viewModel

        NavigationStack {
            VStack(spacing: 0) {
                // Title
                CalendarTitle(year: $vm.currentYear, localization: localization)

                // Month header bar
                MonthHeaderBar(
                    currentMonth: $vm.currentMonth,
                    currentYear: $vm.currentYear,
                    daysCount: viewModel.daysInMonth.count,
                    localization: localization
                )

                // Day list
                MonthListView()
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(localization.ui.todayLabel) {
                        viewModel.goToToday()
                    }
                    .font(.subheadline)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 16) {
                        Button {
                            viewModel.showSearch = true
                        } label: {
                            Image(systemName: "magnifyingglass")
                        }
                        NavigationLink {
                            SettingsView()
                        } label: {
                            Image(systemName: "gearshape")
                        }
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $vm.showSearch) {
                SaintSearchView()
            }
        }
    }
}

// MARK: - Title

struct CalendarTitle: View {
    @Binding var year: Int
    let localization: LocalizationManager
    @State private var showYearPicker = false

    var body: some View {
        HStack(spacing: 6) {
            Text("✝")
                .foregroundStyle(AppColors.crimson)
            Text(localization.ui.appTitle)
                .font(.title2)
                .fontWeight(.bold)

            Button {
                showYearPicker = true
            } label: {
                HStack(spacing: 2) {
                    Text("\(String(year)).")
                        .font(.title2)
                        .fontWeight(.bold)
                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.semibold))
                }
                .foregroundStyle(.primary)
            }
        }
        .padding(.top, 8)
        .padding(.bottom, 4)
        .sheet(isPresented: $showYearPicker) {
            YearPickerView(selectedYear: $year, localization: localization)
                .presentationDetents([.medium])
        }
    }
}

// MARK: - Year Picker

struct YearPickerView: View {
    @Binding var selectedYear: Int
    let localization: LocalizationManager
    @Environment(\.dismiss) private var dismiss

    private let years = Array(2000...2099)

    var body: some View {
        NavigationStack {
            Picker("", selection: $selectedYear) {
                ForEach(years, id: \.self) { year in
                    Text(String(year)).tag(year)
                }
            }
            .pickerStyle(.wheel)
            .navigationTitle(yearTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(doneText) { dismiss() }
                }
            }
        }
    }

    private var yearTitle: String {
        switch localization.language {
        case .sr: return "Година"
        case .ru: return "Год"
        case .en: return "Year"
        }
    }

    private var doneText: String {
        switch localization.language {
        case .sr: return "Готово"
        case .ru: return "Готово"
        case .en: return "Done"
        }
    }
}

// MARK: - Month Header Bar

struct MonthHeaderBar: View {
    @Binding var currentMonth: Int
    @Binding var currentYear: Int
    let daysCount: Int
    let localization: LocalizationManager

    private let headerColor = Color(red: 0.45, green: 0.15, blue: 0.15)

    var body: some View {
        HStack(spacing: 0) {
            // Column headers
            HStack(spacing: 0) {
                columnHeader(dayLabel, width: 28)
                columnHeader(newLabel, width: 28)
                columnHeader(oldLabel, width: 28)
            }

            // Month navigation
            Button {
                goToPreviousMonth()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 4)

            Spacer()

            Text(localization.localizedMonthName(currentMonth))
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(.white)

            Spacer()

            Button {
                goToNextMonth()
            } label: {
                Image(systemName: "chevron.right")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 4)

            Text("\(daysCount > 0 ? "\(daysCount)" : "") \(daysLabel)")
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.8))
                .frame(width: 50, alignment: .trailing)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(headerColor)
    }

    private func columnHeader(_ text: String, width: CGFloat) -> some View {
        Text(text)
            .font(.system(size: 9))
            .foregroundStyle(.white.opacity(0.85))
            .frame(width: width, alignment: .center)
    }

    private var dayLabel: String {
        switch localization.language {
        case .sr: return "дан"
        case .ru: return "день"
        case .en: return "day"
        }
    }

    private var newLabel: String {
        switch localization.language {
        case .sr: return "нов"
        case .ru: return "нов"
        case .en: return "new"
        }
    }

    private var oldLabel: String {
        switch localization.language {
        case .sr: return "стар"
        case .ru: return "стар"
        case .en: return "old"
        }
    }

    private var daysLabel: String {
        switch localization.language {
        case .sr: return "дана"
        case .ru: return "дней"
        case .en: return "days"
        }
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
