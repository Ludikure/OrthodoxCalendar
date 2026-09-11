import XCTest
@testable import Orthodox_Calendar

/// A date after a day number reads as the language writes it: Russian declines
/// the month ("19 декабря", not the header form "19 Декабрь"); the other
/// languages use their month names as they are. Checked against the bundled files.
final class DayAndMonthTests: XCTestCase {
    private func labels(_ lang: String) throws -> UILabels {
        let url = try XCTUnwrap(Bundle.main.url(forResource: lang, withExtension: "json"))
        return try JSONDecoder().decode(LocalizationBundle.self, from: Data(contentsOf: url)).ui
    }

    func testRussianTakesTheGenitive() throws {
        let ru = try labels("ru")
        XCTAssertEqual(ru.dayAndMonth(19, 12), "19 декабря")
        XCTAssertEqual(ru.dayAndMonth(2, 5), "2 мая")
        XCTAssertEqual(ru.monthsGenitive?.count, 12)
    }

    func testOtherLanguagesKeepTheirMonthNames() throws {
        XCTAssertEqual(try labels("en").dayAndMonth(19, 12), "19 December")
        XCTAssertEqual(try labels("sr").dayAndMonth(19, 12), "19 Децембар")
    }

    func testAnOutOfRangeMonthLeavesTheDay() throws {
        XCTAssertEqual(try labels("ru").dayAndMonth(7, 13), "7")
    }
}
