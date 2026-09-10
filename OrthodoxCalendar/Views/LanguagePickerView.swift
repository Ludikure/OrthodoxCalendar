import SwiftUI

struct LanguagePickerView: View {
    @Environment(LocalizationManager.self) private var localization

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
        // No reload callback here: OrthodoxCalendarApp observes localization.language
        // and reloads the month once. A second forceReload from here (and from
        // SettingsView, which used to forward it) only made the same year load
        // twice, cancelling the first, and flickered the spinner.
    }
}
