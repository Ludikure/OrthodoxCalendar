import SwiftUI

struct SettingsView: View {
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        @Bindable var loc = localization

        Form {
            Section {
                LanguagePickerView()
            } header: {
                Text(localization.ui.settingsLabel)
            }

            Section {
                Picker(AppTheme.sectionTitle(for: localization.language),
                       selection: $loc.theme) {
                    ForEach(AppTheme.allCases) { theme in
                        Text(theme.displayName(for: localization.language)).tag(theme)
                    }
                }
                .pickerStyle(.inline)
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
