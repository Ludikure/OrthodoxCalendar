# App Store screenshots

Seven per language (`sr`, `ru`, `en`), in the two sizes App Store Connect asks for:

| Folder | Size | Slot |
|---|---|---|
| `iphone-6.9/<lang>/` | 1320 × 2868 | iPhone 6.9″ display — the current required size, scaled down by the store for smaller iPhones |
| `iphone-6.5/<lang>/` | 1284 × 2778 | iPhone 6.5″ display — still shown on listings that already carry one; it accepts only 1242 × 2688 or 1284 × 2778 |

Both sets are the same seven screens, framed the same way; only the canvas differs.
The App Store allows ten per size, and the first three are the ones shown in search
results.

Captured on an iPhone 17 Pro Max simulator (status bar 9:41) and framed on the crimson
and gold of the app icon. Every language shows the same days: St Nicholas in the
Nativity Fast, Great Lent, and Pascha 2027. The iPad screenshots in the listing are the
older set and were deliberately left alone — the app is universal
(`TARGETED_DEVICE_FAMILY: "1,2"`), so the store requires an iPad set, and the existing
one satisfies it.
