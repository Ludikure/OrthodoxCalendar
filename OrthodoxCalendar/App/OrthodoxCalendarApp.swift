import SwiftUI

@main
struct OrthodoxCalendarApp: App {
    @State private var localization = LocalizationManager()
    @State private var viewModel = CalendarViewModel()
    @State private var updateGate = AppUpdateGate()
    @State private var slava = SlavaStore()
    @Environment(\.scenePhase) private var scenePhase

    private func rescheduleSlavaReminders() {
        SlavaReminders.update(slava.settings, language: localization.language)
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
                        .onAppear {
                            viewModel.loadMonth()
                            Haptics.prepare()
                        }
                        .onChange(of: localization.language) {
                            viewModel.forceReload(locale: localization.language.rawValue)
                            rescheduleSlavaReminders()
                        }
                        .onChange(of: viewModel.currentMonth) {
                            viewModel.loadMonth()
                        }
                        .onChange(of: viewModel.currentYear) {
                            viewModel.loadMonth()
                        }
                }
            }
            .preferredColorScheme(localization.theme.colorScheme)
            .tint(AppColors.crimson)
            .task {
                slava.onChange = { rescheduleSlavaReminders() }
                rescheduleSlavaReminders()
                await updateGate.check()
            }
            .onChange(of: scenePhase) {
                // A reminder a year out is scheduled for its date; coming back
                // to the app tops the queue up with the next occurrence.
                if scenePhase == .active { rescheduleSlavaReminders() }
            }
        }
    }
}
