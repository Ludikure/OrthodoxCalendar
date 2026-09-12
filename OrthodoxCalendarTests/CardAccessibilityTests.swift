import XCTest
@testable import Orthodox_Calendar

/// The day-detail cards hold their whole biography or scripture passage
/// inside the card, so the label is the only thing VoiceOver reads there. Two
/// opposite failures live on this line: text that is never announced (an
/// opened card that stays silent), and text announced while it is hidden (a
/// collapsed card read aloud, thousands of characters before the reader can
/// say "expand").
final class CardAccessibilityTests: XCTestCase {

    func testCollapsedCardLabelNamesTheSubjectOnly() {
        XCTAssertEqual(CardAccessibility.summary(localizedType: "Светитель",
                                                 subject: "Свети Никола",
                                                 text: nil),
                       "Светитель: Свети Никола")
    }

    func testExpandedCardIncludesItsText() {
        XCTAssertEqual(CardAccessibility.summary(localizedType: "Празник",
                                                 subject: "Рождество Христово",
                                                 text: "Дева днес"),
                       "Празник: Рождество Христово. Дева днес")
    }

    func testEmptyTextIsTreatedAsAbsent() {
        // `CalendarRepository.resolveText` hands back `text == ""` when the
        // shipped pool has no entry for a ref; that must not leave a label
        // ending in ". ".
        XCTAssertEqual(CardAccessibility.summary(localizedType: "Martyr",
                                                 subject: "New Hieromartyr Cyril",
                                                 text: ""),
                       "Martyr: New Hieromartyr Cyril")
    }
}
