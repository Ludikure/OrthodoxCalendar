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

Usage: dedup_text.py <dir> [--keep-from=DIR]
  Dedups all calendar_*_*.json in <dir> in place. Idempotent: entries already
  carrying a ref (no text) keep their pool text; pool entries nothing
  references any more are dropped.
  --keep-from=DIR also copies into each pool every entry of DIR's
  texts_<locale>.json that the pool lacks. Use it on the app bundle with the
  deduped 2024-2099 archive as DIR: downloaded years resolve refs against the
  *bundled* pool, so it must be a superset of the archive's (the archive has a
  few pericopes that never fall inside the bundled window).
"""
import sys, os, json, hashlib, glob, re

def h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def main(directory: str, keep_from: str | None = None) -> None:
    by_locale: dict[str, list[str]] = {}
    for f in sorted(glob.glob(os.path.join(directory, "calendar_*_*.json"))):
        m = re.match(r"calendar_(.+)_(\d{4})\.json$", os.path.basename(f))
        if m:
            by_locale.setdefault(m.group(1), []).append(f)

    for locale, files in by_locale.items():
        pool: dict[str, str] = {}
        # Entries that already carry a ref (a re-run on a deduped dir) keep
        # their text from the existing pool; unreferenced stale entries drop.
        existing_path = os.path.join(directory, f"texts_{locale}.json")
        existing: dict[str, str] = json.load(open(existing_path, encoding="utf-8")) if os.path.exists(existing_path) else {}
        before = after = 0
        for path in files:
            before += os.path.getsize(path)
            data = json.load(open(path, encoding="utf-8"))
            days = data["days"]
            for day in (days.values() if isinstance(days, dict) else days):
                for b in (day.get("saintBios") or []):
                    if t := b.get("text"):
                        k = h(t); pool[k] = t; b.pop("text", None); b["ref"] = k
                    elif (k := b.get("ref")) in existing:
                        pool[k] = existing[k]
                for r in (day.get("readings") or []):
                    if t := r.get("text"):
                        k = h(t); pool[k] = t; r.pop("text", None); r["textRef"] = k
                    elif (k := r.get("textRef")) in existing:
                        pool[k] = existing[k]
                    if tw := r.get("textWeb"):
                        k = h(tw); pool[k] = tw; r.pop("textWeb", None); r["textWebRef"] = k
                    elif (k := r.get("textWebRef")) in existing:
                        pool[k] = existing[k]
            json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            after += os.path.getsize(path)
        kept = 0
        if keep_from:
            other = os.path.join(keep_from, f"texts_{locale}.json")
            if os.path.exists(other):
                for k, t in json.load(open(other, encoding="utf-8")).items():
                    if k not in pool:
                        pool[k] = t; kept += 1
        pool_path = os.path.join(directory, f"texts_{locale}.json")
        json.dump(pool, open(pool_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        psize = os.path.getsize(pool_path)
        print(f"{locale:6}: years {before/1e6:6.1f}->{after/1e6:5.1f}MB + pool {psize/1e6:5.1f}MB "
              f"({len(pool)} unique{f', {kept} kept from {keep_from}' if kept else ''})  "
              f"total {(after+psize)/1e6:.1f}MB (was {before/1e6:.1f})")

if __name__ == "__main__":
    dirs = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--keep-from=")), None)
    if len(dirs) != 1:
        print(__doc__); sys.exit(1)
    main(dirs[0], keep)
