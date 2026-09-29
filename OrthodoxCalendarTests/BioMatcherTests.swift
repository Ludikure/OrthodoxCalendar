import XCTest
@testable import Orthodox_Calendar

/// `BioMatcher.assign` decides which biography opens under each saint card, and
/// its stated rule is that a wrong bio is worse than none. These are the cases
/// CLAUDE.md documents as the reason the matcher looks the way it does.
///
/// `scripts/shared/simulate_bio_matching.py` is the reference implementation —
/// if a rule changes there, the expectation here changes with it.
final class BioMatcherTests: XCTestCase {

    private func assignment(_ feasts: [String], _ titles: [String], moveable: [Bool]? = nil) -> [Int: Int] {
        BioMatcher.assign(feastNames: feasts, moveable: moveable ?? Array(repeating: false, count: feasts.count),
                          bioTitles: titles)
    }

    func testInflectedNameMatchesTheFeast() {
        // Вартоломеј / Вартоломеја — the same saint in a different case.
        XCTAssertEqual(assignment(["Св. апостол Вартоломеј"], ["Вартоломеј, један од седмориједесеторих"]), [0: 0])
    }

    func testSpellingVariantMatches() {
        XCTAssertEqual(assignment(["Прп. Јевстатије"], ["Евстатије Преподобни"]), [0: 0])
    }

    func testOneSubstitutionInsideAShortNameDoesNotMatch() {
        // Матија and Марија are different saints; edit distance alone would
        // happily pair them. Needs a second bio: a day carrying exactly one
        // biography is the legacy "one combined text for the day" case, where
        // the bio goes to the first fixed feast without scoring.
        let result = assignment(["Прп. Матија", "Прп. Марија"], ["Неко", "Марија"])
        XCTAssertEqual(result[1], 1)
        XCTAssertNil(result[0], "Матија must not take the biography of Марија")
    }

    func testSingleBioDayIsAssignedWithoutScoring() {
        // Legacy data ships one combined biography for a whole day, so on a day
        // with a single bio the matcher hands it to the first fixed feast
        // whatever the title says. Deliberate; it is why the tests below carry
        // a second candidate when they care about scoring.
        XCTAssertEqual(assignment(["Прп. Матија"], ["Марија"]), [0: 0])
    }

    func testExactTitleBeatsATyingNeighbouringFeast() {
        // "Constantine and Helen" sits next to "Helen of Dechani". The greedy
        // pass breaks score ties by position, so without the exact-title rule
        // the Dechani bio would land on the first feast.
        let feasts = ["Св. цар Константин и царица Јелена", "Преп. Јелена Дечанска"]
        let titles = ["Јелена Дечанска"]
        XCTAssertEqual(assignment(feasts, titles), [1: 0])
    }

    func testMoveableFeastsNeverGetABio() {
        // Moveable entries are injected algorithmically; their biography text
        // comes from Feast.description instead.
        let feasts = ["Св. Никола", "Воскресение Христово"]
        let moveable = [false, true]
        XCTAssertEqual(BioMatcher.assign(feastNames: feasts, moveable: moveable, bioTitles: ["Никола"]), [0: 0])
        XCTAssertEqual(BioMatcher.assign(feastNames: ["Воскресение Христово"], moveable: [true],
                                         bioTitles: ["Воскресение Христово"]), [:])
    }

    func testRankAndPlaceWordsCarryNoIdentity() {
        // "прп.", "свети", "мученик" and the like are ignored on both sides, so
        // the name alone decides the pairing.
        XCTAssertEqual(BioMatcher.significant("Прп. Матија"), ["матија"])
        XCTAssertEqual(assignment(["Прп. Савва", "Прп. Матија"], ["Савва Освећени", "Неко"]), [0: 0])
    }

    func testCountMismatchReturnsNothingRatherThanGuessing() {
        XCTAssertEqual(BioMatcher.assign(feastNames: ["А", "Б"], moveable: [false], bioTitles: ["А"]), [:])
    }
}
