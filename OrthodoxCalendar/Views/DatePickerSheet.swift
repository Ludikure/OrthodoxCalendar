import SwiftUI

struct DatePickerSheet: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss

    @State private var mode: PickerMode = .month
    @State private var pickerYear: Int
    @State private var pickerMonth: Int

    enum PickerMode {
        case month, day
    }

    init(currentMonth: Int, currentYear: Int) {
        _pickerYear = State(initialValue: currentYear)
        _pickerMonth = State(initialValue: currentMonth)
    }

    var body: some View {
        VStack(spacing: 0) {
            // Drag handle
            RoundedRectangle(cornerRadius: 2)
                .fill(Color.secondary.opacity(0.3))
                .frame(width: 36, height: 4)
                .padding(.top, 10)
                .padding(.bottom, 6)

            // Title + close
            HStack {
                Text(mode == .month ? selectMonthLabel : selectDateLabel)
                    .font(.headline)
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 14)

            if mode == .month {
                monthGridView
            } else {
                dayCalendarView
            }

            // Today button
            Button {
                let cal = Calendar(identifier: .gregorian)
                let now = Date()
                viewModel.currentMonth = cal.component(.month, from: now)
                viewModel.currentYear = cal.component(.year, from: now)
                viewModel.scrollToTodayTrigger.toggle()
                dismiss()
            } label: {
                Text(todayButtonLabel)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(AppColors.crimson)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Month Grid (4×3)

    private var monthGridView: some View {
        VStack(spacing: 16) {
            // Year navigation
            HStack {
                Button { pickerYear -= 1 } label: {
                    Image(systemName: "chevron.left")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .disabled(pickerYear <= CalendarViewModel.minYear)
                .opacity(pickerYear <= CalendarViewModel.minYear ? 0.3 : 1)
                Spacer()
                Text(String(pickerYear))
                    .font(.title2.weight(.bold))
                Spacer()
                Button { pickerYear += 1 } label: {
                    Image(systemName: "chevron.right")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .disabled(pickerYear >= CalendarViewModel.maxYear)
                .opacity(pickerYear >= CalendarViewModel.maxYear ? 0.3 : 1)
            }
            .padding(.horizontal, 20)

            // 4×3 month grid
            let columns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 3)
            LazyVGrid(columns: columns, spacing: 8) {
                ForEach(0..<12, id: \.self) { i in
                    let month = i + 1
                    let isSelected = month == viewModel.currentMonth && pickerYear == viewModel.currentYear
                    let isCurrent = month == currentMonthNow && pickerYear == currentYearNow

                    Button {
                        viewModel.currentMonth = month
                        viewModel.currentYear = pickerYear
                        dismiss()
                    } label: {
                        VStack(spacing: 4) {
                            Text(localization.localizedMonthName(month))
                                .font(.subheadline.weight(isSelected ? .bold : .medium))

                            if isCurrent && !isSelected {
                                Circle()
                                    .fill(AppColors.crimson)
                                    .frame(width: 5, height: 5)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(isSelected ? Color.primary : Color.clear)
                        )
                        .foregroundStyle(isSelected ? Color(.systemBackground) : .primary)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(isCurrent && !isSelected ? AppColors.gold : Color.clear, lineWidth: 1.5)
                        )
                    }
                }
            }
            .padding(.horizontal, 16)

            // Switch to day mode
            Button {
                pickerMonth = viewModel.currentMonth
                mode = .day
            } label: {
                Text(exactDateLabel)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 13)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.secondary.opacity(0.3), lineWidth: 1.5)
                    )
            }
            .padding(.horizontal, 20)
        }
    }

    // MARK: - Day Calendar

    private var dayCalendarView: some View {
        VStack(spacing: 12) {
            // Month/year navigation
            HStack {
                let atMin = pickerYear <= CalendarViewModel.minYear && pickerMonth <= 1
                Button {
                    if pickerMonth == 1 { pickerMonth = 12; pickerYear -= 1 }
                    else { pickerMonth -= 1 }
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .disabled(atMin)
                .opacity(atMin ? 0.3 : 1)

                Spacer()

                Button { mode = .month } label: {
                    HStack(spacing: 4) {
                        Text(localization.localizedMonthName(pickerMonth))
                            .font(.headline)
                        Text(String(pickerYear))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Image(systemName: "chevron.up")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .foregroundStyle(.primary)

                Spacer()

                let atMax = pickerYear >= CalendarViewModel.maxYear && pickerMonth >= 12
                Button {
                    if pickerMonth == 12 { pickerMonth = 1; pickerYear += 1 }
                    else { pickerMonth += 1 }
                } label: {
                    Image(systemName: "chevron.right")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .disabled(atMax)
                .opacity(atMax ? 0.3 : 1)
            }
            .padding(.horizontal, 20)

            // Weekday headers
            let weekdayLabels = localization.bundle.ui.daysOfWeek
            HStack(spacing: 0) {
                // Reorder: Mon-Sun (index 1,2,3,4,5,6,0)
                ForEach([1,2,3,4,5,6,0], id: \.self) { i in
                    Text(String(weekdayLabels[i].prefix(2)))
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(i == 0 || i == 6 ? AppColors.crimson : .secondary)
                        .frame(maxWidth: .infinity)
                }
            }
            .padding(.horizontal, 16)

            // Day grid
            let columns = Array(repeating: GridItem(.flexible(), spacing: 3), count: 7)
            let (offset, numDays) = monthLayout(year: pickerYear, month: pickerMonth)

            LazyVGrid(columns: columns, spacing: 3) {
                // Leading empty cells
                ForEach(0..<offset, id: \.self) { i in
                    Color.clear.frame(height: 40)
                        .id("empty-\(i)")
                }

                // Day cells
                ForEach(1...numDays, id: \.self) { day in
                    let isToday = day == currentDayNow && pickerMonth == currentMonthNow && pickerYear == currentYearNow
                    let cellWeekday = (offset + day - 1) % 7
                    let isSunday = cellWeekday == 6
                    let isSaturday = cellWeekday == 5

                    Button {
                        viewModel.currentMonth = pickerMonth
                        viewModel.currentYear = pickerYear
                        viewModel.navigateToDay = day
                        dismiss()
                    } label: {
                        Text("\(day)")
                            .font(.subheadline.weight(isToday ? .bold : .medium))
                            .frame(maxWidth: .infinity)
                            .frame(height: 40)
                            .background(
                                RoundedRectangle(cornerRadius: 10)
                                    .fill(isToday ? Color.primary : Color.clear)
                            )
                            .foregroundStyle(
                                isToday ? Color(.systemBackground) :
                                (isSunday || isSaturday ? AppColors.crimson : .primary)
                            )
                    }
                }
            }
            .padding(.horizontal, 16)

            // Back to months
            Button { mode = .month } label: {
                Text(backToMonthsLabel)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 13)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.secondary.opacity(0.3), lineWidth: 1.5)
                    )
            }
            .padding(.horizontal, 20)
        }
    }

    // MARK: - Helpers

    private var currentYearNow: Int { Calendar(identifier: .gregorian).component(.year, from: Date()) }
    private var currentMonthNow: Int { Calendar(identifier: .gregorian).component(.month, from: Date()) }
    private var currentDayNow: Int { Calendar(identifier: .gregorian).component(.day, from: Date()) }

    private func monthLayout(year: Int, month: Int) -> (offset: Int, numDays: Int) {
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = 1
        let cal = Calendar(identifier: .gregorian)
        guard let firstDay = cal.date(from: components),
              let range = cal.range(of: .day, in: .month, for: firstDay) else {
            return (0, 30)
        }
        // weekday: 1=Sun..7=Sat → Mon-based offset (Mon=0)
        let weekday = cal.component(.weekday, from: firstDay)
        let offset = (weekday + 5) % 7 // Convert: Sun=6, Mon=0, Tue=1, ...
        return (offset, range.count)
    }

    // MARK: - Labels

    private var selectMonthLabel: String {
        switch localization.language {
        case .sr: return "Изаберите месец"
        case .ru: return "Выберите месяц"
        case .en: return "Select month"
        }
    }

    private var selectDateLabel: String {
        switch localization.language {
        case .sr: return "Изаберите датум"
        case .ru: return "Выберите дату"
        case .en: return "Select date"
        }
    }

    private var todayButtonLabel: String {
        switch localization.language {
        case .sr: return "Данас"
        case .ru: return "Сегодня"
        case .en: return "Today"
        }
    }

    private var exactDateLabel: String {
        switch localization.language {
        case .sr: return "Тачан датум"
        case .ru: return "Точная дата"
        case .en: return "Exact date"
        }
    }

    private var backToMonthsLabel: String {
        switch localization.language {
        case .sr: return "Назад на месеце"
        case .ru: return "Назад к месяцам"
        case .en: return "Back to months"
        }
    }
}
