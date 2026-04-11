import SwiftUI

struct DayDetailView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss
    @State private var showAddReminder = false
    @State private var showShareSheet = false
    @State private var expandedSection: String?

    private var isGreat: Bool { day.isGreatFeast }

    var body: some View {
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
                    Image(systemName: "plus.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                HStack(spacing: 8) {
                    Button {
                        showShareSheet = true
                    } label: {
                        Image(systemName: "square.and.arrow.up.circle.fill")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .sheet(isPresented: $showAddReminder) {
            AddReminderView(day: day)
        }
        .sheet(isPresented: $showShareSheet) {
            ShareSheet(items: [shareText])
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
                        .foregroundStyle(isGreat ? AppColors.goldAccent : AppColors.mutedText)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isGreat ? AppColors.crimson.opacity(0.15) : AppColors.warmBorder)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(isGreat ? AppColors.crimson.opacity(0.25) : AppColors.warmBorder, lineWidth: 1)
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
                        AppColors.darkText.opacity(0.15),
                        AppColors.warmBg
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                  ))
                : AnyShapeStyle(AppColors.cardBg)
        )
    }

    // MARK: - Content Sections

    private var contentSections: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Fasting section
            fastingSection
                .padding(.top, 16)

            sectionDivider

            // Saints / Commemorations (with expandable bios)
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

            if !day.fasting.explanation.isEmpty {
                Text(day.fasting.explanation)
                    .font(.subheadline)
                    .foregroundStyle(AppColors.bodyText)
                    .lineSpacing(4)
                    .padding(.leading, 2)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(day.fasting.label)
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

            ForEach(Array(day.feasts.enumerated()), id: \.offset) { index, feast in
                SaintCard(
                    feast: feast,
                    bio: findBio(for: feast, index: index),
                    localizedType: localizedSaintType(feast.type)
                )
            }
        }
    }

    /// Find matching bio for a feast entry
    private func findBio(for feast: Feast, index: Int) -> SaintBio? {
        guard let bios = day.saintBios, !bios.isEmpty else { return nil }
        // Match by title similarity — key words from feast name must appear in bio title
        let feastNameLower = feast.name.lowercased()
        let matched = bios.first { bio in
            let bioTitleLower = bio.title.lowercased()
            let feastWords = feastNameLower.split(separator: " ").filter { $0.count > 3 }
            return feastWords.contains { bioTitleLower.contains($0) }
        }
        if matched != nil { return matched }
        // For single-bio days (Serbian Охридски Пролог), show on the first
        // non-moveable feast (moveable feasts like Pascha, Holy Week don't get saint bios)
        if bios.count == 1 && !feast.moveable {
            // Only if no other feast already matched this bio
            let anyOtherMatch = day.feasts.enumerated().contains { i, f in
                guard i < index else { return false }
                let words = f.name.lowercased().split(separator: " ").filter { $0.count > 3 }
                let bioLower = bios[0].title.lowercased()
                return words.contains { bioLower.contains($0) }
            }
            if !anyOtherMatch { return bios[0] }
        }
        return nil
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
                .foregroundStyle(AppColors.bodyText)
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
        if fastType == "totalabstinence" || fastType == "strict" {
            return ("🚫", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if fastType == "dryeating" {
            return ("🍞", AppColors.fastStrict, AppColors.fastStrictBg)
        } else if fastType == "hotnooil" || fastType == "hotwithoutoil" || fastType == "water" {
            return ("💧", AppColors.fastWater, AppColors.fastWaterBg)
        } else if fastType == "hotwithoil" || fastType == "oil" {
            return ("🫒", AppColors.fastOil, AppColors.fastOilBg)
        } else if fastType == "fish" || fastType == "fishroe" {
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
        case .en: return "Great Feast"
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
        let types_en: [String: String] = [
            "feast": "Feast", "saint": "Saint", "apostle": "Apostle",
            "great_martyr": "Great Martyr", "hierarch": "Hierarch",
            "equal_to_apostles": "Equal-to-the-Apostles", "venerable": "Venerable",
            "hieromartyr": "Hieromartyr", "venerable_martyr": "Venerable Martyr",
            "martyr": "Martyr", "righteous": "Righteous", "blessed": "Blessed",
            "confessor": "Confessor", "noble": "Right-believing", "prophet": "Prophet",
            "synaxis": "Synaxis",
        ]
        switch localization.language {
        case .sr: return types_sr[type] ?? type
        case .ru: return types_ru[type] ?? type
        case .en: return types_en[type] ?? type
        }
    }

    // MARK: - Share

    private var shareText: String {
        var lines: [String] = []

        // Date
        lines.append("☦ \(formattedDate)")
        lines.append("")

        // Primary feast
        if let primary = day.primaryFeast {
            lines.append(primary.name)
        }

        // Secondary feasts
        for feast in day.feasts.dropFirst() {
            lines.append("• \(feast.name)")
        }

        // Fasting
        lines.append("")
        lines.append("\(day.fasting.label)")

        // Readings
        if !day.readings.isEmpty {
            lines.append("")
            for reading in day.readings {
                lines.append("\(reading.displayReference)")
            }
        }

        return lines.joined(separator: "\n")
    }
}

// MARK: - Share Sheet

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
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
        case .en:
            if t == "gospel" { return "Gospel" }
            if t == "apostol" { return "Epistle" }
            if t == "ot" { return "Old Testament" }
            return reading.type
        }
    }

    private var zachaloLabel: String {
        switch localization.language {
        case .sr, .ru: return "зач."
        case .en: return "ch."
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Header: type + reference
            Button {
                if reading.text != nil {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
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
                        Image(systemName: "chevron.down")
                            .font(.caption2)
                            .foregroundStyle(AppColors.lightMuted)
                            .rotationEffect(.degrees(isExpanded ? -180 : 0))
                    }
                }
            }
            .buttonStyle(.plain)

            if let zachalo = reading.zachalo {
                Text("\(zachaloLabel) \(zachalo)")
                    .font(.caption)
                    .foregroundStyle(AppColors.mutedText)
            }

            // Scripture text (expandable)
            if let text = reading.text, !text.isEmpty {
                VStack {
                    Text(text)
                        .font(.system(.subheadline, design: .serif))
                        .foregroundStyle(AppColors.bodyText)
                        .lineSpacing(5)
                        .padding(.top, 4)
                }
                .frame(maxHeight: isExpanded ? .infinity : 0, alignment: .top)
                .clipped()
                .opacity(isExpanded ? 1 : 0)
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
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(localizedType): \(reading.displayReference)")
        .accessibilityHint(reading.text != nil ? (isExpanded ? "" : "Double tap to expand") : "")
    }
}

// MARK: - Saint Card (feast entry + expandable biography)

struct SaintCard: View {
    let feast: Feast
    let bio: SaintBio?
    let localizedType: String
    @State private var isExpanded = false

    /// The expandable text: feast description or saint bio
    private var expandableText: String? {
        if let desc = feast.description, !desc.isEmpty { return desc }
        return bio?.text
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                if expandableText != nil {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                        isExpanded.toggle()
                    }
                }
            } label: {
                HStack(alignment: .top, spacing: 12) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(
                                LinearGradient(
                                    colors: [AppColors.warmBorder, AppColors.warmBorder.opacity(0.8)],
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
                            .multilineTextAlignment(.leading)
                        Text(localizedType)
                            .font(.caption2.weight(.medium))
                            .foregroundStyle(AppColors.lightMuted)
                    }

                    Spacer()

                    if expandableText != nil {
                        Image(systemName: "chevron.down")
                            .font(.caption2)
                            .foregroundStyle(AppColors.lightMuted)
                            .rotationEffect(.degrees(isExpanded ? -180 : 0))
                            .padding(.top, 10)
                    }
                }
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            // Expandable description or biography
            if let text = expandableText {
                VStack(alignment: .leading, spacing: 0) {
                    Text(text)
                        .font(.system(.subheadline, design: .serif))
                        .foregroundStyle(AppColors.bodyText)
                        .lineSpacing(5)
                        .padding(.horizontal, 12)
                        .padding(.bottom, 12)
                }
                .frame(maxHeight: isExpanded ? .infinity : 0, alignment: .top)
                .clipped()
                .opacity(isExpanded ? 1 : 0)
            }
        }
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
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(localizedType): \(feast.name)")
        .accessibilityHint(bio != nil ? (isExpanded ? "" : "Double tap to read biography") : "")
    }
}
