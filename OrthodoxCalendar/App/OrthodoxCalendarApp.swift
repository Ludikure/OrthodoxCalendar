import SwiftUI

@main
struct OrthodoxCalendarApp: App {
    @State private var localization = LocalizationManager()
    @State private var viewModel = CalendarViewModel()
    @State private var updateGate = AppUpdateGate()

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
                        .onAppear {
                            viewModel.loadMonth()
                            Haptics.prepare()
                        }
                        .onChange(of: localization.language) {
                            viewModel.forceReload(locale: localization.language.rawValue)
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
                await updateGate.check()
            }
        }
    }
}
