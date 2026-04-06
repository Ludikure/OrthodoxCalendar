import SwiftUI

/// App color constants — inline definitions to avoid asset catalog lookup issues
enum AppColors {
    static let gold = Color(red: 0.831, green: 0.686, blue: 0.216)
    static let crimson = Color(red: 0.788, green: 0.251, blue: 0.251)
    static let feastBlue = Color(red: 0.345, green: 0.510, blue: 0.690)
    static let holyWeekPurple = Color(red: 0.502, green: 0.376, blue: 0.627)
    static let brightGold = Color(red: 0.831, green: 0.753, blue: 0.502)
    static let fastFreeGreen = Color(red: 0.353, green: 0.541, blue: 0.314)

    // MARK: - Redesign palette

    /// Dark brown header background #2C2418
    static let headerBg = Color(red: 0.173, green: 0.141, blue: 0.094)

    /// Warm gray page background #F5F3EE
    static let warmBg = Color(red: 0.961, green: 0.953, blue: 0.933)

    /// Gold accent #D4C5A9
    static let goldAccent = Color(red: 0.831, green: 0.773, blue: 0.663)

    /// Muted text color #8C7E6A
    static let mutedText = Color(red: 0.549, green: 0.494, blue: 0.416)

    /// Warm border / divider color #F0EDE8
    static let warmBorder = Color(red: 0.941, green: 0.929, blue: 0.910)

    /// Subtle warm background for cards #FAFAF6
    static let cardBg = Color(red: 0.980, green: 0.980, blue: 0.965)

    /// Dark text #2C2418 (same as headerBg, used for body text)
    static let darkText = Color(red: 0.173, green: 0.141, blue: 0.094)

    /// Lighter muted #B0A48E
    static let lightMuted = Color(red: 0.690, green: 0.643, blue: 0.557)

    /// Body text secondary #5C5040
    static let bodyText = Color(red: 0.361, green: 0.314, blue: 0.251)

    // MARK: - Fasting colors (from mockup)

    static let fastStrict = Color(red: 0.482, green: 0.176, blue: 0.557)   // #7B2D8E
    static let fastStrictBg = Color(red: 0.953, green: 0.910, blue: 0.969) // #F3E8F7
    static let fastWater = Color(red: 0.180, green: 0.490, blue: 0.608)    // #2E7D9B
    static let fastWaterBg = Color(red: 0.894, green: 0.949, blue: 0.969)  // #E4F2F7
    static let fastOil = Color(red: 0.545, green: 0.482, blue: 0.176)      // #8B7B2D
    static let fastOilBg = Color(red: 1.0, green: 0.973, blue: 0.882)      // #FFF8E1
    static let fastFish = Color(red: 0.176, green: 0.420, blue: 0.310)     // #2D6B4F
    static let fastFishBg = Color(red: 0.910, green: 0.961, blue: 0.925)   // #E8F5EC
    static let fastFree = Color(red: 0.290, green: 0.486, blue: 0.247)     // #4A7C3F
    static let fastFreeBg = Color(red: 0.929, green: 0.969, blue: 0.918)   // #EDF7EA
}
