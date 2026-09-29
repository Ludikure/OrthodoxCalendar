import SwiftUI

struct SettingsView: View {
    @Environment(LocalizationManager.self) private var localization
    @Environment(SlavaStore.self) private var slavaStore
    @Environment(NameDayStore.self) private var nameDayStore

    var body: some View {
        @Bindable var loc = localization

        Form {
            Section {
                LanguagePickerView()
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

            // English New Testament translation (KJV/WEB). Only relevant to the
            // English locales; the Old Testament always uses the Septuagint.
            if localization.language == .en || localization.language == .en_nc {
                Section {
                    Picker(selection: $loc.bibleTranslation) {
                        ForEach(BibleTranslation.allCases) { translation in
                            Text(translation.displayName).tag(translation)
                        }
                    } label: {
                        EmptyView()
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                } header: {
                    Text("Bible Translation")
                } footer: {
                    Text("New Testament wording. The Old Testament always uses the Septuagint.")
                }
            }

            // Krsna slava is a Serbian custom, so only the Serbian calendar offers it.
            if localization.language == .sr {
                Section {
                    NavigationLink {
                        SlavaSettingsView()
                    } label: {
                        HStack {
                            Text("🕯 Моја слава")
                            Spacer()
                            Text(slavaStore.settings.mine?.name ?? "")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            // Name days (именины) are kept in the Russian calendar only.
            if localization.language == .ru {
                Section {
                    NavigationLink {
                        NameDaySettingsView()
                    } label: {
                        HStack {
                            Label("Мои именины", systemImage: NameDayText.icon)
                            Spacer()
                            Text(nameDayStore.settings.mine.map { NameDayLabel.dayAndMonthOfNext($0.anchor) } ?? "")
                                .foregroundStyle(.secondary)
                        }
                    }
                }
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
