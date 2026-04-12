import SwiftUI

struct CalendarGridView: View {
    @Environment(CalendarViewModel.self) private var viewModel
    @Environment(LocalizationManager.self) private var localization
    @State private var selectedGridDay: CalendarDay?
    @State private var initialized = false

    private var todayString: String {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        fmt.calendar = Calendar(identifier: .gregorian)
        return fmt.string(from: Date())
    }

    /// Weekday of the 1st day of the month (0=Mon..6=Sun for grid layout)
    private var firstDayOffset: Int {
        guard let first = viewModel.daysInMonth.first else { return 0 }
        // dayOfWeek is Python convention: 0=Mon..6=Sun — perfect for Mon-first grid
        return first.dayOfWeek
    }

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 4), count: 7)

    var body: some View {
        let today = todayString
        ScrollView {
            VStack(spacing: 0) {
                // Weekday headers
                weekdayHeaders

                // Grid
                LazyVGrid(columns: columns, spacing: 8) {
                    // Empty cells before month starts
                    ForEach(0..<firstDayOffset, id: \.self) { _ in
                        Color.clear
                            .frame(height: 46)
                    }

                    // Day cells
                    ForEach(viewModel.daysInMonth) { day in
                        GridDayCell(
                            day: day,
                            isToday: day.gregorianDate == today,
                            isSelected: selectedGridDay?.gregorianDate == day.gregorianDate
                        )
                        .onTapGesture {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                                selectedGridDay = day
                            }
                        }
                    }
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 8)

                // Selected day detail card (tap to open full detail)
                if let day = selectedGridDay {
                    SelectedDayCard(day: day)
                        .onTapGesture {
                            viewModel.selectedDay = day
                        }
                        .transition(.asymmetric(
                            insertion: .move(edge: .top).combined(with: .opacity),
                            removal: .opacity
                        ))
                        .padding(.horizontal, 16)
                        .padding(.bottom, 8)
                }

                // Legend
                FastingLegend()
                    .padding(.horizontal, 16)
                    .padding(.bottom, 20)
            }
            .background(AppColors.warmBg)
        }
        .background(AppColors.warmBg)
        .id(viewModel.loadedLocale)
        .onAppear { selectToday() }
        .onChange(of: viewModel.daysInMonth.count) { selectToday() }
    }

    private func selectToday() {
        let today = todayString
        if let todayDay = viewModel.daysInMonth.first(where: { $0.gregorianDate == today }) {
            selectedGridDay = todayDay
        } else if let first = viewModel.daysInMonth.first {
            selectedGridDay = first
        }
    }

    private var weekdayHeaders: some View {
        let abbrevs = localization.bundle.ui.daysOfWeek
        // Reorder: Mon-Sun (index 1,2,3,4,5,6,0)
        let ordered = [1, 2, 3, 4, 5, 6, 0]
        return HStack(spacing: 0) {
            ForEach(ordered, id: \.self) { i in
                Text(String(abbrevs[i].prefix(2)))
                    .font(.caption2.weight(.bold))
                    .tracking(0.5)
                    .foregroundStyle(i == 0 || i == 6 ? AppColors.crimson : AppColors.mutedText)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(AppColors.warmBorder)
    }
}

// MARK: - Grid Day Cell

struct GridDayCell: View {
    let day: CalendarDay
    let isToday: Bool
    let isSelected: Bool

    private var isGreat: Bool { day.isGreatFeast }
    private var isPascha: Bool { day.greatFeast == "pascha" }

    var body: some View {
        VStack(spacing: 2) {
            Text("\(day.gregorianDay)")
                .font(.system(.callout, design: .serif).weight(isGreat || isToday ? .bold : .medium))
                .foregroundStyle(
                    isPascha ? AppColors.goldAccent :
                    isGreat ? AppColors.crimson :
                    isToday ? .white :
                    day.isSunday ? AppColors.crimson :
                    AppColors.darkText
                )

            // Fasting dot
            fastingDot
        }
        .frame(maxWidth: .infinity)
        .frame(height: 46)
        .background(cellBackground)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(
                    isSelected ? AppColors.crimson :
                    isToday ? AppColors.gold :
                    Color.clear,
                    lineWidth: 2
                )
        )
        .overlay(alignment: .topTrailing) {
            if isGreat || isPascha {
                Text("✦")
                    .font(.system(size: 7))
                    .foregroundStyle(isPascha ? AppColors.goldAccent : AppColors.crimson)
                    .padding(3)
            }
        }
    }

    @ViewBuilder
    private var fastingDot: some View {
        let t = day.fasting.type.lowercased()
        if t != "free" {
            Circle()
                .fill(fastingColor(t))
                .frame(width: 6, height: 6)
        } else {
            Color.clear.frame(width: 6, height: 6)
        }
    }

    private var cellBackground: some ShapeStyle {
        if isPascha {
            return AnyShapeStyle(LinearGradient(
                colors: [AppColors.crimson, AppColors.crimson.opacity(0.8)],
                startPoint: .topLeading, endPoint: .bottomTrailing
            ))
        }
        if isToday {
            return AnyShapeStyle(AppColors.crimson)
        }
        if isGreat {
            return AnyShapeStyle(AppColors.crimson.opacity(0.08))
        }
        let t = day.fasting.type.lowercased()
        if t == "totalabstinence" || t == "dryeating" {
            return AnyShapeStyle(AppColors.fastStrict.opacity(0.08))
        }
        if t.contains("oil") {
            return AnyShapeStyle(AppColors.fastOil.opacity(0.08))
        }
        if t.contains("fish") {
            return AnyShapeStyle(AppColors.fastFish.opacity(0.08))
        }
        return AnyShapeStyle(Color.clear)
    }

    private func fastingColor(_ type: String) -> Color {
        if type == "totalabstinence" || type == "dryeating" { return AppColors.fastStrict }
        if type.contains("nooil") { return AppColors.fastWater }
        if type.contains("oil") { return AppColors.fastOil }
        if type.contains("fish") || type.contains("roe") { return AppColors.fastFish }
        return .clear
    }
}

// MARK: - Selected Day Card

struct SelectedDayCard: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization

    private var isPascha: Bool { day.greatFeast == "pascha" }
    private var isGreat: Bool { day.isGreatFeast }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if isGreat, day.primaryFeast != nil {
                Text("✦ \(greatFeastLabel)")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.5)
                    .foregroundStyle(isPascha ? AppColors.goldAccent : AppColors.crimson)
            }

            Text("\(day.gregorianDay). \(localization.localizedMonthName(day.gregorianMonth)) — \(day.primaryFeast?.name ?? "")")
                .font(.system(.body, design: .serif).weight(.semibold))
                .foregroundStyle(isPascha ? .white : AppColors.darkText)

            // Fasting info
            HStack(spacing: 6) {
                let t = day.fasting.type.lowercased()
                if t != "free" {
                    Circle()
                        .fill(fastingColor(t))
                        .frame(width: 8, height: 8)
                    Text(day.fasting.label)
                        .font(.caption)
                        .foregroundStyle(isPascha ? .white.opacity(0.7) : AppColors.mutedText)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(isPascha
                    ? AnyShapeStyle(LinearGradient(colors: [AppColors.crimson, AppColors.crimson.opacity(0.85)], startPoint: .topLeading, endPoint: .bottomTrailing))
                    : isGreat
                        ? AnyShapeStyle(AppColors.cardBg)
                        : AnyShapeStyle(AppColors.warmBorder))
        )
        .overlay(alignment: .leading) {
            Rectangle()
                .fill(isGreat ? AppColors.crimson : AppColors.warmBorder)
                .frame(width: 4)
                .clipShape(RoundedRectangle(cornerRadius: 2))
        }
    }

    private var greatFeastLabel: String {
        switch localization.language {
        case .sr: return "ВЕЛИКИ ПРАЗНИК"
        case .ru: return "ВЕЛИКИЙ ПРАЗДНИК"
        case .en, .en_nc: return "GREAT FEAST"
        }
    }

    private func fastingColor(_ type: String) -> Color {
        if type == "totalabstinence" || type == "dryeating" { return AppColors.fastStrict }
        if type.contains("nooil") { return AppColors.fastWater }
        if type.contains("oil") { return AppColors.fastOil }
        if type.contains("fish") || type.contains("roe") { return AppColors.fastFish }
        return .clear
    }
}

// MARK: - Fasting Legend

struct FastingLegend: View {
    var body: some View {
        HStack(spacing: 16) {
            legendItem(color: AppColors.fastOil, label: "Уље")
            legendItem(color: AppColors.fastFish, label: "Риба")
            legendItem(color: AppColors.fastStrict, label: "Строги")
            legendItem(color: AppColors.crimson, label: "Празник")
        }
        .frame(maxWidth: .infinity)
    }

    private func legendItem(color: Color, label: String) -> some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.system(size: 11))
                .foregroundStyle(AppColors.mutedText)
        }
    }
}
