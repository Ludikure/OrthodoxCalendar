#!/usr/bin/env python3
"""
Scrape pravoslavno.rs's fasting calendar ("Календар поста") into per-day levels.

This is the SPC reference the sr fasting engine is validated against
(scripts/serbian/validate_spc_fasting.py). The month table the saints scraper
reads (q=kalendar) only prints the word "пост" in its fasting column — on Pascha
and all of Bright Week too — so it says nothing about the level. The fasting
calendar (q=post) prints the level on each day: СУХО (dry eating), ВОДА (no oil),
ВИНО (wine, no oil), УЉЕ (oil), РИБА (fish), БЕЛИ МРС (Cheese Week: dairy, eggs
and fish), plus feast labels (БОЖИЋ, ВАСКРС, ЦВЕТИ). It prints nothing at all on
fast-free days — and nothing on the no-food days either (Clean Monday to
Wednesday, Great Friday), so "unmarked" only means free outside the fasts.

Usage:  python3 scripts/serbian/scrape_pravoslavno_fasting.py 2025 2037
Output: data/processed/sr/pravoslavno_fasting.json
        {"YYYY-MM-DD": {"markers": ["ВОДА"], "note": "Св. Агатоник"}, ...}
Pages are cached in data/raw/sr/post/ (gitignored); a re-run fetches nothing.

The page takes the month as `gome=<year><month>`, month unpadded (gome=20259 is
September 2025). `godina`/`mesec`, which the month table uses, are ignored here
and silently return the current month, so every page's title is checked against
the month asked for.
"""
import calendar, html, json, os, re, subprocess, sys, time

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CACHE = os.path.join(ROOT, "data", "raw", "sr", "post")
OUT = os.path.join(ROOT, "data", "processed", "sr", "pravoslavno_fasting.json")
MONTHS = "Јануар Фебруар Март Април Мај Јун Јул Август Септембар Октобар Новембар Децембар".split()
MARKERS = ["БЕЛИ МРС", "СУХО", "ВОДА", "ВИНО", "УЉЕ", "РИБА", "БОЖИЋ", "ВАСКРС", "ЦВЕТИ"]
MARKER_RE = re.compile("|".join(MARKERS))


def page(year: int, month: int) -> str:
    path = os.path.join(CACHE, f"pravoslavno_post_{year}_{month:02d}.html")
    if not os.path.exists(path) or os.path.getsize(path) < 5000:
        os.makedirs(CACHE, exist_ok=True)
        url = f"https://www.pravoslavno.rs/index.php?q=post&gome={year}{month}"
        subprocess.run(["curl", "-sL", "--max-time", "40", "-A", "OrthodoxCalendarApp/1.0", url, "-o", path], check=True)
        time.sleep(1.5)
    return open(path, encoding="utf-8", errors="ignore").read()


def text_lines(raw: str) -> list:
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    s = re.sub(r"<br\s*/?>|</(tr|p|div|li|h\d|td)>", "\n", s)
    lines = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", l))).strip() for l in s.split("\n")]
    return [l for l in lines if l]


def parse_month(raw: str, year: int, month: int) -> dict:
    lines = text_lines(raw)
    want = f"{MONTHS[month - 1]} {year}"
    title = next((i for i, l in enumerate(lines) if l == want), None)
    if title is None:
        shown = next((l for l in lines if re.fullmatch(rf"({'|'.join(MONTHS)}) 20\d\d", l)), "?")
        raise SystemExit(f"{year}-{month:02d}: page shows '{shown}', not '{want}'")
    days, cur, started = {}, None, False
    for line in lines[title + 1:]:
        m = re.fullmatch(r"(?:ДАНАС )?(\d{1,2})", line)
        if m:
            d = int(m.group(1))
            if d == 1 and not started:
                started = True
            elif started and cur is not None and d < cur:
                break               # the next month's filler cells
            cur = d if started else None
            continue
        if not cur:
            continue                # the previous month's filler cells
        entry = days.setdefault(cur, {"markers": [], "note": []})
        found = MARKER_RE.findall(line)
        for f in found:
            if f not in entry["markers"]:
                entry["markers"].append(f)
        rest = MARKER_RE.sub("", line).strip(" /")
        if rest:
            entry["note"].append(rest)
    out = {}
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        e = days.get(d, {"markers": [], "note": []})
        note = ""
        for frag in e["note"]:          # names are wrapped mid-word by the page
            note += (" " if note and frag[:1].isupper() else "") + frag
        out[f"{year}-{month:02d}-{d:02d}"] = {"markers": e["markers"], "note": note or None}
    return out


def main(first: int, last: int):
    data = {}
    if os.path.exists(OUT):
        data = json.load(open(OUT, encoding="utf-8"))
    for y in range(first, last + 1):
        for m in range(1, 13):
            data.update(parse_month(page(y, m), y, m))
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print(f"{OUT}: {len(data)} days")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
