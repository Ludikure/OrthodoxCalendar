import SwiftUI

struct SplashScreenView: View {
    @State private var isActive = false
    @State private var opacity = 1.0
    @State private var scale = 0.8

    var body: some View {
        if isActive {
            CalendarTabView()
        } else {
            ZStack {
                AppColors.headerBg
                    .ignoresSafeArea()

                VStack(spacing: 24) {
                    // Try asset catalog first, fall back to bundle file
                    Group {
                        if let img = UIImage(named: "splash_logo") {
                            Image(uiImage: img)
                                .resizable()
                        } else if let url = Bundle.main.url(forResource: "splash_logo", withExtension: "png"),
                                  let data = try? Data(contentsOf: url),
                                  let uiImg = UIImage(data: data) {
                            Image(uiImage: uiImg)
                                .resizable()
                        } else {
                            Image(systemName: "cross")
                                .resizable()
                        }
                    }
                    .scaledToFit()
                    .frame(width: 180, height: 180)
                    .clipShape(RoundedRectangle(cornerRadius: 36))
                    .shadow(color: .black.opacity(0.3), radius: 20, y: 10)
                    .scaleEffect(scale)

                    VStack(spacing: 6) {
                        Text(splashTitle)
                            .font(.system(.title2, design: .serif).weight(.bold))
                            .foregroundStyle(.white)

                        Text(splashSubtitle)
                            .font(.system(.subheadline, design: .serif))
                            .foregroundStyle(AppColors.goldAccent)
                    }
                }
                .opacity(opacity)
            }
            .onAppear {
                withAnimation(.easeOut(duration: 0.6)) {
                    scale = 1.0
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    withAnimation(.easeInOut(duration: 0.4)) {
                        opacity = 0
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                        isActive = true
                    }
                }
            }
        }
    }

    private var savedLanguage: AppLanguage {
        UserDefaults.standard.string(forKey: "appLanguage")
            .flatMap(AppLanguage.init(rawValue:)) ?? .sr
    }

    private var splashTitle: String {
        switch savedLanguage {
        case .sr: return "Православни Календар"
        case .ru: return "Православный Календарь"
        case .en: return "Orthodox Calendar"
        }
    }

    private var splashSubtitle: String {
        switch savedLanguage {
        case .sr: return "Црквени Календар"
        case .ru: return "Церковный Календарь"
        case .en: return "Church Calendar"
        }
    }
}
