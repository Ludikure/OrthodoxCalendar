import SwiftUI

struct DayDetailView: View {
    let dayInfo: DayInfo
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss
    @State private var showAddReminder = false

    private var calendar: Calendar { Calendar(identifier: .gregorian) }

    /// Whether we have scraped local data for this day
    private var hasLocalData: Bool {
        !dayInfo.localDescription.isEmpty
    }

    /// Non-English locales with scraped data hide English API content
    private var hideEnglishContent: Bool {
        hasLocalData && localization.language != .en
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    dateHeader
                    feastSection
                    if hasLocalData { localCommemorationSection }
                    fastingSection
                    if !dayInfo.localPrayer.isEmpty { prayerSection }
                    if !hideEnglishContent && !dayInfo.saints.isEmpty { commemorationsSection }
                    if !hideEnglishContent && !dayInfo.readings.isEmpty { readingsSection }
                    if !hideEnglishContent && !dayInfo.stories.isEmpty { storiesSection }
                }
                .padding()
            }
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
                AddReminderView(dayInfo: dayInfo)
            }
        }
    }

    // MARK: - Date Header

    private var formattedDate: String {
        let day = calendar.component(.day, from: dayInfo.gregorianDate)
        let month = calendar.component(.month, from: dayInfo.gregorianDate)
        return "\(day) \(localization.localizedMonthName(month))"
    }

    private var dateHeader: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Full day name (dayInfo.weekday: 0=Sun..6=Sat)
            if dayInfo.weekday >= 0, dayInfo.weekday < localization.bundle.ui.daysOfWeekFull.count {
                Text(localization.bundle.ui.daysOfWeekFull[dayInfo.weekday])
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Julian date
            HStack {
                Text(localization.ui.julianLabel)
                    .foregroundStyle(.secondary)
                Text(dayInfo.julianDateString)
            }
            .font(.subheadline)

            // Tone
            if let tone = dayInfo.tone, tone > 0 {
                Text("Глас \(tone)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Feast

    private var feastSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Use localized display name when available
            let title = hasLocalData ? dayInfo.localDescription : dayInfo.displayName
            if !title.isEmpty {
                Text(title)
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(dayInfo.localIsRed ? AppColors.crimson : feastTitleColor)
            }

            if let feastType = dayInfo.feastType {
                Text(localization.localizedFeastType(feastType))
                    .font(.caption)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(feastBadgeColor(feastType).opacity(0.15))
                    .foregroundStyle(feastBadgeColor(feastType))
                    .clipShape(Capsule())
            }

            // Extra feast (language-specific)
            if let extra = dayInfo.extraFeastName, extra != dayInfo.displayName {
                VStack(alignment: .leading, spacing: 2) {
                    Text(extra)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    if let desc = dayInfo.extraFeastDescription {
                        Text(desc)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.top, 4)
            }
        }
    }

    // MARK: - Local Commemorations (scraped Serbian/Russian data)

    private var localCommemorationSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(localization.ui.commemorationsLabel, systemImage: "person.2")
                .font(.headline)

            // The local description contains all saints for the day
            // Split by semicolons for individual display
            let parts = dayInfo.localDescription
                .components(separatedBy: "; ")
                .filter { !$0.isEmpty }

            ForEach(parts, id: \.self) { part in
                Text("• \(part)")
                    .font(.subheadline)
            }
        }
    }

    // MARK: - Fasting

    private var fastingSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(localization.ui.fastingLabel, systemImage: "leaf")
                .font(.headline)

            if !dayInfo.localFastingDesc.isEmpty {
                // Use scraped local fasting description
                Text(dayInfo.localFastingDesc)
                    .font(.body)
            } else {
                Text(dayInfo.fastLevelDesc)
                    .font(.body)

                if !dayInfo.fastExceptionDesc.isEmpty {
                    Text(dayInfo.fastExceptionDesc)
                        .font(.subheadline)
                        .foregroundStyle(AppColors.fastFreeGreen)
                }
            }

            // Liturgical note (Russian)
            if !dayInfo.localLiturgicalNote.isEmpty {
                Text(dayInfo.localLiturgicalNote)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.top, 2)
            }
        }
    }

    // MARK: - Prayer (Russian — Feofan Zatvornik)

    private var prayerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label("Мысли на каждый день", systemImage: "book.closed")
                .font(.headline)

            Text(dayInfo.localPrayer)
                .font(.body)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Commemorations (English API data)

    private var commemorationsSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Only show English header when no local data, to avoid duplication
            if !hasLocalData {
                Label(localization.ui.commemorationsLabel, systemImage: "person.2")
                    .font(.headline)
            }

            ForEach(dayInfo.saints, id: \.self) { saint in
                Text("• \(saint)")
                    .font(.subheadline)
                    .foregroundStyle(hasLocalData ? .secondary : .primary)
            }
        }
    }

    // MARK: - Readings

    private var readingsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(localization.ui.readingsLabel, systemImage: "book")
                .font(.headline)

            ForEach(dayInfo.readings) { reading in
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(reading.source)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        Text(reading.display)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Text(reading.passage.map(\.content).joined(separator: " "))
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .lineLimit(nil)
                }
                .padding(.vertical, 4)
            }
        }
    }

    // MARK: - Stories

    private var storiesSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(localization.ui.commemorationsLabel, systemImage: "text.book.closed")
                .font(.headline)

            ForEach(dayInfo.stories) { story in
                DisclosureGroup {
                    Text(story.story.replacingOccurrences(
                        of: "<[^>]+>",
                        with: "",
                        options: .regularExpression
                    ))
                    .font(.body)
                    .foregroundStyle(.secondary)
                } label: {
                    Text(story.title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                }
            }
        }
    }

    // MARK: - Colors

    private var feastTitleColor: Color {
        guard let type = dayInfo.feastType else { return .primary }
        return feastBadgeColor(type)
    }

    private func feastBadgeColor(_ type: FeastType) -> Color {
        switch type {
        case .pascha:   return AppColors.gold
        case .great:    return AppColors.crimson
        case .major:    return AppColors.feastBlue
        case .holyWeek: return AppColors.holyWeekPurple
        case .bright:   return AppColors.brightGold
        case .minor:    return .secondary
        }
    }
}
