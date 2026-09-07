#!/usr/bin/env python3
"""Upload the deduplicated calendar archive to R2 under the v2/ prefix.

Usage:
    upload_r2_v2.py <deduped_dir> [--shipped-pools=DIR] [--config] [--dry-run]

<deduped_dir> holds calendar_{locale}_{year}.json files already run through
dedup_text.py, plus the texts_{locale}.json pools. Before uploading, every
text ref in every year file is checked against the pools bundled in
OrthodoxCalendar/Localization/ — the app resolves refs against its *bundled*
pool, so a ref missing there would render as empty text on device. A closure
failure aborts the upload; fix it by adding the missing texts to the bundled
pool (ship in the next release) or re-inlining them in the affected files.

--shipped-pools=DIR does that re-inlining automatically for installs that
predate a pool change: DIR holds the texts_{locale}.json pools the *currently
shipped* app carries (e.g. `git show <release-tag>:OrthodoxCalendar/
Localization/texts_sr.json`). Any ref those pools lack is replaced in the
year files by the full text from <deduped_dir>'s pools, so old and new
installs both render it; closure is then also checked against DIR.

--config also uploads worker/config.json (minVersion gate + dataRevision).
Legacy fat objects at the unprefixed keys are never touched.
"""
import json, glob, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLE = os.path.join(BASE, "OrthodoxCalendar", "Localization")
WORKER = os.path.join(BASE, "worker")
BUCKET = "orthodox-calendar-data"
LOCALES = ["sr", "ru", "en", "en_nc"]


def refs_in_file(path):
    days = json.load(open(path))["days"]
    out = set()
    for day in days.values():
        for b in (day.get("saintBios") or []):
            if b.get("ref"):
                out.add(b["ref"])
        for r in (day.get("readings") or []):
            for k in ("textRef", "textWebRef"):
                if r.get(k):
                    out.add(r[k])
    return out


def check_closure(directory, pool_dir=BUNDLE, label="bundled"):
    ok = True
    for locale in LOCALES:
        pool_path = os.path.join(pool_dir, f"texts_{locale}.json")
        bundled = set(json.load(open(pool_path)))
        for f in sorted(glob.glob(os.path.join(directory, f"calendar_{locale}_*.json"))):
            missing = refs_in_file(f) - bundled
            if missing:
                ok = False
                print(f"CLOSURE FAIL {os.path.basename(f)}: {len(missing)} refs "
                      f"missing from {label} texts_{locale}.json: {sorted(missing)[:5]}")
    return ok


def inline_missing(directory, shipped_dir):
    """Replace refs absent from the shipped pools with the full text, in place."""
    for locale in LOCALES:
        shipped_path = os.path.join(shipped_dir, f"texts_{locale}.json")
        pool_path = os.path.join(directory, f"texts_{locale}.json")
        if not os.path.exists(shipped_path) or not os.path.exists(pool_path):
            continue
        shipped = set(json.load(open(shipped_path)))
        pool = json.load(open(pool_path))
        for f in sorted(glob.glob(os.path.join(directory, f"calendar_{locale}_*.json"))):
            data = json.load(open(f, encoding="utf-8"))
            n = 0
            for day in data["days"].values():
                for b in (day.get("saintBios") or []):
                    ref = b.get("ref")
                    if ref and ref not in shipped:
                        b["text"] = pool[ref]
                        del b["ref"]
                        n += 1
                for r in (day.get("readings") or []):
                    for ref_key, text_key in (("textRef", "text"), ("textWebRef", "textWeb")):
                        ref = r.get(ref_key)
                        if ref and ref not in shipped:
                            r[text_key] = pool[ref]
                            del r[ref_key]
                            n += 1
            if n:
                json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
                print(f"inlined {n} texts missing from shipped pool into {os.path.basename(f)} "
                      f"({os.path.getsize(f) / 1e6:.1f} MB)")


def put(local_path, key, dry):
    cmd = ["npx", "wrangler", "r2", "object", "put", f"{BUCKET}/{key}",
           "--file", local_path, "--content-type", "application/json", "--remote"]
    if dry:
        print("DRY:", key)
        return key, True
    r = subprocess.run(cmd, cwd=WORKER, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAILED {key}: {r.stderr.strip().splitlines()[-1] if r.stderr else '?'}")
    return key, r.returncode == 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    directory = sys.argv[1]
    dry = "--dry-run" in sys.argv
    with_config = "--config" in sys.argv
    shipped_dir = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--shipped-pools=")), None)

    files = sorted(glob.glob(os.path.join(directory, "calendar_*_*.json")))
    pools = [os.path.join(directory, f"texts_{loc}.json") for loc in LOCALES]
    pools = [p for p in pools if os.path.exists(p)]
    if not files:
        sys.exit(f"no calendar_*.json in {directory}")

    if shipped_dir:
        inline_missing(directory, shipped_dir)

    print(f"checking pool closure for {len(files)} files against bundled pools...")
    if not check_closure(directory):
        sys.exit("aborting: closure check failed")
    if shipped_dir and not check_closure(directory, shipped_dir, "shipped"):
        sys.exit("aborting: closure check against shipped pools failed")
    print("closure OK")

    jobs = [(f, "v2/" + os.path.basename(f)) for f in files]
    jobs += [(p, "v2/" + os.path.basename(p)) for p in pools]
    if with_config:
        jobs.append((os.path.join(WORKER, "config.json"), "config.json"))

    print(f"uploading {len(jobs)} objects to {BUCKET}...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda j: put(j[0], j[1], dry), jobs))
    failed = [k for k, ok in results if not ok]
    if failed:
        sys.exit(f"{len(failed)} uploads failed: {failed[:5]}")
    print(f"done: {len(results)} objects uploaded")


if __name__ == "__main__":
    main()
