import SwiftUI

struct AboutView: View {
    @Environment(LocalizationManager.self) private var localization

    var body: some View {
        List {
            Section {
                VStack(spacing: 8) {
                    if let img = UIImage(named: "splash_logo") {
                        Image(uiImage: img)
                            .resizable()
                            .scaledToFit()
                            .frame(width: 80, height: 80)
                            .clipShape(RoundedRectangle(cornerRadius: 18))
                    }
                    Text(appTitle)
                        .font(.system(.title3, design: .serif).weight(.bold))
                    Text("v\(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }

            Section(dataSources) {
                creditRow(
                    title: "crkvenikalendar.com",
                    detail: saintBiosSr
                )
                creditRow(
                    title: "pravoslavno.rs",
                    detail: readingsSr
                )
                creditRow(
                    title: "azbyka.ru",
                    detail: saintBiosRu
                )
                creditRow(
                    title: "orthocal.info",
                    detail: readingsEnBios
                )
                creditRow(
                    title: "holytrinityorthodox.com",
                    detail: readingsEn
                )
            }

            Section(algorithms) {
                creditRow(
                    title: paschalionTitle,
                    detail: paschalionDetail
                )
                creditRow(
                    title: lectionaryTitle,
                    detail: lectionaryDetail
                )
                creditRow(
                    title: fastingTitle,
                    detail: fastingDetail
                )
            }

            Section(content) {
                creditRow(
                    title: prologTitle,
                    detail: prologDetail
                )
                creditRow(
                    title: bibleTitle,
                    detail: bibleDetail
                )
            }

            Section {
                Text(disclaimer)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle(aboutTitle)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func creditRow(title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            Text(detail)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 2)
    }

    // MARK: - Localized strings

    private var aboutTitle: String {
        switch localization.language {
        case .sr: return "О апликацији"
        case .ru: return "О приложении"
        case .en, .en_nc: return "About"
        }
    }

    private var appTitle: String {
        switch localization.language {
        case .sr: return "Православни Календар"
        case .ru: return "Православный Календарь"
        case .en, .en_nc: return "Orthodox Calendar"
        }
    }

    private var dataSources: String {
        switch localization.language {
        case .sr: return "Извори података"
        case .ru: return "Источники данных"
        case .en, .en_nc: return "Data Sources"
        }
    }

    private var algorithms: String {
        switch localization.language {
        case .sr: return "Алгоритми"
        case .ru: return "Алгоритмы"
        case .en, .en_nc: return "Algorithms"
        }
    }

    private var content: String {
        switch localization.language {
        case .sr: return "Садржај"
        case .ru: return "Содержание"
        case .en, .en_nc: return "Content"
        }
    }

    private var saintBiosSr: String {
        switch localization.language {
        case .sr: return "Житија светих — Охридски Пролог"
        case .ru: return "Жития святых (сербские) — Охридский Пролог"
        case .en, .en_nc: return "Serbian saint biographies — Ohrid Prologue"
        }
    }

    private var readingsSr: String {
        switch localization.language {
        case .sr: return "Светитељи и читања (српски)"
        case .ru: return "Святые и чтения (сербские)"
        case .en, .en_nc: return "Saints and readings (Serbian)"
        }
    }

    private var saintBiosRu: String {
        switch localization.language {
        case .sr: return "Житија светих (руски)"
        case .ru: return "Жития святых (русские)"
        case .en, .en_nc: return "Saint biographies (Russian)"
        }
    }

    private var readingsEnBios: String {
        switch localization.language {
        case .sr: return "Житија светих и читања (енглески)"
        case .ru: return "Жития святых и чтения (английские)"
        case .en, .en_nc: return "Saint biographies and readings (English)"
        }
    }

    private var readingsEn: String {
        switch localization.language {
        case .sr: return "Библијска читања (енглески)"
        case .ru: return "Библейские чтения (английские)"
        case .en, .en_nc: return "Bible readings (English)"
        }
    }

    private var paschalionTitle: String {
        switch localization.language {
        case .sr: return "Пасхалион"
        case .ru: return "Пасхалия"
        case .en, .en_nc: return "Paschalion"
        }
    }

    private var paschalionDetail: String {
        switch localization.language {
        case .sr: return "Алгоритам Меeуса за израчунавање датума Васкрса"
        case .ru: return "Алгоритм Меeуса для вычисления даты Пасхи"
        case .en, .en_nc: return "Meeus algorithm for computing the date of Pascha"
        }
    }

    private var lectionaryTitle: String {
        switch localization.language {
        case .sr: return "Типикон лекционар"
        case .ru: return "Типикон лекционарий"
        case .en, .en_nc: return "Typikon Lectionary"
        }
    }

    private var lectionaryDetail: String {
        switch localization.language {
        case .sr: return "Алгоритам за дневна читања по Типикону"
        case .ru: return "Алгоритм дневных чтений по Типикону"
        case .en, .en_nc: return "Algorithm for daily readings according to the Typikon"
        }
    }

    private var fastingTitle: String {
        switch localization.language {
        case .sr: return "Правила поста"
        case .ru: return "Правила поста"
        case .en, .en_nc: return "Fasting Rules"
        }
    }

    private var fastingDetail: String {
        switch localization.language {
        case .sr: return "7 нивоа поста по Типикону са правилима СПЦ"
        case .ru: return "7 уровней поста по Типикону с правилами РПЦ"
        case .en, .en_nc: return "7-level fasting engine based on Typikon rules"
        }
    }

    private var prologTitle: String {
        switch localization.language {
        case .sr: return "Охридски Пролог"
        case .ru: return "Охридский Пролог"
        case .en, .en_nc: return "Ohrid Prologue"
        }
    }

    private var prologDetail: String {
        switch localization.language {
        case .sr: return "Св. Николај Велимировић — житија, поуке и химне"
        case .ru: return "Свт. Николай Велимирович — жития, поучения и гимны"
        case .en, .en_nc: return "St. Nikolai Velimirovich — lives, homilies, and hymns"
        }
    }

    private var bibleTitle: String {
        switch localization.language {
        case .sr: return "Свето Писмо"
        case .ru: return "Священное Писание"
        case .en, .en_nc: return "Holy Scripture"
        }
    }

    private var bibleDetail: String {
        switch localization.language {
        case .sr: return "Текстови из Библије на српском, руском и енглеском"
        case .ru: return "Тексты из Библии на сербском, русском и английском"
        case .en, .en_nc: return "Bible texts in Serbian, Russian, and English"
        }
    }

    private var disclaimer: String {
        switch localization.language {
        case .sr: return "Ова апликација је независни пројекат и није званични производ ниједне црквене организације. Подаци су прикупљени из јавно доступних извора ради духовне користи верника."
        case .ru: return "Это приложение является независимым проектом и не является официальным продуктом какой-либо церковной организации. Данные собраны из общедоступных источников для духовной пользы верующих."
        case .en, .en_nc: return "This app is an independent project and is not an official product of any church organization. Data is gathered from publicly available sources for the spiritual benefit of the faithful."
        }
    }
}
