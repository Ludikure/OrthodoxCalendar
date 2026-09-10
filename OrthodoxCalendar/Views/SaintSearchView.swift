import SwiftUI

struct SaintSearchView: View {
    @Environment(LocalizationManager.self) private var localization
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(\.dismiss) private var dismiss

    @State private var query = ""
    @State private var results: [SaintSearchResult] = []
    @State private var searchTask: Task<Void, Never>?
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

        // Search the year already resolved by the calendar (bundle, disk cache,
        // or network) rather than re-reading the bundle — so it also works for
        // fetched years that aren't bundled on device.
        guard let file = viewModel.loadedFile else {
            results = []
            return
        }

        // Fold both sides to one script before comparing: the `sr` data is
        // Cyrillic-only while Serbian is read in both scripts, so "Nikola" or
        // "Sava" used to return nothing at all. Display keeps the original text.
        let foldedQuery = Self.fold(q)
        var found: [SaintSearchResult] = []
        var seen: Set<String> = []
        for (_, day) in file.days {
            for feast in day.feasts {
                let result = SaintSearchResult(
                    matchedText: feast.name,
                    gregorianMonth: day.gregorianMonth,
                    gregorianDay: day.gregorianDay,
                    language: localization.language
                )
                // The id is (date, name), so it has to be unique — a day can
                // list the same commemoration twice (a repose and a translation
                // of relics), and duplicate ids make ForEach misbehave.
                guard Self.fold(feast.name).contains(foldedQuery), seen.insert(result.id).inserted else {
                    continue
                }
                found.append(result)
            }
        }

        results = Array(found.sorted { a, b in
            let aSort = String(format: "%02d-%02d", a.gregorianMonth ?? 0, a.gregorianDay ?? 0)
            let bSort = String(format: "%02d-%02d", b.gregorianMonth ?? 0, b.gregorianDay ?? 0)
            return aSort < bSort
        }.prefix(50))
    }

    /// Lowercase and fold both scripts to one form so either matches the other.
    /// Lossy by design (it decides what to show, never what the data says).
    ///
    /// The target is Serbian Latin, because that is the bi-script case this
    /// exists for: Serbian is read in both alphabets and the `sr` data is
    /// Cyrillic-only. So ч/ћ/ц fold to `c` and ш to `s` — a Russian
    /// romanization ("ch", "sh", "ts") would leave "Cirilo" and "Cedomir"
    /// matching nothing. Latin diacritics fold the same way, so a query typed
    /// properly as "Ćirilo" or "Šišman" lands on the same string. Folding is
    /// applied to both sides, so same-script search is unaffected either way.
    static func fold(_ text: String) -> String {
        text.lowercased().map { folding[$0] ?? "\($0)" }.joined()
    }

    private static let folding: [Character: String] = [
        // Serbian Cyrillic, in Serbian Latin. љ/њ were absent before, so every
        // name containing them ("Љубомир", "Њиш") was unreachable from Latin.
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "dj", "е": "e",
        "ж": "z", "з": "z", "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj",
        "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p", "р": "r", "с": "s",
        "т": "t", "ћ": "c", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "c",
        "џ": "dz", "ш": "s",
        // Russian-only letters, folded consistently with the above.
        "ё": "e", "й": "i", "щ": "sc", "ъ": "", "ы": "i", "ь": "", "э": "e",
        "ю": "ju", "я": "ja",
        // Other Cyrillic that turns up in transliterated sources.
        "є": "je", "ї": "ji", "і": "i", "ў": "u", "ґ": "g", "ѣ": "e",
        "ѳ": "th", "ѵ": "i",
        // Latin diacritics, so a correctly typed Serbian query folds identically.
        "đ": "dj", "ć": "c", "č": "c", "š": "s", "ž": "z",
    ]

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
        case .en, .en_nc: return "Search"
        }
    }

    private var searchPrompt: String {
        switch localization.language {
        case .sr: return "Име светитеља или празника"
        case .ru: return "Имя святого или праздника"
        case .en, .en_nc: return "Saint or feast name"
        }
    }

    private var noResultsText: String {
        switch localization.language {
        case .sr: return "Нема резултата"
        case .ru: return "Ничего не найдено"
        case .en, .en_nc: return "No results"
        }
    }

    private var doneText: String {
        switch localization.language {
        case .sr: return "Готово"
        case .ru: return "Готово"
        case .en, .en_nc: return "Done"
        }
    }
}

struct SaintSearchResult: Identifiable {
    /// Stable across keystrokes (it used to be a fresh UUID, so every debounced
    /// search threw away all row identity: the list rebuilt, scroll position
    /// reset, and rows animated from scratch).
    var id: String {
        "\(gregorianMonth ?? 0)-\(gregorianDay ?? 0)-\(matchedText)"
    }
    let matchedText: String
    var gregorianMonth: Int?
    var gregorianDay: Int?
    let language: AppLanguage
}
