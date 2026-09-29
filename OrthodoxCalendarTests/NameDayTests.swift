import XCTest
@testable import Orthodox_Calendar

/// Russian name days: the bundled catalog lands each name on the day the
/// calendar shows, the birthday rule picks the first commemoration on or after
/// it, and civil names map to church ones only where the mapping is trusted.
final class NameDayTests: XCTestCase {

    private let catalog = NameDayCatalog.shared

    private func ymd(_ date: Date?) -> String {
        guard let date else { return "nil" }
        return DateKeys.key(from: date)
    }

    private func date(_ key: String) -> Date { DateKeys.date(from: key)! }

    private func russianYear(_ year: Int) throws -> CalendarFile {
        let url = try XCTUnwrap(Bundle.main.url(forResource: "calendar_ru_\(year)", withExtension: "json"))
        return try JSONDecoder().decode(CalendarFile.self, from: Data(contentsOf: url))
    }

    private func day(_ file: CalendarFile, _ monthDay: String) throws -> CalendarDay {
        try XCTUnwrap(file.days[monthDay], "\(file.year)-\(monthDay)")
    }

    private func firstNameDay(_ name: String, _ month: Int, _ day: Int, year: Int = 2026,
                              newMartyrs: Bool = false) -> String {
        let hit = catalog.firstNameDay(churchForms: catalog.churchForms(for: name),
                                       birthMonth: month, birthDay: day, year: year,
                                       includeNewMartyrs: newMartyrs)
        return ymd(hit?.date)
    }

    func testCatalogIsBundled() {
        XCTAssertGreaterThan(catalog.names.count, 1000)
        XCTAssertGreaterThan(catalog.days.count, 350)
        XCTAssertFalse(catalog.civil.isEmpty)
    }

    // MARK: - A day's names

    func testTatianaOnJanuary25() throws {
        let names = catalog.names(on: try day(try russianYear(2026), "01-25"))
        XCTAssertEqual(names.first, DayName(name: "Татиана", isMain: true))
    }

    func testFaithHopeLoveSophiaOnSeptember30() throws {
        let names = catalog.names(on: try day(try russianYear(2026), "09-30"))
        XCTAssertEqual(Array(names.prefix(4).map(\.name)), ["Вера", "Надежда", "Любовь", "София"])
        XCTAssertTrue(names.prefix(4).allSatisfy(\.isMain))
    }

    func testMyrrhBearersFollowPascha() throws {
        // Pascha 2026 is 12 April; the Myrrh-bearers' Sunday two weeks later.
        let names = catalog.names(on: try day(try russianYear(2026), "04-26")).map(\.name)
        XCTAssertTrue(names.contains("Мария") && names.contains("Марфа") && names.contains("Иосиф"), "\(names)")
        XCTAssertEqual(ymd(NameDayAnchor.pascha(offset: 14).occurrence(churchYear: 2026)), "2026-04-26")
        XCTAssertEqual(ymd(NameDayAnchor.pascha(offset: 14).occurrence(churchYear: 2027)), "2027-05-16")
    }

    func testSundayAfterNativityRule() throws {
        let joseph = try XCTUnwrap(catalog.commemorations(of: "Иосиф").first {
            if case .weekday = $0.anchor { return true }
            return false
        })
        // Julian 26 December 2026 is Friday 8 January 2027: the Sunday is the 10th.
        XCTAssertEqual(ymd(joseph.anchor.occurrence(churchYear: 2026)), "2027-01-10")
        XCTAssertEqual(ymd(joseph.anchor.occurrence(churchYear: 2025)), "2026-01-11")
        // The Nativity on a Sunday (7 January 2024): kept on Monday the 8th.
        XCTAssertEqual(ymd(joseph.anchor.occurrence(churchYear: 2023)), "2024-01-08")
        // And the calendar day it lands on lists Joseph, David and James.
        let names = catalog.names(on: try day(try russianYear(2027), "01-10")).map(\.name)
        XCTAssertTrue(names.contains("Иосиф") && names.contains("Давид") && names.contains("Иаков"), "\(names)")
        XCTAssertFalse(catalog.names(on: try day(try russianYear(2027), "01-11")).map(\.name).contains("Иаков"))
    }

    func testCassianKeepsFebruary29OnlyInALeapYear() throws {
        let y2026 = try russianYear(2026), y2028 = try russianYear(2028)
        // 2026: Julian 28 February (13 March) holds him.
        XCTAssertTrue(catalog.names(on: try day(y2026, "03-13")).map(\.name).contains("Кассиан"))
        // 2028: Julian 29 February is 13 March; the 28th (12 March) does not.
        XCTAssertFalse(catalog.names(on: try day(y2028, "03-12")).map(\.name).contains("Кассиан"))
        XCTAssertTrue(catalog.names(on: try day(y2028, "03-13")).map(\.name).contains("Кассиан"))

        let cassian = try XCTUnwrap(catalog.commemorations(of: "Кассиан").first { $0.anchor == .julian(month: 2, day: 29) })
        XCTAssertEqual(ymd(cassian.anchor.occurrence(churchYear: 2026)), "2026-03-13")
        XCTAssertEqual(ymd(cassian.anchor.occurrence(churchYear: 2028)), "2028-03-13")
        XCTAssertTrue(cassian.anchor.matches(try day(y2026, "03-13")))
        XCTAssertTrue(cassian.anchor.matches(try day(y2028, "03-13")))
        XCTAssertFalse(cassian.anchor.matches(try day(y2028, "03-12")))
    }

    func testEveryDayListsMainSaintsFirstAndCapsAtTwelve() throws {
        for (key, day) in try russianYear(2026).days {
            let names = catalog.names(on: day)
            if let firstOther = names.firstIndex(where: { !$0.isMain }) {
                XCTAssertFalse(names[firstOther...].contains(where: \.isMain), key)
            }
            XCTAssertEqual(Set(names.map(\.name)).count, names.count, "duplicate name on \(key)")
            let capped = NameDayCatalog.capped(names)
            XCTAssertEqual(capped.shown.count + capped.hidden, names.count, key)
            XCTAssertEqual(capped.shown, Array(names.prefix(capped.shown.count)), key)
            XCTAssertTrue(capped.hidden == 0 || capped.shown.count == NameDayCatalog.dayListLimit, key)
        }
    }

    func testCappingOrder() {
        let list = (1...20).map { DayName(name: "n\($0)", isMain: $0 <= 3) }
        let capped = NameDayCatalog.capped(list)
        XCTAssertEqual(capped.shown.map(\.name), (1...12).map { "n\($0)" })
        XCTAssertEqual(capped.hidden, 8)
        // Hiding a single name would save nothing: all thirteen show.
        XCTAssertEqual(NameDayCatalog.capped(Array(list.prefix(13))).hidden, 0)
        XCTAssertEqual(NameDayCatalog.capped(Array(list.prefix(5))).shown.count, 5)
    }

    // MARK: - Birthday rule

    func testFirstCommemorationOnOrAfterBirthday() {
        XCTAssertEqual(firstNameDay("Татьяна", 1, 1), "2026-01-25")
        XCTAssertEqual(firstNameDay("Таня", 1, 25), "2026-01-25")        // the day itself counts
        // Next: the royal passion-bearers (Julian 4 July), who are not new martyrs.
        XCTAssertEqual(firstNameDay("Татиана", 1, 26), "2026-07-17")
        XCTAssertEqual(firstNameDay("Татиана", 1, 26, newMartyrs: true), "2026-07-17")
        // Past the year's last Tatiana (Julian 10 December = 23 December) it wraps.
        XCTAssertEqual(firstNameDay("Татьяна", 12, 24), "2027-01-25")
        // A name kept once a year wraps too: Або, Julian 8 January = 21 January.
        XCTAssertEqual(firstNameDay("Або", 1, 21), "2026-01-21")
        XCTAssertEqual(firstNameDay("Або", 1, 22), "2027-01-21")
    }

    func testNewMartyrsCountOnlyWhenAskedFor() {
        // After 17 July every Tatiana of the year is a new martyr: azbyka.ru's
        // finder skips them by default, so the name day is next 25 January.
        XCTAssertEqual(firstNameDay("Татьяна", 7, 18), "2027-01-25")
        // "Учитывать новомучеников": St Tatiana Gribkova, Julian 1 September.
        XCTAssertEqual(firstNameDay("Татьяна", 7, 18, newMartyrs: true), "2026-09-14")
    }

    func testNameWithOnlyNewMartyrsStillGetsADay() throws {
        let only = catalog.names.first { !$0.value.isEmpty && $0.value.allSatisfy(\.isNewMartyr) }
        let (name, list) = try XCTUnwrap(only, "some name has only new-martyr saints")
        let hit = catalog.firstNameDay(churchForms: [name], birthMonth: 1, birthDay: 1, year: 2026)
        XCTAssertTrue(list.contains(try XCTUnwrap(hit, name).commemoration), name)
    }

    func testBirthdayRuleReachesMoveableDates() {
        // Born 20 April: the Myrrh-bearers' Sunday (26 April 2026) is the first Salome after it.
        let hit = catalog.firstNameDay(churchForms: ["Саломия"], birthMonth: 4, birthDay: 20, year: 2026)
        XCTAssertEqual(ymd(hit?.date), "2026-04-26")
        XCTAssertEqual(hit?.commemoration.anchor, .pascha(offset: 14))
    }

    func testUsualChurchFormDecides() {
        // Юрий → Георгий first; the new martyr Юрий is only the second form.
        XCTAssertEqual(catalog.firstNameDay(churchForms: catalog.churchForms(for: "Юрий"),
                                            birthMonth: 5, birthDay: 1, year: 2026)?.commemoration.name, "Георгий")
    }

    // MARK: - Civil names

    func testCivilMapping() {
        XCTAssertEqual(catalog.churchForms(for: "Иван"), ["Иоанн"])
        XCTAssertEqual(catalog.churchForms(for: "  иван "), ["Иоанн"])
        XCTAssertEqual(catalog.churchForms(for: "Ваня"), ["Иоанн"])
        XCTAssertEqual(catalog.churchForms(for: "Юрий"), ["Георгий", "Юрий"])
        XCTAssertEqual(catalog.churchForms(for: "Пётр"), ["Петр"])
        XCTAssertEqual(catalog.churchForms(for: "Татьяна"), ["Татиана"])
        // A church name maps to itself.
        XCTAssertEqual(catalog.churchForms(for: "Иоанн"), ["Иоанн"])
    }

    func testUnsureMappingsLeftOutUnlessAzbykaGivesThem() {
        // Curators' doubts without azbyka.ru behind them: not mapped.
        XCTAssertEqual(catalog.churchForms(for: "Егор"), [])
        XCTAssertEqual(catalog.churchForms(for: "Полина"), [])
        XCTAssertEqual(catalog.churchForms(for: "Кристина"), [])
        // Маргарита is not mapped to Марина, but is a church name of its own.
        XCTAssertEqual(catalog.churchForms(for: "Маргарита"), ["Маргарита"])
        // azbyka.ru's own mappings stay.
        XCTAssertEqual(catalog.churchForms(for: "Богдан"), ["Феодот"])
        XCTAssertEqual(catalog.churchForms(for: "Жанна"), ["Иоанна"])
    }

    func testUnknownNameHasNoSaint() {
        XCTAssertEqual(catalog.churchForms(for: "Руслан"), [])
        XCTAssertEqual(catalog.churchForms(for: ""), [])
    }

    func testSuggestions() {
        let names = catalog.suggestions("Тат").map(\.name)
        XCTAssertTrue(names.contains("Татьяна") && names.contains("Татиана"), "\(names)")
        XCTAssertEqual(catalog.suggestions("Ваня").first?.church, "Иоанн")
    }

    // MARK: - Store and wording

    func testMarkAndSettingsRoundTrip() throws {
        let file = try russianYear(2026)
        let tatiana = NameDayChoice(name: "Таня", churchName: "Татиана", title: "Мц. Татианы Римской",
                                    anchor: .julian(month: 1, day: 12), birthMonth: 1, birthDay: 1)
        XCTAssertTrue(tatiana.matches(try day(file, "01-25")))
        XCTAssertFalse(tatiana.matches(try day(file, "01-24")))

        var settings = NameDayStore.Settings()
        settings.mine = tatiana
        settings.friends = [FriendNameDay(person: "мама", nameDay: tatiana)]
        let data = try JSONEncoder().encode(settings)
        XCTAssertEqual(try JSONDecoder().decode(NameDayStore.Settings.self, from: data), settings)
    }

    func testCountdownPlurals() {
        XCTAssertEqual(NameDayText.countdown(0), "С днём ангела!")
        XCTAssertEqual(NameDayText.countdown(1), "завтра")
        XCTAssertEqual(NameDayText.countdown(2), "через 2 дня")
        XCTAssertEqual(NameDayText.countdown(5), "через 5 дней")
        XCTAssertEqual(NameDayText.countdown(11), "через 11 дней")
        XCTAssertEqual(NameDayText.countdown(12), "через 12 дней")
        XCTAssertEqual(NameDayText.countdown(21), "через 21 день")
        XCTAssertEqual(NameDayText.countdown(22), "через 22 дня")
        XCTAssertEqual(NameDayText.countdown(30), "через 30 дней")
    }
}
