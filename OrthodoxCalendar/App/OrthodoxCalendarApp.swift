import SwiftUI

@main
struct OrthodoxCalendarApp: App {
    @State private var localization = LocalizationManager()
    @State private var viewModel = CalendarViewModel()

    var body: some Scene {
        WindowGroup {
            CalendarTabView()
                .environment(localization)
                .environment(viewModel)
                .preferredColorScheme(localization.theme.colorScheme)
                .tint(AppColors.crimson)
                .onAppear {
                    viewModel.loadMonth()
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
}
