import XCTest
@testable import Orthodox_Calendar

/// The `yyyy-MM-dd` keys are the identity of a day everywhere in the app, and
/// they are ASCII in the data files. These tests pin the two properties that
/// broke silently for Arabic/Persian/Thai users: the formatter must not follow
/// the user's numbering system, and adjacency must not split a fasting season.
final class DateKeysTests: XCTestCase {

    private func assertASCII(_ key: String, file: StaticString = #file, line: UInt = #line) {
        let pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
        XCTAssertTrue(key.range(of: pattern, options: .regularExpression) != nil,
                      "expected an ASCII yyyy-MM-dd key, got \"\(key)\"", file: file, line: line)
    }

    func testFormatterIsPinnedToPOSIX() {
        XCTAssertEqual(DateKeys.formatter.locale?.identifier, "en_US_POSIX")
        XCTAssertEqual(DateKeys.formatter.calendar?.identifier, .gregorian)
    }

    func testKeyRoundTripsADataKey() {
        // Round-tripped through the shared formatter rather than compared
        // against a hand-built Date, so the assertion holds whatever the host's
        // timezone is (the formatter renders in the user's zone, so a UTC
        // midnight instant can land on the day before it).
        let date = try? XCTUnwrap(DateKeys.date(from: "2026-09-09"))
        XCTAssertNotNil(date)
        XCTAssertEqual(DateKeys.key(from: date!), "2026-09-09")
        assertASCII(DateKeys.key(from: date!))
        XCTAssertNil(DateKeys.date(from: "2569-09-09x"))
    }

    func testLocaleAwareFormatterWouldBreakTheKeys() {
        // The premise the pinning rests on, asserted rather than assumed. A
        // formatter that follows the user's calendar renders 2569-09-09 (Thai
        // Buddhist, CE + 543) for the same instant; one that follows the
        // user's numbering system renders Eastern Arabic-Indic digits (that
        // half is not asserted — whether "ar-SA-u-nu-arab" reaches a DateFormatter is
        // OS-version dependent, and a failure there would be a false one).
        // Neither string equals the ASCII key in the data files.
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        var components = DateComponents()
        components.year = 2026; components.month = 9; components.day = 9
        let date = cal.date(from: components)!

        var buddhist = Calendar(identifier: .buddhist)
        buddhist.timeZone = cal.timeZone
        let byCalendar = DateFormatter()
        byCalendar.locale = Locale(identifier: "en_US")
        byCalendar.dateFormat = "yyyy-MM-dd"
        byCalendar.calendar = buddhist
        byCalendar.timeZone = cal.timeZone
        XCTAssertEqual(byCalendar.string(from: date), "2569-09-09",
                       "if this is not 2569-09-09 the premise below is untested")

        // The pinned formatter never goes down either path, so it stays ASCII.
        assertASCII(DateKeys.key(from: date))
    }

    func testTodayIsAnASCIIKey() {
        assertASCII(DateKeys.today)
    }

    func testConsecutiveDays() {
        XCTAssertTrue(DateKeys.isConsecutive("2026-02-27", "2026-02-28"))
        // 2026 is not a leap year: Feb 28 is followed by Mar 1.
        XCTAssertTrue(DateKeys.isConsecutive("2026-02-28", "2026-03-01"))
        XCTAssertTrue(DateKeys.isConsecutive("2027-12-31", "2028-01-01"))
        XCTAssertFalse(DateKeys.isConsecutive("2026-03-01", "2026-03-03"))
        XCTAssertFalse(DateKeys.isConsecutive("2026-03-02", "2026-03-01"))
        XCTAssertFalse(DateKeys.isConsecutive("not-a-date", "2026-03-01"))
    }
}
