import XCTest
@testable import Orthodox_Calendar

/// The widgets' snapshot: consecutive days from the bundled data, the right
/// fields, and the slava countdown as the banner counts it.
final class WidgetSnapshotTests: XCTestCase {

    private func year(_ locale: String, _ year: Int) throws -> [String: CalendarDay] {
        let url = try XCTUnwrap(Bundle.main.url(forResource: "calendar_\(locale)_\(year)", withExtension: "json"))
        let file = try JSONDecoder().decode(CalendarFile.self, from: Data(contentsOf: url))
        var days: [String: CalendarDay] = [:]
        for day in file.days.values { days[day.gregorianDate] = day }
        return days
    }

    private func labels(_ language: AppLanguage) throws -> UILabels {
        let url = try XCTUnwrap(Bundle.main.url(forResource: language.localizationFile, withExtension: "json"))
        return try JSONDecoder().decode(LocalizationBundle.self, from: Data(contentsOf: url)).ui
    }

    private func date(_ key: String) -> Date { DateKeys.date(from: key)! }

    private let nikoljdan = SlavaDay("Никољдан", "Свети Николај", .julian(month: 12, day: 6))

    func testTwentyOneConsecutiveDaysAcrossTheYearBoundary() throws {
        var days = try year("sr", 2026)
        days.merge(try year("sr", 2027)) { a, _ in a }
        let snapshot = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: days, from: date("2026-12-20"), language: .sr, ui: try labels(.sr), mySlava: nil))

        XCTAssertEqual(snapshot.language, "sr")
        XCTAssertEqual(snapshot.days.count, WidgetSnapshot.dayCount)
        XCTAssertEqual(snapshot.days.first?.date, "2026-12-20")
        XCTAssertEqual(snapshot.days.last?.date, "2027-01-09")
        for (a, b) in zip(snapshot.days, snapshot.days.dropFirst()) {
            XCTAssertTrue(DateKeys.isConsecutive(a.date, b.date), "\(a.date) → \(b.date)")
        }

        // Fields come from the day as the calendar shows it.
        let christmas = try XCTUnwrap(snapshot.day(for: "2027-01-07"))
        let source = try XCTUnwrap(days["2027-01-07"])
        XCTAssertTrue(christmas.isGreatFeast)
        XCTAssertEqual(christmas.primary, source.primaryFeast?.name)
        XCTAssertEqual(christmas.fastingType, source.fasting.type)
        XCTAssertEqual(christmas.fastingLabel, source.fasting.label)
        XCTAssertEqual(christmas.fastingAbbrev, source.fasting.abbrev ?? "")
        XCTAssertEqual(christmas.weekday, try labels(.sr).daysOfWeekFull[source.weekdayIndex])
        XCTAssertEqual(christmas.dateLabel, try labels(.sr).dayAndMonth(7, 1))
        XCTAssertLessThanOrEqual(christmas.secondary.count, WidgetSnapshotBuilder.maxSecondary)
        XCTAssertNil(christmas.slava)
    }

    func testStopsWhereTheDataStops() throws {
        let days = try year("sr", 2026)
        let snapshot = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: days, from: date("2026-12-25"), language: .sr, ui: try labels(.sr), mySlava: nil))
        XCTAssertEqual(snapshot.days.last?.date, "2026-12-31")
        XCTAssertNil(WidgetSnapshotBuilder.build(
            days: days, from: date("2027-01-02"), language: .sr, ui: try labels(.sr), mySlava: nil))
    }

    func testSlavaCountdownWithinThirtyDays() throws {
        let days = try year("sr", 2026)
        let snapshot = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: days, from: date("2026-12-07"), language: .sr, ui: try labels(.sr), mySlava: nikoljdan))
        XCTAssertEqual(snapshot.days[0].slava, WidgetSnapshot.Slava(name: "Никољдан", daysUntil: 12))
        XCTAssertEqual(snapshot.day(for: "2026-12-18")?.slava?.daysUntil, 1)
        XCTAssertEqual(snapshot.day(for: "2026-12-19")?.slava?.daysUntil, 0)
        // The day after, the next one is a year away: no countdown.
        XCTAssertNil(snapshot.day(for: "2026-12-20")?.slava)
        XCTAssertEqual(SlavaCountdownText.label(12), "за 12 дана")
        XCTAssertEqual(SlavaCountdownText.label(21), "за 21 дан")
        XCTAssertEqual(SlavaCountdownText.label(0), "Срећна слава!")

        // More than 30 days out: nothing yet.
        let early = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: days, from: date("2026-11-01"), language: .sr, ui: try labels(.sr), mySlava: nikoljdan))
        XCTAssertNil(early.days[0].slava)
        XCTAssertEqual(early.day(for: "2026-11-19")?.slava?.daysUntil, 30)
    }

    func testNoSlavaOutsideSerbian() throws {
        let snapshot = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: try year("en", 2026), from: date("2026-12-07"), language: .en,
            ui: try labels(.en), mySlava: nikoljdan))
        XCTAssertEqual(snapshot.language, "en")
        XCTAssertTrue(snapshot.days.allSatisfy { $0.slava == nil })
    }

    func testRoundTripsThroughAFile() throws {
        let snapshot = try XCTUnwrap(WidgetSnapshotBuilder.build(
            days: try year("ru", 2026), from: date("2026-09-27"), language: .ru,
            ui: try labels(.ru), mySlava: nil, now: date("2026-09-27")))
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("widget_snapshot_test.json")
        defer { try? FileManager.default.removeItem(at: url) }
        try snapshot.write(to: url)
        XCTAssertEqual(WidgetSnapshot.read(from: url), snapshot)
    }
}
