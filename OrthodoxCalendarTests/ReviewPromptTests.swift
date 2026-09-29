import XCTest
@testable import Orthodox_Calendar

/// The rating ask counts separate days of use, not launches, and fires at most
/// once per app version.
final class ReviewPromptTests: XCTestCase {
    private var defaults: UserDefaults!
    private let suite = "ReviewPromptTests"

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: suite)
        defaults.removePersistentDomain(forName: suite)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suite)
        super.tearDown()
    }

    private func day(_ n: Int) -> Date {
        DateKeys.date(from: "2026-09-01")!.addingTimeInterval(TimeInterval(n) * 86_400 + 3_600)
    }

    func testSameDayCountsOnce() {
        let prompt = ReviewPrompt(defaults: defaults, version: "1.5.0")
        for _ in 0..<10 { prompt.recordActive(on: day(0)) }
        XCTAssertEqual(prompt.activeDays, 1)
        XCTAssertFalse(prompt.shouldPrompt)
    }

    func testAsksAfterRequiredDays() {
        let prompt = ReviewPrompt(defaults: defaults, version: "1.5.0")
        for n in 0..<(ReviewPrompt.requiredDays - 1) { prompt.recordActive(on: day(n)) }
        XCTAssertFalse(prompt.shouldPrompt)
        prompt.recordActive(on: day(ReviewPrompt.requiredDays))
        XCTAssertTrue(prompt.shouldPrompt)
    }

    func testOncePerVersion() {
        let prompt = ReviewPrompt(defaults: defaults, version: "1.5.0")
        for n in 0..<ReviewPrompt.requiredDays { prompt.recordActive(on: day(n)) }
        prompt.markPrompted()
        for n in 10..<30 { prompt.recordActive(on: day(n)) }
        XCTAssertFalse(prompt.shouldPrompt)

        // A new version starts from the days used since the last ask.
        let next = ReviewPrompt(defaults: defaults, version: "1.6.0")
        XCTAssertTrue(next.shouldPrompt)
    }
}
