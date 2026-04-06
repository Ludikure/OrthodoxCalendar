import SwiftUI

struct SaintSearchView: View {
    @Environment(LocalizationManager.self) private var localization
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(\.dismiss) private var dismiss

    @State private var query = ""
    @State private var results: [SaintSearchResult] = []
    @FocusState private var isSearchFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search field
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(.secondary)
                    TextField(searchPrompt, text: $query)
                        .focused($isSearchFocused)
                        .autocorrectionDisabled()
                    if !query.isEmpty {
                        Button {
                            query = ""
                            results = []
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding(10)
                .background(Color(.systemGray6))
                .cornerRadius(10)
                .padding(.horizontal)
                .padding(.vertical, 8)

                // Results
                List {
                    if results.isEmpty && query.count >= 2 {
                        Text(noResultsText)
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(results) { result in
                            Button {
                                navigateToDate(result)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(result.matchedText)
                                        .font(.subheadline)
                                        .foregroundStyle(.primary)
                                        .lineLimit(2)

                                    Text(dateDisplay(for: result))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                .padding(.vertical, 2)
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
            .navigationTitle(searchTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(doneText) { dismiss() }
                }
            }
            .onChange(of: query) {
                search()
            }
            .onAppear {
                isSearchFocused = true
            }
        }
    }

    // MARK: - Search

    private func search() {
        let q = query.lowercased().trimmingCharacters(in: .whitespaces)
        guard q.count >= 2 else {
            results = []
            return
        }

        var found: [SaintSearchResult] = []
        let lang = localization.language

        if lang == .sr {
            let data = SerbianCalendarData.shared
            for (julianKey, entry) in data.fixedByJulianDate {
                if entry.description.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: entry.description,
                        julianKey: julianKey,
                        paschaDistance: nil,
                        language: .sr
                    ))
                }
            }
            for (dist, entry) in data.moveableByPaschaDistance {
                if entry.description.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: entry.description,
                        julianKey: nil,
                        paschaDistance: Int(dist),
                        language: .sr
                    ))
                }
            }
        } else if lang == .ru {
            let data = RussianCalendarData.shared
            for (julianKey, entry) in data.fixedByJulianDate {
                if entry.description.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: entry.description,
                        julianKey: julianKey,
                        paschaDistance: nil,
                        language: .ru
                    ))
                }
            }
            for (dist, entry) in data.moveableByPaschaDistance {
                if entry.description.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: entry.description,
                        julianKey: nil,
                        paschaDistance: Int(dist),
                        language: .ru
                    ))
                }
            }
        } else {
            // English: search API data indexed from all 12 months
            for entry in viewModel.englishSearchIndex {
                if entry.text.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: entry.text,
                        julianKey: nil,
                        paschaDistance: nil,
                        gregorianMonth: entry.month,
                        gregorianDay: entry.day,
                        language: .en
                    ))
                }
            }
            // Also search extraFeasts from en.json (has "Christmas" etc.)
            for extra in localization.bundle.extraFeasts {
                if extra.name.lowercased().contains(q) {
                    let jkey = String(format: "%02d-%02d", extra.julianMonth, extra.julianDay)
                    found.append(SaintSearchResult(
                        matchedText: extra.name,
                        julianKey: jkey,
                        paschaDistance: nil,
                        language: .en
                    ))
                }
            }
            // Deduplicate — extraFeasts may overlap with API index
            var seen = Set<String>()
            found = found.filter { seen.insert($0.matchedText).inserted }
        }

        // Sort by date
        results = Array(found.sorted { a, b in
            let aSort = a.gregorianMonth.map { String(format: "%02d-%02d", $0, a.gregorianDay ?? 0) }
                ?? a.julianKey
                ?? "99"
            let bSort = b.gregorianMonth.map { String(format: "%02d-%02d", $0, b.gregorianDay ?? 0) }
                ?? b.julianKey
                ?? "99"
            return aSort < bSort
        }.prefix(50))
    }

    // MARK: - Date Display

    private func dateDisplay(for result: SaintSearchResult) -> String {
        let year = viewModel.currentYear

        if let jk = result.julianKey {
            let parts = jk.split(separator: "-")
            if let jm = Int(parts[0]), let jd = Int(parts[1]),
               let greg = JulianConverter.gregorianDate(julianMonth: jm, julianDay: jd, year: year) {
                let cal = Calendar(identifier: .gregorian)
                let day = cal.component(.day, from: greg)
                let month = cal.component(.month, from: greg)
                return "\(day) \(localization.localizedMonthName(month))"
            }
        }
        if let pdist = result.paschaDistance,
           let paschaDate = PaschaCalculator.pascha(for: year) {
            let cal = Calendar(identifier: .gregorian)
            if let feastDate = cal.date(byAdding: .day, value: pdist, to: paschaDate) {
                let day = cal.component(.day, from: feastDate)
                let month = cal.component(.month, from: feastDate)
                return "\(day) \(localization.localizedMonthName(month))"
            }
        }
        // Direct Gregorian date (from API index)
        if let gm = result.gregorianMonth, let gd = result.gregorianDay {
            return "\(gd) \(localization.localizedMonthName(gm))"
        }
        return ""
    }

    // MARK: - Navigation

    private func navigateToDate(_ result: SaintSearchResult) {
        if let julianKey = result.julianKey {
            let parts = julianKey.split(separator: "-")
            if let jm = Int(parts[0]), let jd = Int(parts[1]) {
                if let greg = JulianConverter.gregorianDate(julianMonth: jm, julianDay: jd, year: viewModel.currentYear) {
                    viewModel.currentMonth = Calendar(identifier: .gregorian).component(.month, from: greg)
                    dismiss()
                }
            }
        } else if let pdist = result.paschaDistance {
            if let paschaDate = PaschaCalculator.pascha(for: viewModel.currentYear) {
                if let feastDate = Calendar(identifier: .gregorian).date(byAdding: .day, value: pdist, to: paschaDate) {
                    viewModel.currentMonth = Calendar(identifier: .gregorian).component(.month, from: feastDate)
                    dismiss()
                }
            }
        } else if let gm = result.gregorianMonth {
            viewModel.currentMonth = gm
            dismiss()
        }
    }

    // MARK: - Localized labels

    private var searchTitle: String {
        switch localization.language {
        case .sr: return "Претрага"
        case .ru: return "Поиск"
        case .en: return "Search"
        }
    }

    private var searchPrompt: String {
        switch localization.language {
        case .sr: return "Име светитеља или празника"
        case .ru: return "Имя святого или праздника"
        case .en: return "Saint or feast name"
        }
    }

    private var noResultsText: String {
        switch localization.language {
        case .sr: return "Нема резултата"
        case .ru: return "Ничего не найдено"
        case .en: return "No results"
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

struct SaintSearchResult: Identifiable {
    let id = UUID()
    let matchedText: String
    let julianKey: String?
    let paschaDistance: Int?
    var gregorianMonth: Int?
    var gregorianDay: Int?
    let language: AppLanguage
}
