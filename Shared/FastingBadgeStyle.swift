import SwiftUI

/// The fasting badge's icon and colours for a `FastingInfo.type`: the calendar
/// row and the widgets draw the same badge from it.
struct FastingBadgeStyle {
    let icon: String
    let color: Color
    let background: Color

    init(type: String) {
        let t = type.lowercased()
        if t == "totalabstinence" {
            (icon, color, background) = ("🚫", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if t == "dryeating" {
            (icon, color, background) = ("🍞", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if t.contains("nooil") {
            (icon, color, background) = ("💧", AppColors.fastWater, AppColors.fastWaterBg)
        } else if t.contains("oil") {
            (icon, color, background) = ("🫒", AppColors.fastOil, AppColors.fastOilBg)
        } else if t.contains("fish") || t.contains("roe") {
            (icon, color, background) = ("🐟", AppColors.fastFish, AppColors.fastFishBg)
        } else {
            (icon, color, background) = ("✓", AppColors.fastFree, AppColors.fastFreeBg)
        }
    }
}
