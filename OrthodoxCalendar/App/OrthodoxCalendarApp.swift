import SwiftUI

@main
struct OrthodoxCalendarApp: App {
    @State private var localization = LocalizationManager()
    @State private var viewModel: CalendarViewModel

    init() {
        let loc = LocalizationManager()
        _localization = State(initialValue: loc)
        _viewModel = State(initialValue: CalendarViewModel(localizationManager: loc))
    }

    var body: some Scene {
        WindowGroup {
            CalendarTabView()
                .environment(localization)
                .environment(viewModel)
                .preferredColorScheme(localization.theme.colorScheme)
                .task {
                    await viewModel.loadMonth()
                }
                .task {
                    await viewModel.startBackgroundPrefetch()
                }
                .onChange(of: localization.language) {
                    Task { await viewModel.loadMonth() }
                }
                .onChange(of: viewModel.currentMonth) {
                    Task { await viewModel.loadMonth() }
                }
                .onChange(of: viewModel.currentYear) {
                    Task { await viewModel.loadMonth() }
                }
        }
    }
}
