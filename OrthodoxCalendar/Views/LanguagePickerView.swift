import SwiftUI

struct LanguagePickerView: View {
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var loc = localization

        Picker(localization.ui.settingsLabel, selection: $loc.language) {
            ForEach(AppLanguage.allCases) { lang in
                Text(lang.displayName).tag(lang)
            }
        }
        .pickerStyle(.inline)
        .labelsHidden()
    }
}
