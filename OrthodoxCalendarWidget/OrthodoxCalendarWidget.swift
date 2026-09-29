import SwiftUI
import WidgetKit

// MARK: - Timeline

struct DayEntry: TimelineEntry {
    let date: Date
    let language: String
    /// Nil when the app's snapshot does not cover this day: the widget asks
    /// the user to open the app rather than show another day's saints.
    let day: WidgetSnapshot.Day?
}

struct DayProvider: TimelineProvider {
    /// Entries scheduled per timeline, one per local midnight.
    static let daysAhead = 7

    func placeholder(in context: Context) -> DayEntry {
        DayEntry(date: Date(), language: "sr", day: .sample)
    }

    func getSnapshot(in context: Context, completion: @escaping @Sendable (DayEntry) -> Void) {
        let entry = Self.entries(now: Date()).first ?? DayEntry(date: Date(), language: "sr", day: nil)
        // The widget gallery before the app has ever run: show what it looks like.
        if context.isPreview, entry.day == nil {
            completion(DayEntry(date: Date(), language: entry.language, day: .sample))
        } else {
            completion(entry)
        }
    }

    func getTimeline(in context: Context, completion: @escaping @Sendable (Timeline<DayEntry>) -> Void) {
        let now = Date()
        let entries = Self.entries(now: now)
        if entries.contains(where: { $0.day != nil }) {
            completion(Timeline(entries: entries, policy: .atEnd))
        } else {
            // Nothing to show until the app writes a snapshot; look again
            // tomorrow (the app also reloads the widgets when it writes one).
            let tomorrow = Calendar.current.date(byAdding: .day, value: 1,
                                                 to: Calendar.current.startOfDay(for: now)) ?? now
            completion(Timeline(entries: [entries.first ?? DayEntry(date: now, language: "sr", day: nil)],
                                policy: .after(tomorrow)))
        }
    }

    /// Today (from now) and each following midnight, while the snapshot lasts.
    static func entries(now: Date) -> [DayEntry] {
        let snapshot = WidgetSnapshot.read()
        let language = snapshot?.language ?? WidgetStrings.deviceLanguage
        let cal = Calendar.current
        let today = cal.startOfDay(for: now)
        var out: [DayEntry] = []
        for offset in 0..<daysAhead {
            guard let midnight = cal.date(byAdding: .day, value: offset, to: today) else { break }
            let day = snapshot?.day(for: DateKeys.key(from: midnight))
            if offset > 0, day == nil { break }
            out.append(DayEntry(date: offset == 0 ? now : midnight, language: language, day: day))
        }
        return out
    }
}

// MARK: - Strings

/// The widget's own few strings, by `AppLanguage` raw value.
struct WidgetStrings {
    let language: String

    static var deviceLanguage: String {
        switch Locale.preferredLanguages.first?.prefix(2) {
        case "ru": return "ru"
        case "en": return "en"
        default: return "sr"
        }
    }

    var displayName: String {
        switch language {
        case "sr": return "Православни календар"
        case "ru": return "Православный календарь"
        default: return "Orthodox Calendar"
        }
    }

    var description: String {
        switch language {
        case "sr": return "Данашњи светитељи и пост."
        case "ru": return "Святые дня и пост."
        default: return "Today's saints and fasting."
        }
    }

    var openApp: String {
        switch language {
        case "sr": return "Отворите апликацију"
        case "ru": return "Откройте приложение"
        default: return "Open the app"
        }
    }

    var greatFeast: String {
        switch language {
        case "sr": return "Велики празник"
        case "ru": return "Великий праздник"
        default: return "Great Feast"
        }
    }
}

// MARK: - Views

struct DayWidgetView: View {
    let entry: DayEntry
    @Environment(\.widgetFamily) private var family

    private var strings: WidgetStrings { WidgetStrings(language: entry.language) }

    var body: some View {
        Group {
            if let day = entry.day {
                switch family {
                case .systemMedium: MediumDayView(day: day, strings: strings)
                case .accessoryRectangular: RectangularDayView(day: day)
                case .accessoryInline: InlineDayView(day: day)
                default: SmallDayView(day: day)
                }
            } else {
                placeholder
            }
        }
        .widgetURL(URL(string: "orthodoxcalendar://today"))
        .containerBackground(for: .widget) {
            if family == .systemSmall || family == .systemMedium {
                AppColors.warmBg
            } else {
                Color.clear
            }
        }
    }

    @ViewBuilder private var placeholder: some View {
        switch family {
        case .accessoryInline:
            Text("☦ \(strings.openApp)")
        case .accessoryRectangular:
            VStack(alignment: .leading) {
                Text("☦").font(.headline)
                Text(strings.openApp).font(.caption)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        default:
            VStack(spacing: 6) {
                Text("☦")
                    .font(.system(size: 28, design: .serif))
                    .foregroundStyle(AppColors.crimson)
                Text(strings.openApp)
                    .font(.system(.subheadline, design: .serif))
                    .foregroundStyle(AppColors.bodyText)
                    .multilineTextAlignment(.center)
            }
        }
    }
}

/// Weekday over the date; the ✦ on a great feast.
private struct DateHeader: View {
    let day: WidgetSnapshot.Day

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 0) {
                Text(day.weekday.uppercased())
                    .font(.system(size: 11, weight: .bold))
                    .tracking(0.8)
                    .foregroundStyle(AppColors.crimson)
                    .lineLimit(1)
                Text(day.dateLabel)
                    .font(.system(size: 12))
                    .foregroundStyle(AppColors.mutedText)
                    .lineLimit(1)
            }
            Spacer(minLength: 4)
            if day.isGreatFeast {
                Text("✦")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(AppColors.crimson)
            }
        }
    }
}

/// The calendar row's fasting badge: icon and short label in a tinted capsule.
private struct FastingBadge: View {
    let day: WidgetSnapshot.Day

    var body: some View {
        let style = FastingBadgeStyle(type: day.fastingType)
        let text = day.fastingAbbrev.isEmpty ? day.fastingLabel : day.fastingAbbrev
        HStack(spacing: 3) {
            Text(style.icon).font(.system(size: 10))
            Text(text)
                .font(.system(size: 10, weight: .semibold))
                .lineLimit(1)
        }
        .foregroundStyle(style.color)
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(style.background)
        .clipShape(Capsule())
    }
}

private struct PrimaryName: View {
    let day: WidgetSnapshot.Day
    let lines: Int

    var body: some View {
        Text(day.primary)
            .font(.system(size: 15, weight: day.isGreatFeast ? .bold : .semibold, design: .serif))
            .foregroundStyle(day.isGreatFeast ? AppColors.bannerTitle : AppColors.darkText)
            .lineLimit(lines)
            .minimumScaleFactor(0.85)
            .fixedSize(horizontal: false, vertical: true)
    }
}

private struct SmallDayView: View {
    let day: WidgetSnapshot.Day

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            DateHeader(day: day)
            Spacer(minLength: 4)
            PrimaryName(day: day, lines: 3)
            Spacer(minLength: 4)
            FastingBadge(day: day)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}

private struct MediumDayView: View {
    let day: WidgetSnapshot.Day
    let strings: WidgetStrings

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 0) {
                DateHeader(day: day)
                Spacer(minLength: 4)
                FastingBadge(day: day)
                Text(day.fastingLabel)
                    .font(.system(size: 11))
                    .foregroundStyle(AppColors.mutedText)
                    .lineLimit(2)
                    .padding(.top, 4)
            }
            .frame(width: 104, alignment: .leading)
            .frame(maxHeight: .infinity, alignment: .leading)

            AppColors.goldAccent
                .frame(width: 1)

            VStack(alignment: .leading, spacing: 3) {
                if day.isGreatFeast {
                    Text("✦ \(strings.greatFeast)")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.2)
                        .textCase(.uppercase)
                        .foregroundStyle(AppColors.crimson)
                }
                PrimaryName(day: day, lines: 2)
                if !day.secondary.isEmpty {
                    Text(day.secondary.joined(separator: "; "))
                        .font(.caption)
                        .foregroundStyle(AppColors.mutedText)
                        .lineLimit(day.slava == nil ? 3 : 2)
                }
                Spacer(minLength: 0)
                if let slava = day.slava {
                    Text("🕯 \(slava.name) · \(SlavaCountdownText.label(slava.daysUntil))")
                        .font(.system(size: 12, weight: .bold, design: .serif))
                        .foregroundStyle(AppColors.slavaGold)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }
}

private struct RectangularDayView: View {
    let day: WidgetSnapshot.Day

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text((day.isGreatFeast ? "✦ " : "") + day.primary)
                .font(.system(.headline, design: .serif))
                .lineLimit(2)
                .minimumScaleFactor(0.8)
            Text("\(FastingBadgeStyle(type: day.fastingType).icon) \(day.fastingLabel)")
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .widgetAccentable()
    }
}

private struct InlineDayView: View {
    let day: WidgetSnapshot.Day

    var body: some View {
        if let slava = day.slava, slava.daysUntil == 0 {
            Text("🕯 \(SlavaCountdownText.label(0))")
        } else {
            Text("\(FastingBadgeStyle(type: day.fastingType).icon) \(day.fastingLabel)")
        }
    }
}

// MARK: - Widget

struct OrthodoxCalendarWidget: Widget {
    let kind = "OrthodoxCalendarToday"

    var body: some WidgetConfiguration {
        let strings = WidgetStrings(language: WidgetSnapshot.read()?.language ?? WidgetStrings.deviceLanguage)
        return StaticConfiguration(kind: kind, provider: DayProvider()) { entry in
            DayWidgetView(entry: entry)
        }
        .configurationDisplayName(strings.displayName)
        .description(strings.description)
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular, .accessoryInline])
    }
}

@main
struct OrthodoxCalendarWidgetBundle: WidgetBundle {
    var body: some Widget {
        OrthodoxCalendarWidget()
    }
}

// MARK: - Sample

extension WidgetSnapshot.Day {
    /// The gallery and placeholder day.
    static let sample = WidgetSnapshot.Day(
        date: "2026-12-19",
        weekday: "Субота",
        dateLabel: "19 децембар",
        primary: "Свети Николај Мирликијски Чудотворац",
        secondary: ["Преподобни Никола Суворов"],
        isGreatFeast: false,
        fastingType: "fish",
        fastingLabel: "Риба дозвољена",
        fastingAbbrev: "риба",
        slava: WidgetSnapshot.Slava(name: "Никољдан", daysUntil: 0)
    )
}

#Preview("Small", as: .systemSmall) {
    OrthodoxCalendarWidget()
} timeline: {
    DayEntry(date: .now, language: "sr", day: .sample)
    DayEntry(date: .now, language: "sr", day: nil)
}

#Preview("Medium", as: .systemMedium) {
    OrthodoxCalendarWidget()
} timeline: {
    DayEntry(date: .now, language: "sr", day: .sample)
}

#Preview("Rectangular", as: .accessoryRectangular) {
    OrthodoxCalendarWidget()
} timeline: {
    DayEntry(date: .now, language: "sr", day: .sample)
}
