import SwiftUI

struct LanguagePickerView: View {
    @Environment(LocalizationManager.self) private var localization
    var onLanguageChanged: ((String) -> Void)?

    var body: some View {
        VStack {
            ForEach(AppLanguage.allCases) { lang in
                Button {
                    localization.language = lang
                    onLanguageChanged?(lang.rawValue)
                } label: {
                    HStack {
                        Text(lang.displayName)
                            .foregroundStyle(.primary)
                        Spacer()
                        if localization.language == lang {
                            Image(systemName: "checkmark")
                                .foregroundStyle(AppColors.crimson)
                        }
                    }
                    .padding(.vertical, 8)
                }
            }
        }
    }
}
