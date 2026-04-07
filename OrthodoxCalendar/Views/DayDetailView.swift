import SwiftUI

struct DayDetailView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss
    @State private var showAddReminder = false
    @State private var expandedSection: String?

    private var calendar: Calendar { Calendar(identifier: .gregorian) }

    private var isGreat: Bool { day.isGreatFeast }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    heroSection
                    contentSections
                }
            }
            .background(AppColors.warmBg)
            .navigationTitle(formattedDate)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showAddReminder = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .sheet(isPresented: $showAddReminder) {
                AddReminderView(day: day)
            }
        }
    }

    // MARK: - Date Header

    private var formattedDate: String {
        "\(day.gregorianDay) \(localization.localizedMonthName(day.gregorianMonth))"
    }

    // MARK: - Hero Section

    private var heroSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Liturgical period badge
            if let period = day.liturgicalPeriod, !period.isEmpty {
                HStack(spacing: 5) {
                    Text("⛪")
                        .font(.system(size: 10))
                    Text(period)
                        .font(.system(size: 11, weight: .bold))
                        .tracking(0.5)
                        .foregroundStyle(isGreat ? Color(red: 0.910, green: 0.659, blue: 0.486) : AppColors.mutedText)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isGreat ? AppColors.crimson.opacity(0.15) : AppColors.warmBorder)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(isGreat ? AppColors.crimson.opacity(0.25) : Color(red: 0.878, green: 0.863, blue: 0.831), lineWidth: 1)
                        )
                )
                .padding(.bottom, 12)
            }

            // Title
            if let primary = day.primaryFeast {
                Text(primary.name)
                    .font(.system(.title, design: .serif).weight(.bold))
                    .foregroundStyle(isGreat ? .white : AppColors.darkText)
                    .padding(.bottom, 6)
            }

            // Great feast subtitle
            if isGreat {
                Text(greatFeastLabel)
                    .font(.system(.subheadline, design: .serif).weight(.medium))
                    .foregroundStyle(AppColors.goldAccent)
                    .padding(.bottom, 14)
            }

            // Meta row
            HStack(spacing: 12) {
                // Full day name
                let idx = day.weekdayIndex
                if idx >= 0, idx < localization.bundle.ui.daysOfWeekFull.count {
                    Text(localization.bundle.ui.daysOfWeekFull[idx])
                        .font(.caption)
                }

                Text("•")
                    .font(.caption)
                    .opacity(0.4)

                Text("\(localization.ui.julianLabel) \(day.julianDate)")
                    .font(.caption)
            }
            .foregroundStyle(isGreat ? AppColors.lightMuted : AppColors.mutedText)
        }
        .padding(.horizontal, 20)
        .padding(.top, 24)
        .padding(.bottom, 20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            isGreat
                ? AnyShapeStyle(LinearGradient(
                    colors: [
                        AppColors.headerBg,
                        Color(red: 0.239, green: 0.196, blue: 0.145),
                        Color(red: 1, green: 0.97, blue: 0.94)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                  ))
                : AnyShapeStyle(Color(red: 0.996, green: 0.992, blue: 0.984))
        )
    }

    // MARK: - Content Sections

    private var contentSections: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Fasting section
            fastingSection
                .padding(.top, 16)

            sectionDivider

            // Saints / Commemorations
            if !day.feasts.isEmpty {
                saintsSection
            }

            sectionDivider

            // Readings
            if !day.readings.isEmpty {
                readingsSection
            }

            // Reflection
            if let reflection = day.reflection, !reflection.text.isEmpty {
                sectionDivider
                reflectionSection(reflection)
            }

            Spacer().frame(height: 40)
        }
        .padding(.horizontal, 16)
    }

    private var sectionDivider: some View {
        Rectangle()
            .fill(AppColors.warmBorder)
            .frame(height: 1)
            .padding(.vertical, 20)
    }

    // MARK: - Fasting

    private var fastingSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Large fasting badge
            let (icon, color, bg) = fastingStyle(for: day.fasting.type)
            HStack(spacing: 8) {
                Text(icon)
                    .font(.system(size: 20))
                Text(day.fasting.label)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(color)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(bg)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(color.opacity(0.13), lineWidth: 1.5)
                    )
            )

            // Only show explanation if it's in the current locale (not English fallback)
            if !day.fasting.explanation.isEmpty && !isEnglishText(day.fasting.explanation) {
                Text(day.fasting.explanation)
                    .font(.subheadline)
                    .foregroundStyle(AppColors.bodyText)
                    .lineSpacing(4)
                    .padding(.leading, 2)
            }
        }
    }

    // MARK: - Saints

    private var saintsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("☦")
                    .font(.system(size: 16))
                Text(localization.ui.commemorationsLabel)
                    .font(.system(.subheadline, design: .serif).weight(.bold))
                    .foregroundStyle(AppColors.darkText)
            }

            ForEach(day.feasts, id: \.name) { feast in
                HStack(alignment: .top, spacing: 12) {
                    // Icon
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(
                                LinearGradient(
                                    colors: [AppColors.warmBorder, Color(red: 0.878, green: 0.863, blue: 0.831)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 36, height: 36)
                        Text(feast.importance == "great" ? "✦" : "☦")
                            .font(.system(size: 16))
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(feast.name)
                            .font(.system(.subheadline, design: .serif).weight(.semibold))
                            .foregroundStyle(AppColors.darkText)
                        Text(localizedSaintType(feast.type))
                            .font(.caption2.weight(.medium))
                            .foregroundStyle(AppColors.lightMuted)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(AppColors.cardBg)
                )
                .overlay(alignment: .leading) {
                    Rectangle()
                        .fill(AppColors.goldAccent)
                        .frame(width: 3)
                        .clipShape(RoundedRectangle(cornerRadius: 2))
                }
            }
        }
    }

    // MARK: - Readings

    private var readingsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("📖")
                    .font(.system(size: 16))
                Text(localization.ui.readingsLabel)
                    .font(.system(.subheadline, design: .serif).weight(.bold))
                    .foregroundStyle(AppColors.darkText)
            }

            ForEach(Array(day.readings.enumerated()), id: \.offset) { _, reading in
                ReadingCard(reading: reading)
            }
        }
    }

    // MARK: - Reflection

    private func reflectionSection(_ reflection: Reflection) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Text("💭")
                    .font(.system(size: 16))
                Text(reflection.source)
                    .font(.system(.subheadline, design: .serif).weight(.bold))
                    .foregroundStyle(AppColors.darkText)
            }

            Text(reflection.text)
                .font(.system(.subheadline, design: .serif))
                .foregroundStyle(Color(red: 0.239, green: 0.196, blue: 0.145))
                .lineSpacing(5)
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(
                            LinearGradient(
                                colors: [AppColors.cardBg, AppColors.warmBg],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                )
                .overlay(alignment: .leading) {
                    Rectangle()
                        .fill(AppColors.goldAccent)
                        .frame(width: 3)
                        .clipShape(RoundedRectangle(cornerRadius: 2))
                }
        }
    }

    // MARK: - Fasting Style Helper

    private func fastingStyle(for type: String) -> (String, Color, Color) {
        let fastType = type.lowercased()
        if fastType == "strict" || fastType == "dryeating" {
            return ("🚫", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if fastType == "hotwithoutoil" || fastType == "water" {
            return ("💧", AppColors.fastWater, AppColors.fastWaterBg)
        } else if fastType == "hotwithoil" || fastType == "oil" {
            return ("🫒", AppColors.fastOil, AppColors.fastOilBg)
        } else if fastType == "fish" {
            return ("🐟", AppColors.fastFish, AppColors.fastFishBg)
        } else {
            return ("✓", AppColors.fastFree, AppColors.fastFreeBg)
        }
    }

    // MARK: - Labels

    private var greatFeastLabel: String {
        switch localization.language {
        case .sr: return "Велики празник"
        case .ru: return "Великий праздник"
        }
    }

    private func localizedSaintType(_ type: String) -> String {
        let types_sr: [String: String] = [
            "feast": "Празник", "saint": "Свети", "apostle": "Апостол",
            "great_martyr": "Великомученик", "hierarch": "Светитељ",
            "equal_to_apostles": "Равноапостолни", "venerable": "Преподобни",
            "hieromartyr": "Свештеномученик", "venerable_martyr": "Преподобномученик",
            "martyr": "Мученик", "righteous": "Праведни", "blessed": "Блажени",
            "confessor": "Исповедник", "noble": "Благоверни", "prophet": "Пророк",
            "synaxis": "Сабор",
        ]
        let types_ru: [String: String] = [
            "feast": "Праздник", "saint": "Святой", "apostle": "Апостол",
            "great_martyr": "Великомученик", "hierarch": "Святитель",
            "equal_to_apostles": "Равноапостольный", "venerable": "Преподобный",
            "hieromartyr": "Священномученик", "venerable_martyr": "Преподобномученик",
            "martyr": "Мученик", "righteous": "Праведный", "blessed": "Блаженный",
            "confessor": "Исповедник", "noble": "Благоверный", "prophet": "Пророк",
            "synaxis": "Собор",
        ]
        switch localization.language {
        case .sr: return types_sr[type] ?? type
        case .ru: return types_ru[type] ?? type
        }
    }

    /// Check if text appears to be English (fallback from API)
    private func isEnglishText(_ text: String) -> Bool {
        let latinRange = text.range(of: "[a-zA-Z]{3,}", options: .regularExpression)
        return latinRange != nil
    }
}

// MARK: - Reading Card (expandable scripture text)

struct ReadingCard: View {
    let reading: ScriptureReading
    @Environment(LocalizationManager.self) private var localization
    @State private var isExpanded = false

    private var localizedType: String {
        let t = reading.type.lowercased()
        switch localization.language {
        case .sr:
            if t == "gospel" { return "Јеванђеље" }
            if t == "apostol" { return "Апостол" }
            if t == "ot" { return "Стари Завет" }
            return reading.type
        case .ru:
            if t == "gospel" { return "Евангелие" }
            if t == "apostol" { return "Апостол" }
            if t == "ot" { return "Ветхий Завет" }
            return reading.type
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Header: type + reference
            Button {
                if reading.text != nil {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        isExpanded.toggle()
                    }
                }
            } label: {
                HStack {
                    // Service label if available
                    if let service = reading.service {
                        Text(service)
                            .font(.system(size: 10, weight: .bold))
                            .tracking(0.5)
                            .foregroundStyle(AppColors.mutedText)
                    }

                    Text(localizedType.uppercased())
                        .font(.system(size: 11, weight: .bold))
                        .tracking(0.8)
                        .foregroundStyle(AppColors.mutedText)

                    Spacer()

                    Text(reading.displayReference)
                        .font(.system(.caption, design: .serif).weight(.bold))
                        .foregroundStyle(AppColors.darkText)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(AppColors.warmBorder)
                        )

                    if reading.text != nil {
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .font(.caption2)
                            .foregroundStyle(AppColors.lightMuted)
                    }
                }
            }
            .buttonStyle(.plain)

            if let zachalo = reading.zachalo {
                Text("зач. \(zachalo)")
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
            }

            // Scripture text (expandable)
            if isExpanded, let text = reading.text, !text.isEmpty {
                Text(text)
                    .font(.system(.subheadline, design: .serif))
                    .foregroundStyle(AppColors.bodyText)
                    .lineSpacing(5)
                    .padding(.top, 4)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(AppColors.cardBg)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(AppColors.warmBorder, lineWidth: 1.5)
                )
        )
        .shadow(color: AppColors.darkText.opacity(0.04), radius: 2, y: 1)
    }
}
