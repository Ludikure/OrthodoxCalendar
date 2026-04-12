import SwiftUI
import EventKit

struct AddReminderView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss

    @State private var title: String = ""
    @State private var selectedAlerts: Set<AlertOption> = [.morningOf]
    @State private var customTime = Date()
    @State private var notes: String = ""
    @State private var permissionDenied = false
    @State private var showSuccess = false

    private let store = EKEventStore()

    enum AlertOption: String, CaseIterable, Identifiable {
        case morningOf
        case eveningBefore
        case dayBefore
        case twoDaysBefore
        case weekBefore
        case custom

        var id: String { rawValue }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField(titlePlaceholder, text: $title)

                    HStack {
                        Text(dateLabel)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(formattedDate)
                    }
                }

                Section(header: Text(alertLabel)) {
                    ForEach(AlertOption.allCases) { option in
                        Button {
                            if selectedAlerts.contains(option) {
                                selectedAlerts.remove(option)
                            } else {
                                selectedAlerts.insert(option)
                            }
                        } label: {
                            HStack {
                                Text(alertText(option))
                                    .foregroundStyle(.primary)
                                Spacer()
                                if selectedAlerts.contains(option) {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(AppColors.crimson)
                                }
                            }
                        }
                    }

                    if selectedAlerts.contains(.custom) {
                        DatePicker(customTimeLabel, selection: $customTime, displayedComponents: [.date, .hourAndMinute])
                    }
                }

                Section(header: Text(notesLabel)) {
                    TextField(notesLabel, text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle(addReminderTitle)
            .navigationBarTitleDisplayMode(.inline)
            .scrollDismissesKeyboard(.interactively)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(cancelText) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saveText) {
                        Task { await saveEvent() }
                    }
                    .fontWeight(.semibold)
                }
                ToolbarItem(placement: .keyboard) {
                    HStack {
                        Spacer()
                        Button {
                            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                        } label: {
                            Image(systemName: "keyboard.chevron.compact.down")
                        }
                    }
                }
            }
            .onAppear {
                if title.isEmpty { title = defaultTitle }
                // Set custom time default to 9am on the event date
                var components = Calendar(identifier: .gregorian).dateComponents([.year, .month, .day], from: eventDate)
                components.hour = 9
                customTime = Calendar(identifier: .gregorian).date(from: components) ?? eventDate
            }
            .alert(permissionDeniedTitle, isPresented: $permissionDenied) {
                Button("OK") { dismiss() }
            } message: {
                Text(permissionDeniedMessage)
            }
            .alert(savedTitle, isPresented: $showSuccess) {
                Button("OK") { dismiss() }
            } message: {
                Text(savedMessage)
            }
        }
    }

    // MARK: - Save

    private var eventDate: Date {
        day.date ?? Date()
    }

    private func saveEvent() async {
        do {
            let granted = try await store.requestFullAccessToEvents()
            guard granted else {
                permissionDenied = true
                return
            }
        } catch {
            permissionDenied = true
            return
        }

        // Check for duplicates
        let cal = Calendar(identifier: .gregorian)
        let dayStart = cal.startOfDay(for: eventDate)
        guard let dayEnd = cal.date(byAdding: .day, value: 1, to: dayStart) else { return }
        let predicate = store.predicateForEvents(withStart: dayStart, end: dayEnd, calendars: nil)
        let existing = store.events(matching: predicate)
        if existing.contains(where: { $0.title == title }) {
            showSuccess = true
            return
        }

        let event = EKEvent(eventStore: store)
        event.title = title
        event.isAllDay = true
        event.startDate = eventDate
        event.endDate = eventDate
        event.calendar = store.defaultCalendarForNewEvents
        event.notes = notes.isEmpty ? nil : notes

        // Add selected alarms
        for alert in selectedAlerts {
            var alarmDate: Date?
            switch alert {
            case .morningOf:
                alarmDate = cal.date(bySettingHour: 9, minute: 0, second: 0, of: eventDate)
            case .eveningBefore:
                if let evening = cal.date(byAdding: .day, value: -1, to: eventDate) {
                    alarmDate = cal.date(bySettingHour: 20, minute: 0, second: 0, of: evening)
                }
            case .dayBefore:
                if let dayBefore = cal.date(byAdding: .day, value: -1, to: eventDate) {
                    alarmDate = cal.date(bySettingHour: 9, minute: 0, second: 0, of: dayBefore)
                }
            case .twoDaysBefore:
                if let twoDays = cal.date(byAdding: .day, value: -2, to: eventDate) {
                    alarmDate = cal.date(bySettingHour: 9, minute: 0, second: 0, of: twoDays)
                }
            case .weekBefore:
                if let week = cal.date(byAdding: .day, value: -7, to: eventDate) {
                    alarmDate = cal.date(bySettingHour: 9, minute: 0, second: 0, of: week)
                }
            case .custom:
                alarmDate = customTime
            }
            if let alarmDate {
                event.addAlarm(EKAlarm(absoluteDate: alarmDate))
            }
        }

        do {
            try store.save(event, span: .thisEvent)
            showSuccess = true
        } catch {
            print("Failed to save calendar event: \(error)")
        }
    }

    // MARK: - Helpers

    private var defaultTitle: String {
        day.primaryFeast?.name ?? day.feasts.first?.name ?? ""
    }

    private var formattedDate: String {
        "\(day.gregorianDay) \(localization.localizedMonthName(day.gregorianMonth)) \(day.gregorianDate.prefix(4))"
    }

    private func alertText(_ option: AlertOption) -> String {
        switch option {
        case .morningOf:
            switch localization.language {
            case .sr: return "Ујутру тог дана (9:00)"
            case .ru: return "Утром в этот день (9:00)"
            case .en, .en_nc: return "Morning of (9:00)"
            }
        case .eveningBefore:
            switch localization.language {
            case .sr: return "Вече пре (20:00)"
            case .ru: return "Вечером накануне (20:00)"
            case .en, .en_nc: return "Evening before (8 PM)"
            }
        case .dayBefore:
            switch localization.language {
            case .sr: return "Дан раније (9:00)"
            case .ru: return "За день до (9:00)"
            case .en, .en_nc: return "Day before (9:00)"
            }
        case .twoDaysBefore:
            switch localization.language {
            case .sr: return "Два дана раније"
            case .ru: return "За два дня до"
            case .en, .en_nc: return "Two days before"
            }
        case .weekBefore:
            switch localization.language {
            case .sr: return "Недељу дана раније"
            case .ru: return "За неделю до"
            case .en, .en_nc: return "Week before"
            }
        case .custom:
            switch localization.language {
            case .sr: return "Прилагођено време"
            case .ru: return "Своё время"
            case .en, .en_nc: return "Custom time"
            }
        }
    }

    // MARK: - Labels

    private var addReminderTitle: String {
        switch localization.language {
        case .sr: return "Подсетник"
        case .ru: return "Напоминание"
        case .en, .en_nc: return "Reminder"
        }
    }

    private var titlePlaceholder: String {
        switch localization.language {
        case .sr: return "Назив"
        case .ru: return "Название"
        case .en, .en_nc: return "Title"
        }
    }

    private var dateLabel: String {
        switch localization.language {
        case .sr: return "Датум"
        case .ru: return "Дата"
        case .en, .en_nc: return "Date"
        }
    }

    private var alertLabel: String {
        switch localization.language {
        case .sr: return "Обавештења"
        case .ru: return "Уведомления"
        case .en, .en_nc: return "Alerts"
        }
    }

    private var customTimeLabel: String {
        switch localization.language {
        case .sr: return "Време"
        case .ru: return "Время"
        case .en, .en_nc: return "Custom time"
        }
    }

    private var notesLabel: String {
        switch localization.language {
        case .sr: return "Белешке"
        case .ru: return "Заметки"
        case .en, .en_nc: return "Notes"
        }
    }

    private var cancelText: String {
        switch localization.language {
        case .sr: return "Откажи"
        case .ru: return "Отмена"
        case .en, .en_nc: return "Cancel"
        }
    }

    private var saveText: String {
        switch localization.language {
        case .sr: return "Сачувај"
        case .ru: return "Сохранить"
        case .en, .en_nc: return "Save"
        }
    }

    private var permissionDeniedTitle: String {
        switch localization.language {
        case .sr: return "Нема приступа"
        case .ru: return "Нет доступа"
        case .en, .en_nc: return "No Access"
        }
    }

    private var permissionDeniedMessage: String {
        switch localization.language {
        case .sr: return "Дозволите приступ календару у Подешавањима."
        case .ru: return "Разрешите доступ к календарю в Настройках."
        case .en, .en_nc: return "Allow calendar access in Settings."
        }
    }

    private var savedTitle: String {
        switch localization.language {
        case .sr: return "Сачувано"
        case .ru: return "Сохранено"
        case .en, .en_nc: return "Saved"
        }
    }

    private var savedMessage: String {
        switch localization.language {
        case .sr: return "Подсетник је додат у календар."
        case .ru: return "Напоминание добавлено в календарь."
        case .en, .en_nc: return "Reminder added to calendar."
        }
    }
}
