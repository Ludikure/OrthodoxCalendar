#!/usr/bin/env python3
"""
Deduplicate saint-bio text across bundled calendar year files.

The same saint biographies repeat across years (a fixed-date saint appears
every year), and for Russian the bio text dominates file size. This extracts
each unique bio `text` into a per-locale pool `bios_<locale>.json` keyed by a
content hash, and rewrites every day's bios from `{title, text}` to
`{title, ref}`. Apps resolve `ref` -> pool text at load.

Only meant for the BUNDLED files (the app ships the pool alongside them).
The API keeps serving the full embedded format, so older app versions and the
streaming path are unaffected.

Usage:
    dedup_bios.py <dir>           # dedup all calendar_*_*.json in <dir> in place
Idempotent: bios already carrying `ref` (no `text`) are left untouched.
"""
import sys, os, json, hashlib, glob, re

def bio_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def main(directory: str) -> None:
    files = sorted(glob.glob(os.path.join(directory, "calendar_*_*.json")))
    # group by locale: calendar_<locale>_<year>.json
    by_locale: dict[str, list[str]] = {}
    for f in files:
        m = re.match(r"calendar_(.+)_(\d{4})\.json$", os.path.basename(f))
        if not m:
            continue
        by_locale.setdefault(m.group(1), []).append(f)

    for locale, locale_files in by_locale.items():
        pool: dict[str, str] = {}
        before = after = 0
        for path in locale_files:
            before += os.path.getsize(path)
            data = json.load(open(path, encoding="utf-8"))
            days = data["days"]
            day_iter = days.values() if isinstance(days, dict) else days
            for day in day_iter:
                bios = day.get("saintBios")
                if not bios:
                    continue
                for b in bios:
                    text = b.get("text")
                    if not text:          # already deduped (ref-only) — skip
                        continue
                    h = bio_hash(text)
                    pool[h] = text
                    b.pop("text", None)
                    b["ref"] = h
            json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            after += os.path.getsize(path)
        pool_path = os.path.join(directory, f"bios_{locale}.json")
        json.dump(pool, open(pool_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        pool_size = os.path.getsize(pool_path)
        print(f"{locale}: years {before/1e6:.1f}MB -> {after/1e6:.1f}MB + pool {pool_size/1e6:.1f}MB "
              f"({len(pool)} unique bios)  net {(before-after-pool_size)/1e6:+.1f}MB")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1])
