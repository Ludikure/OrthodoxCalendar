import SwiftUI

/// Settings › Мои именины: the user's name day, reminders, and friends' name
/// days. Russian only, so its text is Russian throughout.
struct NameDaySettingsView: View {
    @Environment(NameDayStore.self) private var store

    var body: some View {
        @Bindable var store = store

        Form {
            Section {
                if let mine = store.settings.mine {
                    NavigationLink {
                        NameDayEditor(title: "Мои именины", initial: mine) { pick($0) }
                    } label: {
                        NameDayLabel(choice: mine)
                    }
                    Button("Удалить именины", role: .destructive) {
                        store.settings.mine = nil
                    }
                } else {
                    NavigationLink {
                        NameDayEditor(title: "Мои именины") { pick($0) }
                    } label: {
                        Text("Указать имя и день рождения")
                            .foregroundStyle(AppColors.crimson)
                    }
                }
            } header: {
                Text("Именины")
            } footer: {
                Text("По обычаю Церкви именины — первый после дня рождения день памяти святого, чьё имя вы носите. Если вы знаете своего святого, выберите его сами.")
            }

            Section {
                Toggle("В день именин", isOn: $store.settings.remindOnDay)
                Toggle("Именины друзей — в тот же день", isOn: $store.settings.remindFriends)
                Toggle("Именины друзей — накануне", isOn: $store.settings.remindFriendsDayBefore)
                DatePicker("Время", selection: reminderTime, displayedComponents: .hourAndMinute)
                    .environment(\.locale, Locale(identifier: "ru_RU"))
            } header: {
                Text("Напоминания")
            }
            .tint(AppColors.crimson)

            Section {
                ForEach(store.settings.friends) { friend in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(friend.displayName)
                        Text("\(friend.nameDay.churchName) · \(NameDayLabel.when(friend.nameDay.anchor))")
                            .font(.caption)
                            .foregroundStyle(AppColors.mutedText)
                    }
                }
                .onDelete { store.settings.friends.remove(atOffsets: $0) }

                NavigationLink {
                    NameDayEditor(title: "Именины друга", isFriend: true) { choice, person in
                        store.settings.friends.append(FriendNameDay(person: person, nameDay: choice))
                        askForNotifications()
                    }
                } label: {
                    Label("Добавить именины", systemImage: "plus")
                        .foregroundStyle(AppColors.crimson)
                }
            } header: {
                Text("Именины друзей")
            }
        }
        .navigationTitle("Мои именины")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func pick(_ choice: NameDayChoice) {
        store.settings.mine = choice
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

/// A name day: the church name over the saint and when it falls.
struct NameDayLabel: View {
    let choice: NameDayChoice

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Image(systemName: NameDayText.icon)
                    .foregroundStyle(AppColors.slavaGold)
                Text(choice.name == choice.churchName ? choice.name : "\(choice.name) (\(choice.churchName))")
                    .font(.system(.body, design: .serif).weight(.semibold))
            }
            Text(Self.when(choice.anchor))
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppColors.slavaGold)
            Text(choice.title)
                .font(.caption)
                .foregroundStyle(AppColors.mutedText)
                .lineLimit(3)
        }
    }

    /// "25 января (12 января по ст. ст.)", or for one that moves
    /// "переходящая, ближайшая 26 апреля".
    static func when(_ anchor: NameDayAnchor, from now: Date = Date()) -> String {
        let civil = anchor.nextOccurrence(onOrAfter: now).map(dayAndMonth) ?? ""
        switch anchor {
        case .julian(let m, let d):
            return "\(civil) (\(d) \(NameDayReminders.monthsGenitive[(m - 1) % 12]) по ст. ст.)"
        case .pascha, .weekday:
            return "переходящая, ближайшая \(civil)"
        }
    }

    /// "25 января": the next date, for the Settings row.
    static func dayAndMonthOfNext(_ anchor: NameDayAnchor) -> String {
        anchor.nextOccurrence(onOrAfter: Date()).map(dayAndMonth) ?? ""
    }

    static func dayAndMonth(_ date: Date) -> String {
        let c = ChurchDates.calendar.dateComponents([.month, .day], from: date)
        return "\(c.day ?? 1) \(NameDayReminders.monthsGenitive[((c.month ?? 1) - 1) % 12])"
    }
}

// MARK: - Editor

/// Finds a name day from a first name and a birthday — the first commemoration
/// of the name on or after it — or lets the user choose the saint.
struct NameDayEditor: View {
    let title: String
    var isFriend = false
    let onSave: (NameDayChoice, String) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var person = ""
    @State private var name = ""
    @State private var knowsBirthday = true
    @State private var birthMonth = 1
    @State private var birthDay = 1
    /// A saint chosen by hand; cleared when the name changes.
    @State private var manual: NameDayCatalog.Commemoration?
    @FocusState private var nameFocused: Bool

    private let catalog = NameDayCatalog.shared

    init(title: String, initial: NameDayChoice? = nil, onSave: @escaping (NameDayChoice) -> Void) {
        self.title = title
        self.onSave = { choice, _ in onSave(choice) }
        _name = State(initialValue: initial?.name ?? "")
        if let initial {
            if let m = initial.birthMonth, let d = initial.birthDay {
                _birthMonth = State(initialValue: m)
                _birthDay = State(initialValue: d)
            } else {
                _knowsBirthday = State(initialValue: false)
                _manual = State(initialValue: NameDayCatalog.Commemoration(
                    name: initial.churchName, anchor: initial.anchor, title: initial.title, isNewMartyr: false))
            }
        }
    }

    init(title: String, isFriend: Bool, onSave: @escaping (NameDayChoice, String) -> Void) {
        self.title = title
        self.isFriend = isFriend
        self.onSave = onSave
    }

    private var forms: [String] { catalog.churchForms(for: name) }

    private var trimmedName: String { name.trimmingCharacters(in: .whitespaces) }

    /// The name day found from the birthday.
    private var found: (commemoration: NameDayCatalog.Commemoration, date: Date)? {
        guard knowsBirthday else { return nil }
        let year = ChurchDates.calendar.component(.year, from: Date())
        return catalog.firstNameDay(churchForms: forms, birthMonth: birthMonth, birthDay: birthDay, year: year)
    }

    private var chosen: NameDayCatalog.Commemoration? { manual ?? found?.commemoration }

    var body: some View {
        Form {
            Section {
                if isFriend {
                    TextField("Кто (например, мама, кум Сергей)", text: $person)
                }
                TextField("Имя", text: $name)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
                    .focused($nameFocused)
                    .onChange(of: name) { manual = nil }
                if nameFocused {
                    ForEach(suggestions, id: \.name) { s in
                        Button {
                            name = s.name
                            nameFocused = false
                        } label: {
                            HStack {
                                Text(s.name).foregroundStyle(AppColors.darkText)
                                Spacer()
                                if s.church != s.name {
                                    Text(s.church).font(.caption).foregroundStyle(AppColors.mutedText)
                                }
                            }
                        }
                    }
                }
            } header: {
                Text(isFriend ? "Кто и как зовут" : "Ваше имя")
            } footer: {
                nameFooter
            }

            Section {
                Toggle("Знаю день рождения", isOn: $knowsBirthday.animation())
                    .tint(AppColors.crimson)
                if knowsBirthday {
                    Picker("Месяц", selection: $birthMonth) {
                        ForEach(1...12, id: \.self) { m in
                            Text(Self.monthsNominative[m - 1]).tag(m)
                        }
                    }
                    Picker("День", selection: $birthDay) {
                        ForEach(1...Self.daysIn(birthMonth), id: \.self) { d in
                            Text("\(d)").tag(d)
                        }
                    }
                    .onChange(of: birthMonth) {
                        birthDay = min(birthDay, Self.daysIn(birthMonth))
                        manual = nil
                    }
                    .onChange(of: birthDay) { manual = nil }
                }
            } header: {
                Text("День рождения")
            }

            if let chosen {
                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(NameDayLabel.when(chosen.anchor))
                            .font(.system(.title3, design: .serif).weight(.bold))
                            .foregroundStyle(AppColors.slavaGold)
                        Text(chosen.title)
                            .font(.subheadline)
                            .foregroundStyle(AppColors.bodyText)
                    }
                    .padding(.vertical, 4)
                } header: {
                    Text(manual == nil ? "Именины" : "Выбранный святой")
                } footer: {
                    if manual == nil {
                        Text("Первый день памяти святого с именем \(chosen.name) после дня рождения.")
                    }
                }
            }

            if !trimmedName.isEmpty {
                Section {
                    NavigationLink {
                        NameDaySaintPicker(churchNames: forms) { manual = $0 }
                    } label: {
                        Label(forms.isEmpty ? "Выбрать святого" : "Выбрать другого святого или день",
                              systemImage: "list.bullet")
                            .foregroundStyle(AppColors.crimson)
                    }
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Сохранить") { save() }
                    .disabled(chosen == nil || trimmedName.isEmpty)
            }
        }
    }

    @ViewBuilder private var nameFooter: some View {
        if trimmedName.isEmpty {
            Text("Можно обычное имя (Иван, Таня) или церковное (Иоанн, Татиана).")
        } else if forms.isEmpty {
            Text("Святого с именем «\(trimmedName)» в календаре нет. Обычно при крещении дают созвучное или близкое по смыслу имя — выберите святого вручную.")
        } else if forms != [trimmedName] {
            Text("Церковное имя: \(forms.joined(separator: " или "))")
        }
    }

    private var suggestions: [(name: String, church: String)] {
        let s = catalog.suggestions(trimmedName)
        return s.count == 1 && s[0].name == trimmedName ? [] : s
    }

    private func save() {
        guard let chosen else { return }
        let choice = NameDayChoice(
            name: trimmedName, churchName: chosen.name, title: chosen.title, anchor: chosen.anchor,
            birthMonth: manual == nil && knowsBirthday ? birthMonth : nil,
            birthDay: manual == nil && knowsBirthday ? birthDay : nil)
        Haptics.light()
        onSave(choice, person.trimmingCharacters(in: .whitespaces))
        dismiss()
    }

    static let monthsNominative = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    static func daysIn(_ month: Int) -> Int {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][(month - 1) % 12]
    }
}

// MARK: - Saint picker

/// Every commemoration of the given church names, in calendar order, and a
/// search over all names for a saint the name doesn't lead to.
struct NameDaySaintPicker: View {
    let churchNames: [String]
    let onPick: (NameDayCatalog.Commemoration) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    private let catalog = NameDayCatalog.shared

    var body: some View {
        List {
            let shown = query.trimmingCharacters(in: .whitespaces).isEmpty
                ? churchNames
                : catalog.churchNames(matching: query)
            if shown.isEmpty {
                Text(query.isEmpty ? "Найдите святого по имени" : "Ничего не найдено")
                    .foregroundStyle(AppColors.mutedText)
            }
            ForEach(shown, id: \.self) { name in
                Section(name) {
                    ForEach(sorted(catalog.commemorations(of: name))) { c in
                        Button {
                            Haptics.light()
                            onPick(c)
                            dismiss()
                        } label: {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(NameDayLabel.when(c.anchor))
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(AppColors.darkText)
                                Text(c.isNewMartyr ? "\(c.title) · новомученики" : c.title)
                                    .font(.caption)
                                    .foregroundStyle(AppColors.mutedText)
                                    .lineLimit(3)
                            }
                        }
                    }
                }
            }
        }
        .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Имя святого")
        .autocorrectionDisabled()
        .navigationTitle("Выбор святого")
        .navigationBarTitleDisplayMode(.inline)
    }

    /// Calendar order from 1 January, by this year's (or the next) date.
    private func sorted(_ list: [NameDayCatalog.Commemoration]) -> [NameDayCatalog.Commemoration] {
        let cal = ChurchDates.calendar
        let jan1 = cal.date(from: DateComponents(year: cal.component(.year, from: Date()), month: 1, day: 1)) ?? Date()
        let keyed = list.map { c -> (NameDayCatalog.Commemoration, Date) in
            (c, c.anchor.nextOccurrence(onOrAfter: jan1) ?? .distantFuture)
        }
        return keyed.sorted { $0.1 < $1.1 }.map(\.0)
    }
}
