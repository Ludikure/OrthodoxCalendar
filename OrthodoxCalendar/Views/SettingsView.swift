import SwiftUI

struct SettingsView: View {
    @Environment(LocalizationManager.self) private var localization
    var onLanguageChanged: ((String) -> Void)?

    var body: some View {
        @Bindable var loc = localization

        Form {
            Section {
                LanguagePickerView(onLanguageChanged: onLanguageChanged)
            } header: {
                Text(localization.ui.settingsLabel)
            }

            Section {
                Picker(selection: $loc.theme) {
                    ForEach(AppTheme.allCases) { theme in
                        Text(theme.displayName(for: localization.language)).tag(theme)
                    }
                } label: {
                    EmptyView()
                }
                .pickerStyle(.inline)
                .labelsHidden()
            } header: {
                Text(AppTheme.sectionTitle(for: localization.language))
            }

            Section {
                HStack {
                    Text("Version")
                    Spacer()
                    Text("1.0.0")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle(localization.ui.settingsLabel)
        .navigationBarTitleDisplayMode(.inline)
    }
}
