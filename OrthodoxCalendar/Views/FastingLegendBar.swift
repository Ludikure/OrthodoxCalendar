import SwiftUI

struct FastingLegendBar: View {
    var body: some View {
        HStack(spacing: 12) {
            legendItem(icon: "🚫", color: AppColors.fastStrict)
            legendItem(icon: "💧", color: AppColors.fastWater)
            legendItem(icon: "🫒", color: AppColors.fastOil)
            legendItem(icon: "🐟", color: AppColors.fastFish)
            legendItem(icon: "✓", color: AppColors.fastFree)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
        .background(AppColors.warmBorder)
    }

    private func legendItem(icon: String, color: Color) -> some View {
        Text(icon)
            .font(.system(size: 11))
            .foregroundStyle(color)
    }
}
