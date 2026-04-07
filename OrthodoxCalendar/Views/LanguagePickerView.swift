import SwiftUI

struct LanguagePickerView: View {
    @Environment(LocalizationManager.self) private var localization
    var onLanguageChanged: ((String) -> Void)?

    var body: some View {
        @Bindable var loc = localization

        Picker(selection: $loc.language) {
            ForEach(AppLanguage.allCases) { lang in
                Text(lang.displayName).tag(lang)
            }
        } label: {
            EmptyView()
        }
        .pickerStyle(.inline)
        .labelsHidden()
        .onChange(of: localization.language) {
            onLanguageChanged?(localization.language.rawValue)
        }
    }
}
