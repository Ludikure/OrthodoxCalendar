import XCTest
@testable import Orthodox_Calendar

/// Serbian is read in both alphabets but the `sr` data is Cyrillic-only, so
/// search folds both sides to one form before comparing. The target is Serbian
/// Latin: a Russian romanization (ч→"ch", ш→"sh", ц→"ts") leaves a Serb typing
/// the spelling they actually use matching nothing.
@MainActor
final class SaintSearchFoldingTests: XCTestCase {

    private func fold(_ s: String) -> String { SaintSearchView.fold(s) }

    /// Every Serbian Cyrillic letter, folded to the Latin a Serb would type.
    func testSerbianCyrillicFoldsToSerbianLatin() {
        let pairs: [(String, String)] = [
            ("Ђорђе", "djordje"), ("Љубомир", "ljubomir"), ("Његош", "njegos"),
            ("Ћирило", "cirilo"), ("Чудотворац", "cudotvorac"), ("Шишатовачки", "sisatovacki"),
            ("Џаџић", "dzadzic"), ("Жарко", "zarko"), ("Царица", "carica"),
        ]
        for (cyrillic, latin) in pairs {
            XCTAssertEqual(fold(cyrillic), latin, "\(cyrillic)")
        }
    }

    /// љ and њ were absent from the table entirely, so every name containing
    /// them was unreachable from a Latin query.
    func testLjAndNjAreMapped() {
        XCTAssertEqual(fold("љ"), "lj")
        XCTAssertEqual(fold("њ"), "nj")
        XCTAssertTrue(fold("Краљ Миљутин").contains("kralj"))
    }

    /// A query typed with proper Serbian diacritics folds to the same string as
    /// the same query typed without them, and as the Cyrillic it stands for.
    func testLatinDiacriticsFoldTheSameWay() {
        XCTAssertEqual(fold("Ćirilo"), fold("Cirilo"))
        XCTAssertEqual(fold("Šišatovački"), fold("Sisatovacki"))
        XCTAssertEqual(fold("Đorđe"), fold("Djordje"))
        XCTAssertEqual(fold("Žarko"), fold("Zarko"))
        XCTAssertEqual(fold("Ćirilo"), fold("Ћирило"))
    }

    /// Folding is applied to both the query and the data, so a same-script
    /// search must be unaffected by any of the above.
    func testSameScriptSearchIsUnaffected() {
        XCTAssertTrue(fold("Свети Никола").contains(fold("Никола")))
        XCTAssertTrue(fold("Преподобни Сава Псковски").contains(fold("Сава")))
        XCTAssertTrue(fold("Saint Nicholas").contains(fold("Nicholas")))
    }

    /// Case folding happens before the table lookup, so an upper-case query and
    /// a capitalised name meet in the middle.
    func testFoldingIsCaseInsensitive() {
        XCTAssertEqual(fold("НИКОЛА"), fold("никола"))
        XCTAssertEqual(fold("NIKOLA"), fold("nikola"))
        XCTAssertEqual(fold("НИКОЛА"), fold("Nikola"))
    }
}
