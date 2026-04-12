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
                NavigationLink {
                    AboutView()
                } label: {
                    Text(aboutLabel)
                }
            }

            Section {
                HStack {
                    Text(versionLabel)
                    Spacer()
                    Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle(localization.ui.settingsLabel)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var aboutLabel: String {
        switch localization.language {
        case .sr: return "О апликацији"
        case .ru: return "О приложении"
        case .en, .en_nc: return "About"
        }
    }

    private var versionLabel: String {
        switch localization.language {
        case .sr: return "Верзија"
        case .ru: return "Версия"
        case .en, .en_nc: return "Version"
        }
    }
}
