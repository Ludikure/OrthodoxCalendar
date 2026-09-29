import Foundation

/// The slavas Serbian families commonly keep, offered first in the picker.
///
/// Built from the pipeline's `isSlava` flags (pravoslavno.rs) merged with
/// crkvenikalendar.rs's list of Serbian slavas, which adds the moveable ones,
/// Павловдан, and the second commemoration on days both keep (Лучиндан beside
/// St Peter of Cetinje, Ћириловдан beside St Auxentius). Dates are Julian —
/// the civil date is 13 days later — or a distance from Pascha. Any other
/// commemoration can still be chosen by searching the whole calendar, and a
/// date the calendar doesn't name through "Други датум".
enum SlavaCatalog {
    static let common: [SlavaDay] = moveable + fixed

    /// The slava `feast` is, on `day`, or nil when it isn't one.
    ///
    /// A day can hold two slavas (Лучиндан beside St Peter of Cetinje), so the
    /// common list is matched by name, not just date. A feast the data flags as
    /// a slava but the list doesn't name still counts, kept by its church date.
    static func slava(for feast: Feast, on day: CalendarDay) -> SlavaDay? {
        let name = SaintSearchView.fold(feast.name)
        let sameDay = common.filter { $0.matches(day) }
        if let hit = sameDay.first(where: {
            name.contains(SaintSearchView.fold($0.name)) || name.contains(SaintSearchView.fold($0.saint))
        }) {
            return hit
        }
        guard feast.isSlava, !feast.moveable else { return nil }
        let parts = day.julianDate.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 2 else { return nil }
        return SlavaDay(feast.name, feast.name, .julian(month: parts[0], day: parts[1]))
    }

    static let moveable: [SlavaDay] = [
        SlavaDay("Лазарева субота", "Васкрсење праведног Лазара", .pascha(offset: -8)),
        SlavaDay("Цвети", "Улазак Господа Исуса Христа у Јерусалим", .pascha(offset: -7)),
        SlavaDay("Спасовдан", "Вазнесење Господње", .pascha(offset: 39)),
        SlavaDay("Тројичиндан", "Педесетница – Силазак Светог Духа", .pascha(offset: 49)),
        SlavaDay("Духовдан", "Духовски понедељак – Дан Светог Духа", .pascha(offset: 50)),
    ]

    /// In civil-calendar order through the year (January 2 is Julian 20 December).
    static let fixed: [SlavaDay] = [
        SlavaDay("Игњатијевдан", "Свети Игњатије Богоносац", .julian(month: 12, day: 20)),
        SlavaDay("Божић", "Рождество Христово", .julian(month: 12, day: 25)),
        SlavaDay("Стевањдан", "Свети првомученик и архиђакон Стефан", .julian(month: 12, day: 27)),
        SlavaDay("Василијевдан", "Свети Василије Велики", .julian(month: 1, day: 1)),
        SlavaDay("Богојављење", "Крштење Господње", .julian(month: 1, day: 6)),
        SlavaDay("Јовањдан", "Сабор светог Јована Крститеља", .julian(month: 1, day: 7)),
        SlavaDay("Савиндан", "Свети Сава, први архиепископ српски", .julian(month: 1, day: 14)),
        SlavaDay("Часне вериге", "Часне вериге светог апостола Петра", .julian(month: 1, day: 16)),
        SlavaDay("Трифундан", "Свети мученик Трифун", .julian(month: 2, day: 1)),
        SlavaDay("Сретење", "Сретење Господње", .julian(month: 2, day: 2)),
        SlavaDay("Симеоновдан", "Свети Симеон Богопримац и Ана пророчица", .julian(month: 2, day: 3)),
        SlavaDay("Ћириловдан", "Свети Кирило Словенски", .julian(month: 2, day: 14)),
        SlavaDay("Свети Авксентије", "Преподобни Авксентије", .julian(month: 2, day: 14)),
        SlavaDay("Младенци", "Светих четрдесет мученика Севастијских", .julian(month: 3, day: 9)),
        SlavaDay("Благовести", "Благовештење Пресвете Богородице", .julian(month: 3, day: 25)),
        SlavaDay("Ђурђевдан", "Свети великомученик Георгије", .julian(month: 4, day: 23)),
        SlavaDay("Марковдан", "Свети апостол и јеванђелист Марко", .julian(month: 4, day: 25)),
        SlavaDay("Свети Василије Острошки", "Свети Василије Острошки Чудотворац", .julian(month: 4, day: 29)),
        SlavaDay("Јеремијевдан", "Свети пророк Јеремија", .julian(month: 5, day: 1)),
        SlavaDay("Јовањдан пролетњи", "Свети апостол и јеванђелист Јован Богослов", .julian(month: 5, day: 8)),
        SlavaDay("Летњи Никола", "Пренос моштију светог Николаја", .julian(month: 5, day: 9)),
        SlavaDay("Ћирило и Методије", "Свети Кирило и Методије", .julian(month: 5, day: 11)),
        SlavaDay("Цар Константин и царица Јелена", "Свети цар Константин и царица Јелена", .julian(month: 5, day: 21)),
        SlavaDay("Видовдан", "Свети кнез Лазар и свети српски мученици", .julian(month: 6, day: 15)),
        SlavaDay("Ивањдан", "Рођење светог Јована Претече", .julian(month: 6, day: 24)),
        SlavaDay("Петровдан", "Свети апостоли Петар и Павле", .julian(month: 6, day: 29)),
        SlavaDay("Павловдан", "Сабор светих дванаест апостола", .julian(month: 6, day: 30)),
        SlavaDay("Прокопијевдан", "Свети великомученик Прокопије", .julian(month: 7, day: 8)),
        SlavaDay("Свети арханђел Гаврило", "Сабор светог арханђела Гаврила", .julian(month: 7, day: 13)),
        SlavaDay("Огњена Марија", "Света великомученица Марина", .julian(month: 7, day: 17)),
        SlavaDay("Илиндан", "Свети пророк Илија", .julian(month: 7, day: 20)),
        SlavaDay("Блага Марија", "Света Марија Магдалина", .julian(month: 7, day: 22)),
        SlavaDay("Света Петка Римљанка", "Преподобномученица Параскева Римљанка", .julian(month: 7, day: 26)),
        SlavaDay("Пантелијевдан", "Свети великомученик Пантелејмон", .julian(month: 7, day: 27)),
        SlavaDay("Преображење", "Преображење Господње", .julian(month: 8, day: 6)),
        SlavaDay("Велика Госпојина", "Успеније Пресвете Богородице", .julian(month: 8, day: 15)),
        SlavaDay("Усековање", "Усековање главе светог Јована Крститеља", .julian(month: 8, day: 29)),
        SlavaDay("Мала Госпојина", "Рођење Пресвете Богородице", .julian(month: 9, day: 8)),
        SlavaDay("Свети Јоаким и Ана", "Свети праведници Јоаким и Ана", .julian(month: 9, day: 9)),
        SlavaDay("Крстовдан", "Воздвижење часног Крста", .julian(month: 9, day: 14)),
        SlavaDay("Зачеће светог Јована", "Зачеће светог Јована Претече и Крститеља", .julian(month: 9, day: 23)),
        SlavaDay("Јовањдан јесењи", "Свети апостол и јеванђелист Јован Богослов", .julian(month: 9, day: 26)),
        SlavaDay("Михољдан", "Преподобни Киријак Отшелник", .julian(month: 9, day: 29)),
        SlavaDay("Покров Пресвете Богородице", "Покров Пресвете Богородице", .julian(month: 10, day: 1)),
        SlavaDay("Томиндан", "Свети апостол Тома", .julian(month: 10, day: 6)),
        SlavaDay("Срђевдан", "Свети мученици Сергије и Вакх", .julian(month: 10, day: 7)),
        SlavaDay("Петковица", "Преподобна мати Параскева Трнова", .julian(month: 10, day: 14)),
        SlavaDay("Лучиндан", "Свети апостол и јеванђелист Лука", .julian(month: 10, day: 18)),
        SlavaDay("Свети Петар Цетињски", "Свети Петар Цетињски", .julian(month: 10, day: 18)),
        SlavaDay("Свети Прохор Пчињски", "Преподобни Прохор Пчињски", .julian(month: 10, day: 19)),
        SlavaDay("Митровдан", "Свети великомученик Димитрије", .julian(month: 10, day: 26)),
        SlavaDay("Свети Аврамије", "Свети Аврамије Затворник", .julian(month: 10, day: 29)),
        SlavaDay("Врачеви", "Свети Козма и Дамјан", .julian(month: 11, day: 1)),
        SlavaDay("Ђурђиц", "Обновљење храма светог великомученика Георгија", .julian(month: 11, day: 3)),
        SlavaDay("Аранђеловдан", "Сабор светог арханђела Михаила", .julian(month: 11, day: 8)),
        SlavaDay("Мратиндан", "Свети краљ Стефан Дечански", .julian(month: 11, day: 11)),
        SlavaDay("Свети Јован Милостиви", "Свети Јован Милостиви", .julian(month: 11, day: 12)),
        SlavaDay("Свети Јован Златоусти", "Свети Јован Златоусти", .julian(month: 11, day: 13)),
        SlavaDay("Матејевдан", "Свети апостол и јеванђелист Матеј", .julian(month: 11, day: 16)),
        SlavaDay("Ваведење", "Ваведење Пресвете Богородице", .julian(month: 11, day: 21)),
        SlavaDay("Свети Алимпије", "Преподобни Алимпије Столпник", .julian(month: 11, day: 26)),
        SlavaDay("Андрејевдан", "Свети апостол Андреј Првозвани", .julian(month: 11, day: 30)),
        SlavaDay("Никољдан", "Свети Николај Чудотворац", .julian(month: 12, day: 6)),
    ]
}
