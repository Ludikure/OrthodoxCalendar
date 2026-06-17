#!/usr/bin/env python3
"""
Deduplicate large text (saint bios + scripture readings) across bundled
calendar year files into one per-locale pool `texts_<locale>.json`.

Bios and scripture readings repeat across years (fixed-date feasts recur), and
their full text dominates file size — especially Russian bios and the English
KJV/WEB scripture text. Each unique `text` (bio text, reading `text`, reading
`textWeb`) is extracted into the pool keyed by a content hash; the calendar
files keep only a reference:
  - SaintBio:        {title, ref}
  - ScriptureReading {…, textRef, textWebRef}
Apps resolve the refs against the pool at load.

Usage: dedup_text.py <dir>   # dedup all calendar_*_*.json in <dir> in place
Idempotent: entries already carrying a ref (no text) are skipped.
"""
import sys, os, json, hashlib, glob, re

def h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def main(directory: str) -> None:
    by_locale: dict[str, list[str]] = {}
    for f in sorted(glob.glob(os.path.join(directory, "calendar_*_*.json"))):
        m = re.match(r"calendar_(.+)_(\d{4})\.json$", os.path.basename(f))
        if m:
            by_locale.setdefault(m.group(1), []).append(f)

    for locale, files in by_locale.items():
        pool: dict[str, str] = {}
        before = after = 0
        for path in files:
            before += os.path.getsize(path)
            data = json.load(open(path, encoding="utf-8"))
            days = data["days"]
            for day in (days.values() if isinstance(days, dict) else days):
                for b in (day.get("saintBios") or []):
                    if t := b.get("text"):
                        k = h(t); pool[k] = t; b.pop("text", None); b["ref"] = k
                for r in (day.get("readings") or []):
                    if t := r.get("text"):
                        k = h(t); pool[k] = t; r.pop("text", None); r["textRef"] = k
                    if tw := r.get("textWeb"):
                        k = h(tw); pool[k] = tw; r.pop("textWeb", None); r["textWebRef"] = k
            json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            after += os.path.getsize(path)
        pool_path = os.path.join(directory, f"texts_{locale}.json")
        json.dump(pool, open(pool_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        psize = os.path.getsize(pool_path)
        print(f"{locale:6}: years {before/1e6:6.1f}->{after/1e6:5.1f}MB + pool {psize/1e6:5.1f}MB "
              f"({len(pool)} unique)  total {(after+psize)/1e6:.1f}MB (was {before/1e6:.1f})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1])
