import SwiftUI

/// Full-screen, non-dismissable gate shown when the installed version is below
/// the server-required minimum. The only action is to open the App Store.
struct UpdateRequiredView: View {
    let appStoreURL: URL?
    let localization: LocalizationManager
    @Environment(\.openURL) private var openURL

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            Text("✝")
                .font(.system(size: 40))
                .foregroundStyle(AppColors.crimson)

            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 52))
                .foregroundStyle(AppColors.crimson)

            Text(localization.ui.updateRequiredTitle ?? "Update Required")
                .font(.system(.title2, design: .serif).weight(.bold))
                .foregroundStyle(AppColors.darkText)
                .multilineTextAlignment(.center)

            Text(localization.ui.updateRequiredMessage
                 ?? "A new version is required to continue. Please update the app.")
                .font(.body)
                .foregroundStyle(AppColors.mutedText)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Spacer()

            if let url = appStoreURL {
                Button {
                    Haptics.medium()
                    openURL(url)
                } label: {
                    Text(localization.ui.updateButton ?? "Update")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(AppColors.crimson)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 40)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.warmBg)
        .interactiveDismissDisabled()
    }
}
