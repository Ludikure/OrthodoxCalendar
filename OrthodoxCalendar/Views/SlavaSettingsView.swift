import SwiftUI

/// Settings › Моја слава: the user's krsna slava, reminders, and friends'
/// slavas. Serbian only, so its text is Serbian throughout.
struct SlavaSettingsView: View {
    @Environment(SlavaStore.self) private var store
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var store = store

        Form {
            Section {
                if let mine = store.settings.mine {
                    NavigationLink {
                        SlavaPickerView(title: "Промени славу") { pick($0) }
                    } label: {
                        SlavaLabel(slava: mine)
                    }
                    Button("Уклони славу", role: .destructive) {
                        store.settings.mine = nil
                    }
                } else {
                    NavigationLink {
                        SlavaPickerView(title: "Изаберите славу") { pick($0) }
                    } label: {
                        Text("Изаберите славу")
                            .foregroundStyle(AppColors.crimson)
                    }
                }
            } header: {
                Text("Крсна слава")
            } footer: {
                Text("Слава се памти по црквеном календару, па сваке године пада на прави дан.")
            }

            Section {
                Toggle("Недељу дана пре", isOn: $store.settings.remindWeekBefore)
                Toggle("На дан славе", isOn: $store.settings.remindOnDay)
                Toggle("Дан пре славе пријатеља", isOn: $store.settings.remindFriends)
                DatePicker("Време", selection: reminderTime, displayedComponents: .hourAndMinute)
                    .environment(\.locale, Locale(identifier: "sr_RS"))
            } header: {
                Text("Подсетници")
            }
            .tint(AppColors.crimson)

            Section {
                ForEach(store.settings.friends) { friend in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(friend.person)
                        Text("\(friend.slava.name) · \(SlavaLabel.when(friend.slava, localization))")
                            .font(.caption)
                            .foregroundStyle(AppColors.mutedText)
                    }
                }
                .onDelete { store.settings.friends.remove(atOffsets: $0) }

                NavigationLink {
                    FriendSlavaEditor { friend in
                        store.settings.friends.append(friend)
                        askForNotifications()
                    }
                } label: {
                    Label("Додај славу", systemImage: "plus")
                        .foregroundStyle(AppColors.crimson)
                }
            } header: {
                Text("Славе пријатеља")
            }
        }
        .navigationTitle("Моја слава")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func pick(_ slava: SlavaDay) {
        store.settings.mine = slava
        askForNotifications()
    }

    /// Asked for only when there is something to remind about, never at launch.
    private func askForNotifications() {
        Task {
            await SlavaReminders.requestAuthorization()
            store.onChange?()
        }
    }

    private var reminderTime: Binding<Date> {
        Binding {
            let start = ChurchDates.startOfDay(Date())
            return ChurchDates.calendar.date(byAdding: .minute, value: store.settings.reminderMinutes, to: start) ?? start
        } set: { date in
            let c = ChurchDates.calendar.dateComponents([.hour, .minute], from: date)
            store.settings.reminderMinutes = (c.hour ?? 9) * 60 + (c.minute ?? 0)
        }
    }
}

/// A slava's name over when it falls this year.
struct SlavaLabel: View {
    let slava: SlavaDay
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("🕯 \(slava.name)")
                .font(.system(.body, design: .serif).weight(.semibold))
            Text("\(slava.saint) · \(Self.when(slava, localization))")
                .font(.caption)
                .foregroundStyle(AppColors.mutedText)
        }
    }

    /// "19. децембар (6. децембар по старом)", or for a moveable slava
    /// "покретна, следећа 21. мај".
    @MainActor
    static func when(_ slava: SlavaDay, _ localization: LocalizationManager) -> String {
        let next = slava.nextOccurrence(onOrAfter: Date())
        let civil = next.map {
            let c = ChurchDates.calendar.dateComponents([.month, .day], from: $0)
            return localization.dayAndMonth(c.day ?? 1, c.month ?? 1)
        } ?? ""
        switch slava.anchor {
        case .pascha:
            return "покретна, следећа \(civil)"
        case .julian(let m, let d):
            return "\(civil) (\(localization.dayAndMonth(d, m)) по старом)"
        }
    }
}

// MARK: - Picker

/// Chooses a slava: the common ones first, then any commemoration in the
/// calendar by search, then a date the calendar doesn't name.
struct SlavaPickerView: View {
    let title: String
    let onPick: (SlavaDay) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(LocalizationManager.self) private var localization
    @State private var query = ""
    /// Every fixed commemoration in the Serbian calendar, one per church date and name.
    @State private var calendarSaints: [SlavaDay] = []
    @State private var showCustom = false
    @State private var customPick: SlavaDay?

    var body: some View {
        List {
            if folded.isEmpty {
                Section("Покретне славе") {
                    ForEach(SlavaCatalog.moveable) { row($0) }
                }
                Section("Честе славе") {
                    ForEach(SlavaCatalog.fixed) { row($0) }
                }
            } else {
                let common = SlavaCatalog.common.filter(matches)
                if !common.isEmpty {
                    Section("Честе славе") {
                        ForEach(common) { row($0) }
                    }
                }
                let others = calendarMatches
                if !others.isEmpty {
                    Section("Из календара") {
                        ForEach(others) { row($0) }
                    }
                }
                if common.isEmpty && others.isEmpty {
                    Text("Нема резултата")
                        .foregroundStyle(AppColors.mutedText)
                }
            }

            Section {
                Button {
                    showCustom = true
                } label: {
                    Label("Други датум", systemImage: "calendar.badge.plus")
                        .foregroundStyle(AppColors.crimson)
                }
            } footer: {
                Text("Ако ваше славе нема у календару, унесите њен назив и датум.")
            }
        }
        .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always),
                    prompt: "Слава или светитељ")
        .autocorrectionDisabled()
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadCalendarSaints() }
        .sheet(isPresented: $showCustom, onDismiss: {
            if let customPick { choose(customPick) }
        }) {
            CustomSlavaView { slava in
                customPick = slava
                showCustom = false
            }
        }
    }

    private func row(_ slava: SlavaDay) -> some View {
        Button {
            choose(slava)
        } label: {
            VStack(alignment: .leading, spacing: 2) {
                Text(slava.name)
                    .font(.system(.body, design: .serif).weight(.semibold))
                    .foregroundStyle(AppColors.darkText)
                Text(slava.name == slava.saint
                     ? SlavaLabel.when(slava, localization)
                     : "\(slava.saint) · \(SlavaLabel.when(slava, localization))")
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
            }
        }
    }

    private func choose(_ slava: SlavaDay) {
        Haptics.light()
        onPick(slava)
        dismiss()
    }

    private var folded: String {
        SaintSearchView.fold(query.trimmingCharacters(in: .whitespaces))
    }

    private func matches(_ slava: SlavaDay) -> Bool {
        let q = folded
        return SaintSearchView.fold(slava.name).contains(q) || SaintSearchView.fold(slava.saint).contains(q)
    }

    /// Calendar commemorations matching the query, minus what the common list
    /// already shows for the same church date.
    private var calendarMatches: [SlavaDay] {
        guard folded.count >= 2 else { return [] }
        let commonDates = Set(SlavaCatalog.fixed.filter(matches).map(\.anchor))
        return Array(calendarSaints.lazy
            .filter { matches($0) && !commonDates.contains($0.anchor) }
            .prefix(50))
    }

    /// Reads one Serbian year for its fixed commemorations: they sit on the same
    /// church date every year, so any year serves. Moveable feasts are left to
    /// the common list, which anchors them to Pascha.
    private func loadCalendarSaints() async {
        guard calendarSaints.isEmpty else { return }
        let year = ChurchDates.calendar.component(.year, from: Date())
        guard let file = try? await CalendarRepository.shared.load(locale: "sr", year: year) else { return }
        var seen = Set<String>()
        var out: [SlavaDay] = []
        for day in file.days.values.sorted(by: { $0.gregorianDate < $1.gregorianDate }) {
            let parts = day.julianDate.split(separator: "-").compactMap { Int($0) }
            guard parts.count == 2 else { continue }
            for feast in day.feasts where !feast.moveable && !feast.name.isEmpty {
                let slava = SlavaDay(feast.name, feast.name, .julian(month: parts[0], day: parts[1]))
                if seen.insert(slava.id).inserted { out.append(slava) }
            }
        }
        calendarSaints = out
    }
}

/// A slava the calendar doesn't name: a name and a date, kept by church date.
struct CustomSlavaView: View {
    let onSave: (SlavaDay) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(LocalizationManager.self) private var localization
    @State private var name = ""
    @State private var date = Date()

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Назив славе", text: $name)
                    DatePicker("Датум", selection: $date, displayedComponents: .date)
                        .environment(\.locale, Locale(identifier: "sr_RS"))
                } footer: {
                    let j = ChurchDates.julian(from: date)
                    Text("По старом календару: \(localization.dayAndMonth(j.day, j.month)). Слава ће сваке године падати на тај дан.")
                }
            }
            .navigationTitle("Други датум")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Откажи") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Сачувај") {
                        let j = ChurchDates.julian(from: date)
                        let title = name.trimmingCharacters(in: .whitespaces)
                        onSave(SlavaDay(title, title, .julian(month: j.month, day: j.day)))
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

/// Adds a friend's slava: who, and which slava.
struct FriendSlavaEditor: View {
    let onSave: (FriendSlava) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var person = ""
    @State private var slava: SlavaDay?

    var body: some View {
        Form {
            Section {
                TextField("Име (нпр. Петровићи, кум Марко)", text: $person)
                NavigationLink {
                    SlavaPickerView(title: "Њихова слава") { slava = $0 }
                } label: {
                    if let slava {
                        SlavaLabel(slava: slava)
                    } else {
                        Text("Изаберите славу")
                            .foregroundStyle(AppColors.crimson)
                    }
                }
            }
        }
        .navigationTitle("Слава пријатеља")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Сачувај") {
                    guard let slava else { return }
                    onSave(FriendSlava(person: person.trimmingCharacters(in: .whitespaces), slava: slava))
                    dismiss()
                }
                .disabled(slava == nil || person.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
    }
}
