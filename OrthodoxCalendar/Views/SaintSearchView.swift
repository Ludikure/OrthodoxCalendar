import SwiftUI

struct SaintSearchView: View {
    @Environment(LocalizationManager.self) private var localization
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(\.dismiss) private var dismiss

    @State private var query = ""
    @State private var results: [SaintSearchResult] = []
    @State private var searchTask: Task<Void, Never>?
    @State private var cachedFile: CalendarFile?
    @State private var cachedKey = ""
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
                searchTask?.cancel()
                searchTask = Task { @MainActor in
                    try? await Task.sleep(for: .milliseconds(200))
                    guard !Task.isCancelled else { return }
                    search()
                }
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

        let locale = localization.language.rawValue
        let key = "calendar_\(locale)_\(viewModel.currentYear)"

        // Cache decoded file to avoid re-parsing JSON on every keystroke
        if cachedKey != key {
            guard let url = Bundle.main.url(forResource: key, withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let file = try? JSONDecoder().decode(CalendarFile.self, from: data) else {
                results = []
                return
            }
            cachedFile = file
            cachedKey = key
        }

        guard let file = cachedFile else {
            results = []
            return
        }

        var found: [SaintSearchResult] = []
        for (_, day) in file.days {
            for feast in day.feasts {
                if feast.name.lowercased().contains(q) {
                    found.append(SaintSearchResult(
                        matchedText: feast.name,
                        gregorianMonth: day.gregorianMonth,
                        gregorianDay: day.gregorianDay,
                        language: localization.language
                    ))
                }
            }
        }

        results = Array(found.sorted { a, b in
            let aSort = String(format: "%02d-%02d", a.gregorianMonth ?? 0, a.gregorianDay ?? 0)
            let bSort = String(format: "%02d-%02d", b.gregorianMonth ?? 0, b.gregorianDay ?? 0)
            return aSort < bSort
        }.prefix(50))
    }

    // MARK: - Date Display

    private func dateDisplay(for result: SaintSearchResult) -> String {
        if let gm = result.gregorianMonth, let gd = result.gregorianDay {
            return "\(gd) \(localization.localizedMonthName(gm))"
        }
        return ""
    }

    // MARK: - Navigation

    private func navigateToDate(_ result: SaintSearchResult) {
        if let gm = result.gregorianMonth {
            viewModel.currentMonth = gm
            if let gd = result.gregorianDay {
                viewModel.navigateToDay = gd
            }
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
    var gregorianMonth: Int?
    var gregorianDay: Int?
    let language: AppLanguage
}
