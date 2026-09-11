# Release notes — 1.4.4 (build 17)

**The App Store is on 1.2.3**, released 2026-08-04 (checked via
`curl "https://itunes.apple.com/lookup?id=6761862951"`). Versions 1.3.0 through
1.4.3 were tagged in git but never reached the store, so this release carries
roughly five months of work to users in one step — write the notes for someone
coming from 1.2.3, not from 1.4.3.

App Store "What's New" allows 4000 characters per localization. The three below
are well inside it.

---

## English (en-US)

```
All years 2024–2099
Browse the whole liturgical calendar, far back or far ahead. 2025–2030 are built into the app and work with no connection; any other year downloads once and stays on your device.

Fasting seasons at a glance
Great Lent, the Apostles', Dormition and Nativity fasts now appear as a banner with their dates and the day within them.

Scripture readings
Missing and truncated readings repaired across all three languages. English readings now use the King James Version with the Brenton Septuagint for the Old Testament, and the World English Bible is selectable for the New.

Saint biographies
Rebuilt from their original sources and matched to the saint they belong to — many were previously shown under the wrong commemoration.

English (New Calendar)
Corrected: feasts and fasting periods now fall on their proper Revised Julian dates. Christmas is no longer inside the Nativity Fast, and each great feast appears once rather than twice.

Also fixed
• Reminders saved for the correct day, with a clear message if one can't be added
• Month arrows no longer step outside the available years
• A year that can't be loaded says so, instead of blaming your connection
• The fasting banner no longer shows a fast that has ended or not yet begun
• The Beheading of St John, the Exaltation of the Cross and Theophany Eve are marked as fast days again
• Empty commemoration cards removed
• Faster launch and snappier haptics
```

## Serbian (sr)

```
Све године 2024–2099
Листајте цео литургијски календар, далеко уназад или унапред. Године 2025–2030 су уграђене у апликацију и раде без интернета; свака друга година се преузме једном и остаје на уређају.

Постови на први поглед
Часни, Петровски, Госпојински и Божићни пост сада се приказују у траци са датумима и даном поста.

Читања
Исправљена недостајућа и одсечена читања на сва три језика.

Житија светих
Поново састављена из изворних текстова и придружена правом свецу — многа су раније стајала уз погрешан спомен.

Пост
Пост сада прати календар СПЦ дан по дан: строги дани су на води, а уље и риба само где их Црква разрешава. Усековање, Воздвижење и Богојављенски Крстовдан поново су постни дани.

Још исправки
• Подсетници се чувају на тачан дан, уз јасну поруку ако додавање не успе
• Стрелице за месец више не излазе из доступних година
• Година која се не може учитати то и каже, уместо да криви везу
• Трака о посту више не приказује пост који је завршен или још није почео
• Уклоњене празне картице спомена
• Брже покретање и одзивнији хаптички одговор
```

## Russian (ru)

```
Все годы с 2024 по 2099
Листайте весь литургический календарь далеко назад или вперёд. Годы 2025–2030 встроены в приложение и работают без интернета; любой другой год загружается один раз и остаётся на устройстве.

Посты сразу видны
Великий, Петров, Успенский и Рождественский посты показываются баннером с датами и днём поста.

Чтения
Исправлены отсутствующие и обрезанные чтения на всех трёх языках, включая составные отрывки из разных глав.

Жития святых
Заново собраны из первоисточников и привязаны к своему святому — многие прежде стояли рядом с чужой памятью.

Ещё исправлено
• Напоминания сохраняются на верный день, с понятным сообщением при ошибке
• Стрелки месяцев больше не выходят за доступные годы
• Год, который не удалось загрузить, так и сообщает, а не винит соединение
• Баннер поста больше не показывает уже закончившийся или не начавшийся пост
• Усекновение главы Иоанна Предтечи, Воздвижение Креста и Крещенский сочельник снова отмечены как постные дни
• Убраны пустые карточки памяти
• Быстрее запуск и отзывчивее тактильная отдача
```

---

## Before submitting

- `minVersion` in `worker/config.json` is `1.2.0` and `latestVersion` is `1.2.3`,
  both deliberately matching the store. Once 1.4.4 is approved, set
  `latestVersion` to `1.4.4` and republish with
  `python3 scripts/shared/upload_r2_v2.py data/archive_v2/files --config`.
  Leave `minVersion` alone until you are willing to wall off 1.2.3 users — and
  remember one value gates the Android app too, which is on a different version
  line (see PARITY.md in the Android repo).
- **The fasting fix changes the archive.** `worker/config.json` is at `dataRevision: 6`,
  and the regenerated 2024–2099 archive has to be published
  (`upload_r2_v2.py <dir> --config`) before this release goes out, or years
  downloaded from R2 keep the old fasting while the bundled ones show the new.
  Only `fasting` differs from the published archive, apart from five `en_nc`
  days — Apr 7 in 2058, 2069, 2075, 2080 and 2086 — that gain the Palm Sunday
  or Pascha marking the old build lost (it took Apr 7 for the Julian
  Annunciation). The text pools are byte-identical, so this publish needs no
  `--shipped-pools` inlining.
- `--shipped-pools` was skipped on the last publishes because no released build
  reads the v2 archive. **That stops being true the moment 1.4.4 ships.** The next
  regeneration after this release must pass `--shipped-pools` pointing at 1.4.4's
  bundled `texts_*.json`, or downloaded years will render empty text on it.
