import SwiftUI

/// App color constants with light/dark mode support
enum AppColors {
    // MARK: - Brand colors (same in both modes)
    static let gold = Color(red: 0.831, green: 0.686, blue: 0.216)
    static let crimson = Color(red: 0.788, green: 0.251, blue: 0.251)
    static let feastBlue = Color(red: 0.345, green: 0.510, blue: 0.690)
    static let holyWeekPurple = Color(red: 0.502, green: 0.376, blue: 0.627)
    static let brightGold = Color(red: 0.831, green: 0.753, blue: 0.502)
    static let fastFreeGreen = Color(red: 0.353, green: 0.541, blue: 0.314)

    // MARK: - Adaptive colors (light/dark)

    /// Dark brown header background
    static let headerBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.12, green: 0.10, blue: 0.07, alpha: 1)
            : UIColor(red: 0.173, green: 0.141, blue: 0.094, alpha: 1)
    })

    /// Page background
    static let warmBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.systemBackground
            : UIColor(red: 0.961, green: 0.953, blue: 0.933, alpha: 1)
    })

    /// Gold accent
    static let goldAccent = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.75, green: 0.68, blue: 0.55, alpha: 1)
            : UIColor(red: 0.831, green: 0.773, blue: 0.663, alpha: 1)
    })

    /// Muted text
    static let mutedText = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.secondaryLabel
            : UIColor(red: 0.549, green: 0.494, blue: 0.416, alpha: 1)
    })

    /// Warm border / divider
    static let warmBorder = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.separator
            : UIColor(red: 0.941, green: 0.929, blue: 0.910, alpha: 1)
    })

    /// Card background
    static let cardBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.secondarySystemBackground
            : UIColor(red: 0.980, green: 0.980, blue: 0.965, alpha: 1)
    })

    /// Primary text
    static let darkText = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.label
            : UIColor(red: 0.173, green: 0.141, blue: 0.094, alpha: 1)
    })

    /// Light muted
    static let lightMuted = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.tertiaryLabel
            : UIColor(red: 0.690, green: 0.643, blue: 0.557, alpha: 1)
    })

    /// Body text secondary
    static let bodyText = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor.secondaryLabel
            : UIColor(red: 0.361, green: 0.314, blue: 0.251, alpha: 1)
    })

    // MARK: - Fasting colors (same in both modes — badge backgrounds adapt via opacity)

    static let fastStrict = Color(red: 0.482, green: 0.176, blue: 0.557)
    static let fastStrictBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.482, green: 0.176, blue: 0.557, alpha: 0.2)
            : UIColor(red: 0.953, green: 0.910, blue: 0.969, alpha: 1)
    })
    static let fastWater = Color(red: 0.180, green: 0.490, blue: 0.608)
    static let fastWaterBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.180, green: 0.490, blue: 0.608, alpha: 0.2)
            : UIColor(red: 0.894, green: 0.949, blue: 0.969, alpha: 1)
    })
    static let fastOil = Color(red: 0.545, green: 0.482, blue: 0.176)
    static let fastOilBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.545, green: 0.482, blue: 0.176, alpha: 0.2)
            : UIColor(red: 1.0, green: 0.973, blue: 0.882, alpha: 1)
    })
    static let fastFish = Color(red: 0.176, green: 0.420, blue: 0.310)
    static let fastFishBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.176, green: 0.420, blue: 0.310, alpha: 0.2)
            : UIColor(red: 0.910, green: 0.961, blue: 0.925, alpha: 1)
    })
    static let fastFree = Color(red: 0.290, green: 0.486, blue: 0.247)
    static let fastFreeBg = Color(UIColor { tc in
        tc.userInterfaceStyle == .dark
            ? UIColor(red: 0.290, green: 0.486, blue: 0.247, alpha: 0.2)
            : UIColor(red: 0.929, green: 0.969, blue: 0.918, alpha: 1)
    })
}
