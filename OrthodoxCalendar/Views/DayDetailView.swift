import SwiftUI

struct DayDetailView: View {
    let day: CalendarDay
    @Environment(LocalizationManager.self) private var localization
    @Environment(\.dismiss) private var dismiss
    @State private var showAddReminder = false

    private var calendar: Calendar { Calendar(identifier: .gregorian) }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    dateHeader
                    feastSection
                    fastingSection
                    if let reflection = day.reflection, !reflection.text.isEmpty { reflectionSection }
                    if !day.feasts.isEmpty { commemorationsSection }
                    if !day.readings.isEmpty { readingsSection }
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
                AddReminderView(day: day)
            }
        }
    }

    // MARK: - Date Header

    private var formattedDate: String {
        "\(day.gregorianDay) \(localization.localizedMonthName(day.gregorianMonth))"
    }

    private var dateHeader: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Full day name
            let idx = day.weekdayIndex
            if idx >= 0, idx < localization.bundle.ui.daysOfWeekFull.count {
                Text(localization.bundle.ui.daysOfWeekFull[idx])
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Julian date
            HStack {
                Text(localization.ui.julianLabel)
                    .foregroundStyle(.secondary)
                Text(day.julianDate)
            }
            .font(.subheadline)

            // Liturgical period
            if let period = day.liturgicalPeriod, !period.isEmpty {
                Text(period)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Feast

    private var feastSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Primary feast
            if let primary = day.primaryFeast {
                Text(primary.name)
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(primary.importance == "great" ? AppColors.crimson : .primary)

                if day.isGreatFeast {
                    Text(greatFeastLabel)
                        .font(.caption)
                        .fontWeight(.medium)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(AppColors.crimson.opacity(0.15))
                        .foregroundStyle(AppColors.crimson)
                        .clipShape(Capsule())
                }
            }

            // Secondary feasts
            if !day.secondaryFeasts.isEmpty {
                ForEach(day.secondaryFeasts, id: \.name) { feast in
                    Text(feast.name)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
            }
        }
    }

    // MARK: - Commemorations

    private var commemorationsSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(localization.ui.commemorationsLabel, systemImage: "person.2")
                .font(.headline)

            ForEach(day.feasts, id: \.name) { feast in
                Text("• \(feast.name)")
                    .font(.subheadline)
            }
        }
    }

    // MARK: - Fasting

    private var fastingSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(localization.ui.fastingLabel, systemImage: "leaf")
                .font(.headline)

            Text(day.fasting.label)
                .font(.body)

            if !day.fasting.explanation.isEmpty {
                Text(day.fasting.explanation)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Reflection

    private var reflectionSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let reflection = day.reflection {
                Label(reflection.source, systemImage: "book.closed")
                    .font(.headline)

                Text(reflection.text)
                    .font(.body)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Readings

    private var readingsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(localization.ui.readingsLabel, systemImage: "book")
                .font(.headline)

            ForEach(Array(day.readings.enumerated()), id: \.offset) { _, reading in
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(reading.book)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        Text(reading.reference)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        if let zachalo = reading.zachalo {
                            Text("(зач. \(zachalo))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding(.vertical, 4)
            }
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
}
