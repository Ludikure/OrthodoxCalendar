import XCTest
@testable import Orthodox_Calendar

/// A slava lands on the day the calendar shows for it, in every year, and
/// the reminder wording follows Serbian grammar and the day's fast.
final class SlavaTests: XCTestCase {

    private func ymd(_ date: Date?) -> String {
        guard let date else { return "nil" }
        return DateKeys.key(from: date)
    }

    private func date(_ key: String) -> Date { DateKeys.date(from: key)! }

    /// The bundled Serbian years, as the app loads them.
    private func bundledYears() throws -> [CalendarFile] {
        let urls = Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []
        let files = try urls.filter { $0.lastPathComponent.hasPrefix("calendar_sr_") }
            .map { try JSONDecoder().decode(CalendarFile.self, from: Data(contentsOf: $0)) }
        XCTAssertFalse(files.isEmpty, "no bundled Serbian years found")
        return files
    }

    func testPaschalionAgreesWithEveryBundledYear() throws {
        for file in try bundledYears() {
            let pascha = try XCTUnwrap(file.days.values.first { $0.paschaDistance == 0 })
            XCTAssertEqual(ymd(Paschalion.pascha(year: file.year)), pascha.gregorianDate, "year \(file.year)")
        }
        // Outside the bundle too, against the published Paschalion.
        XCTAssertEqual(ymd(Paschalion.pascha(year: 2024)), "2024-05-05")
        XCTAssertEqual(ymd(Paschalion.pascha(year: 2034)), "2034-04-09")
        XCTAssertEqual(ymd(Paschalion.pascha(year: 2099)), "2099-04-12")
    }

    func testFixedSlavaFallsThirteenDaysAfterItsChurchDate() {
        let nikoljdan = SlavaDay("Никољдан", "Свети Николај", .julian(month: 12, day: 6))
        XCTAssertEqual(ymd(nikoljdan.nextOccurrence(onOrAfter: date("2026-12-07"))), "2026-12-19")
        XCTAssertEqual(ymd(nikoljdan.nextOccurrence(onOrAfter: date("2026-12-19"))), "2026-12-19")
        XCTAssertEqual(ymd(nikoljdan.nextOccurrence(onOrAfter: date("2026-12-20"))), "2027-12-19")

        // Julian 25 December of 2026 is 7 January 2027.
        let bozic = SlavaDay("Божић", "Рождество Христово", .julian(month: 12, day: 25))
        XCTAssertEqual(ymd(bozic.nextOccurrence(onOrAfter: date("2026-12-20"))), "2027-01-07")
        XCTAssertEqual(ymd(bozic.nextOccurrence(onOrAfter: date("2027-01-05"))), "2027-01-07")
    }

    func testMoveableSlavaFollowsPascha() {
        let lazareva = SlavaDay("Лазарева субота", "", .pascha(offset: -8))
        XCTAssertEqual(ymd(lazareva.nextOccurrence(onOrAfter: date("2026-01-01"))), "2026-04-04")
        XCTAssertEqual(ymd(lazareva.nextOccurrence(onOrAfter: date("2026-04-05"))), "2027-04-24")
        let spasovdan = SlavaDay("Спасовдан", "", .pascha(offset: 39))
        XCTAssertEqual(ymd(spasovdan.nextOccurrence(onOrAfter: date("2026-01-01"))), "2026-05-21")
    }

    func testEveryCommonSlavaMatchesExactlyOneDayOfEachBundledYear() throws {
        for file in try bundledYears() {
            for slava in SlavaCatalog.common {
                let hits = file.days.values.filter { slava.matches($0) }.map(\.gregorianDate)
                XCTAssertEqual(hits.count, 1, "\(slava.name) in \(file.year): \(hits)")
                // And the day it matches is the day it is scheduled for.
                if let hit = hits.first, case .pascha = slava.anchor {
                    XCTAssertEqual(ymd(slava.occurrence(churchYear: file.year)), hit, slava.name)
                }
            }
        }
    }

    func testMatchedDayCarriesTheSlava() throws {
        // The data's own slava flags agree with the catalog where both name the day.
        let file = try XCTUnwrap(try bundledYears().first { $0.year == 2026 })
        let nikoljdan = try XCTUnwrap(SlavaCatalog.fixed.first { $0.name == "Никољдан" })
        let day = try XCTUnwrap(file.days["12-19"])
        XCTAssertTrue(nikoljdan.matches(day))
        XCTAssertTrue(day.feasts.contains { $0.isSlava && $0.name.contains("Никољдан") })
    }

    func testCountdownPlurals() {
        XCTAssertEqual(SeasonBanner.countdownLabel(0), "Срећна слава!")
        XCTAssertEqual(SeasonBanner.countdownLabel(1), "сутра")
        XCTAssertEqual(SeasonBanner.countdownLabel(2), "за 2 дана")
        XCTAssertEqual(SeasonBanner.countdownLabel(11), "за 11 дана")
        XCTAssertEqual(SeasonBanner.countdownLabel(21), "за 21 дан")
        XCTAssertEqual(SeasonBanner.countdownLabel(30), "за 30 дана")
    }

    func testTableFollowsTheFast() {
        XCTAssertEqual(SlavaText.table("free"), "Трпеза је мрсна.")
        XCTAssertEqual(SlavaText.table("fish"), "Трпеза је посна — риба је дозвољена.")
        XCTAssertEqual(SlavaText.table("hotNoOil"), "Трпеза је посна — на води, без уља.")
        XCTAssertEqual(SlavaText.table("dryEating"), "Трпеза је посна — строги пост.")
    }

    func testSettingsRoundTrip() throws {
        var settings = SlavaStore.Settings()
        settings.mine = SlavaCatalog.moveable[0]
        settings.friends = [FriendSlava(person: "Петровићи", slava: SlavaCatalog.fixed[0])]
        let data = try JSONEncoder().encode(settings)
        XCTAssertEqual(try JSONDecoder().decode(SlavaStore.Settings.self, from: data), settings)
    }

    func testEveryFlaggedSlavaFeastCanBeSetFromItsCard() throws {
        for file in try bundledYears() {
            for day in file.days.values {
                for feast in day.feasts where feast.isSlava {
                    let slava = try XCTUnwrap(SlavaCatalog.slava(for: feast, on: day),
                                              "\(feast.name) \(day.gregorianDate)")
                    XCTAssertTrue(slava.matches(day), "\(slava.name) \(day.gregorianDate)")
                }
            }
        }
    }

    func testTwoSlavasOnOneDayStayApart() throws {
        // 31 October: St Peter of Cetinje (flagged) and Лучиндан (not flagged).
        let file = try XCTUnwrap(try bundledYears().first { $0.year == 2026 })
        let day = try XCTUnwrap(file.days["10-31"])
        let names = day.feasts.compactMap { SlavaCatalog.slava(for: $0, on: day)?.name }
        XCTAssertEqual(Set(names), ["Свети Петар Цетињски", "Лучиндан"])
        // And an ordinary saint is not offered.
        let mina = try XCTUnwrap(file.days["11-24"]?.feasts.first { $0.name.contains("Мина") })
        XCTAssertNil(SlavaCatalog.slava(for: mina, on: try XCTUnwrap(file.days["11-24"])))
    }
}
