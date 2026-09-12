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

en and en_nc show the same bios and the same scripture text, so they share a
single `texts_en.json`; a separate texts_en_nc.json was a byte-for-byte copy.

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

POOL_ALIAS = {"en_nc": "en"}   # locales that share another locale's pool

def pool_name(locale: str) -> str:
    return POOL_ALIAS.get(locale, locale)

def h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def main(directory: str, keep_from: str | None = None) -> None:
    by_pool: dict[str, list[str]] = {}
    for f in sorted(glob.glob(os.path.join(directory, "calendar_*_*.json"))):
        m = re.match(r"calendar_(.+)_(\d{4})\.json$", os.path.basename(f))
        if m:
            by_pool.setdefault(pool_name(m.group(1)), []).append(f)

    for locale, files in by_pool.items():
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
        # Sorted, so a pool's bytes depend only on its texts. Refs are content
        # hashes, but the pool used to be written in first-appearance order: a
        # regeneration that moved a bio to another day reordered the whole file
        # and a byte comparison could not tell that from a real change.
        json.dump(dict(sorted(pool.items())), open(pool_path, "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        psize = os.path.getsize(pool_path)
        print(f"{locale:6}: years {before/1e6:6.1f}->{after/1e6:5.1f}MB + pool {psize/1e6:5.1f}MB "
              f"({len(pool)} unique{f', {kept} kept from {keep_from}' if kept else ''})  "
              f"total {(after+psize)/1e6:.1f}MB (was {before/1e6:.1f})")

        # Verify what landed on disk: every ref in a year file must resolve
        # against the pool written next to it. A dangling ref is an empty
        # biography on device with no signal in release builds (the app prints
        # only under DEBUG), and it used to survive silently — a ref whose text
        # the pool lost is copied forward untouched. upload_r2_v2 checks the same
        # thing before publishing; checking here catches it when it is created.
        dangling = []
        for path in files:
            data = json.load(open(path, encoding="utf-8"))
            days = data["days"]
            for key, day in (days.items() if isinstance(days, dict) else enumerate(days)):
                refs = {b["ref"] for b in (day.get("saintBios") or []) if b.get("ref")}
                refs |= {r[k] for r in (day.get("readings") or [])
                         for k in ("textRef", "textWebRef") if r.get(k)}
                missing = sorted(refs - set(pool))
                if not missing:
                    continue
                dangling.append((os.path.basename(path), key, missing))
        if dangling:
            # Count refs, not days: one day can dangle several (bio + textRef +
            # textWebRef), and only the first three of each day are shown.
            n_refs = sum(len(row[2]) for row in dangling)
            for row in dangling[:5]:
                print(f"  DANGLING {row[0]} day {row[1]}: {row[2][:3]}")
            sys.exit(f"dedup produced {n_refs} dangling refs in "
                     f"{len(dangling)} day entr{'y' if len(dangling) == 1 else 'ies'} "
                     f"for {locale}: the pool does not contain text the year files "
                     f"point at")

if __name__ == "__main__":
    dirs = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--keep-from=")), None)
    if len(dirs) != 1:
        print(__doc__); sys.exit(1)
    main(dirs[0], keep)
