import SwiftUI

@main
struct OrthodoxCalendarApp: App {
    @State private var localization = LocalizationManager()
    @State private var viewModel = CalendarViewModel()
    @State private var updateGate = AppUpdateGate()
    @State private var slava = SlavaStore()
    @State private var nameDays = NameDayStore()
    @Environment(\.scenePhase) private var scenePhase

    private func rescheduleSlavaReminders() {
        SlavaReminders.update(slava.settings, language: localization.language)
        NameDayReminders.update(nameDays.settings, language: localization.language)
    }

    private func refreshWidgets() {
        WidgetSync.refresh(language: localization.language, ui: localization.ui, mySlava: slava.settings.mine)
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if updateGate.mustUpdate {
                    UpdateRequiredView(appStoreURL: updateGate.appStoreURL,
                                       localization: localization)
                } else {
                    SplashScreenView()
                        .environment(localization)
                        .environment(viewModel)
                        .environment(slava)
                        .environment(nameDays)
                        .onAppear {
                            viewModel.loadMonth()
                            Haptics.prepare()
                        }
                        .onChange(of: localization.language) {
                            viewModel.forceReload(locale: localization.language.rawValue)
                            rescheduleSlavaReminders()
                            refreshWidgets()
                        }
                        .onChange(of: viewModel.currentMonth) {
                            viewModel.loadMonth()
                        }
                        .onChange(of: viewModel.currentYear) {
                            viewModel.loadMonth()
                        }
                        .onChange(of: viewModel.isLoading) {
                            // The current year just finished loading (perhaps
                            // downloaded): the widgets can now be written.
                            if !viewModel.isLoading, viewModel.loadedFile?.year == Calendar.current.component(.year, from: Date()) {
                                refreshWidgets()
                            }
                        }
                        .onOpenURL { url in
                            // The widgets link to orthodoxcalendar://today.
                            if url.scheme == "orthodoxcalendar" { viewModel.openToday() }
                        }
                }
            }
            .preferredColorScheme(localization.theme.colorScheme)
            .tint(AppColors.crimson)
            .task {
                slava.onChange = {
                    rescheduleSlavaReminders()
                    refreshWidgets()
                }
                nameDays.onChange = {
                    NameDayReminders.update(nameDays.settings, language: localization.language)
                }
                rescheduleSlavaReminders()
                refreshWidgets()
                await updateGate.check()
            }
            .onChange(of: scenePhase) {
                // A reminder a year out is scheduled for its date; coming back
                // to the app tops the queue up with the next occurrence.
                if scenePhase == .active {
                    rescheduleSlavaReminders()
                    refreshWidgets()
                }
            }
        }
    }
}
