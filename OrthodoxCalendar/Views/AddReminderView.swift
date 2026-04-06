import SwiftUI
import EventKit

struct AddReminderView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss

    @State private var title: String = ""
    @State private var alertOption: AlertOption = .morningOf
    @State private var notes: String = ""
    @State private var permissionDenied = false
    @State private var showSuccess = false

    private let store = EKEventStore()

    enum AlertOption: String, CaseIterable, Identifiable {
        case none = "none"
        case morningOf = "morningOf"
        case dayBefore = "dayBefore"
        case weekBefore = "weekBefore"

        var id: String { rawValue }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField(titlePlaceholder, text: $title)

                    // Date (read-only)
                    HStack {
                        Text(dateLabel)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(formattedDate)
                    }
                }

                Section(header: Text(alertLabel)) {
                    Picker(alertLabel, selection: $alertOption) {
                        Text(noAlertText).tag(AlertOption.none)
                        Text(morningOfText).tag(AlertOption.morningOf)
                        Text(dayBeforeText).tag(AlertOption.dayBefore)
                        Text(weekBeforeText).tag(AlertOption.weekBefore)
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
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
                if title.isEmpty {
                    title = defaultTitle
                }
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

        let event = EKEvent(eventStore: store)
        event.title = title
        event.isAllDay = true
        event.startDate = eventDate
        event.endDate = eventDate
        event.calendar = store.defaultCalendarForNewEvents
        event.notes = notes.isEmpty ? nil : notes

        // Set alarm
        switch alertOption {
        case .none:
            break
        case .morningOf:
            // 9:00 AM on the day
            event.isAllDay = false
            var components = Calendar(identifier: .gregorian).dateComponents([.year, .month, .day], from: eventDate)
            components.hour = 9
            components.minute = 0
            if let date = Calendar(identifier: .gregorian).date(from: components) {
                event.startDate = date
                event.endDate = date.addingTimeInterval(3600)
            }
            event.addAlarm(EKAlarm(relativeOffset: 0))
        case .dayBefore:
            event.addAlarm(EKAlarm(relativeOffset: -86400)) // 24h before
        case .weekBefore:
            event.addAlarm(EKAlarm(relativeOffset: -604800)) // 7 days before
        }

        do {
            try store.save(event, span: .thisEvent)
            showSuccess = true
        } catch {
            // Could show error, but success alert covers the happy path
        }
    }

    // MARK: - Default title

    private var defaultTitle: String {
        day.primaryFeast?.name ?? day.feasts.first?.name ?? ""
    }

    private var formattedDate: String {
        "\(day.gregorianDay) \(localization.localizedMonthName(day.gregorianMonth)) \(day.gregorianDate.prefix(4))"
    }

    // MARK: - Localized labels

    private var addReminderTitle: String {
        switch localization.language {
        case .sr: return "Подсетник"
        case .ru: return "Напоминание"
        }
    }

    private var titlePlaceholder: String {
        switch localization.language {
        case .sr: return "Назив"
        case .ru: return "Название"
        }
    }

    private var dateLabel: String {
        switch localization.language {
        case .sr: return "Датум"
        case .ru: return "Дата"
        }
    }

    private var alertLabel: String {
        switch localization.language {
        case .sr: return "Обавештење"
        case .ru: return "Уведомление"
        }
    }

    private var noAlertText: String {
        switch localization.language {
        case .sr: return "Без обавештења"
        case .ru: return "Без уведомления"
        }
    }

    private var morningOfText: String {
        switch localization.language {
        case .sr: return "Ујутру тог дана (9:00)"
        case .ru: return "Утром в этот день (9:00)"
        }
    }

    private var dayBeforeText: String {
        switch localization.language {
        case .sr: return "Дан раније"
        case .ru: return "За день до"
        }
    }

    private var weekBeforeText: String {
        switch localization.language {
        case .sr: return "Недељу дана раније"
        case .ru: return "За неделю до"
        }
    }

    private var notesLabel: String {
        switch localization.language {
        case .sr: return "Белешке"
        case .ru: return "Заметки"
        }
    }

    private var cancelText: String {
        switch localization.language {
        case .sr: return "Откажи"
        case .ru: return "Отмена"
        }
    }

    private var saveText: String {
        switch localization.language {
        case .sr: return "Сачувај"
        case .ru: return "Сохранить"
        }
    }

    private var permissionDeniedTitle: String {
        switch localization.language {
        case .sr: return "Нема приступа"
        case .ru: return "Нет доступа"
        }
    }

    private var permissionDeniedMessage: String {
        switch localization.language {
        case .sr: return "Дозволите приступ календару у Подешавањима."
        case .ru: return "Разрешите доступ к календарю в Настройках."
        }
    }

    private var savedTitle: String {
        switch localization.language {
        case .sr: return "Сачувано"
        case .ru: return "Сохранено"
        }
    }

    private var savedMessage: String {
        switch localization.language {
        case .sr: return "Подсетник је додат у календар."
        case .ru: return "Напоминание добавлено в календарь."
        }
    }
}
