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
import json, glob, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dedup_text import POOL_ALIAS

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLE = os.path.join(BASE, "OrthodoxCalendar", "Localization")
WORKER = os.path.join(BASE, "worker")
BUCKET = "orthodox-calendar-data"
LOCALES = ["sr", "ru", "en", "en_nc"]


def pool_path(directory, locale):
    """The texts pool a locale resolves against in `directory`.

    en_nc shares en's pool (dedup_text.POOL_ALIAS), but a release that shipped
    its own texts_en_nc.json still has one — hence the fallback rather than a
    plain alias, so --shipped-pools keeps working against older bundles.
    """
    path = os.path.join(directory, f"texts_{locale}.json")
    if os.path.exists(path) or locale not in POOL_ALIAS:
        return path
    return os.path.join(directory, f"texts_{POOL_ALIAS[locale]}.json")


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
        path = pool_path(pool_dir, locale)
        if not os.path.exists(path):
            # Without the pool the check proves nothing, and a silent pass here
            # is what lets an archive publish that no device can resolve.
            print(f"CLOSURE FAIL: {path} not found — pass the directory holding "
                  f"texts_{locale}.json (the app bundle for --dir, the release's "
                  f"pools for --shipped-pools)")
            return False
        bundled = set(json.load(open(path)))
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
        shipped_path = pool_path(shipped_dir, locale)
        current_path = pool_path(directory, locale)
        if not os.path.exists(current_path):
            continue  # nothing to inline for this locale
        if not os.path.exists(shipped_path):
            # The whole point of --shipped-pools is that installs already in the
            # store keep working; skipping a locale silently would publish refs
            # their bundled pool cannot resolve.
            sys.exit(f"--shipped-pools={shipped_dir} has no texts_{locale}.json — "
                     f"extract it from the release commit in the store "
                     f"(git show <tag>:OrthodoxCalendar/Localization/texts_{locale}.json)")
        shipped = set(json.load(open(shipped_path)))
        pool = json.load(open(current_path))
        for f in sorted(glob.glob(os.path.join(directory, f"calendar_{locale}_*.json"))):
            data = json.load(open(f, encoding="utf-8"))
            n = 0
            for day in data["days"].values():
                for b in (day.get("saintBios") or []):
                    ref = b.get("ref")
                    if ref and ref not in shipped:
                        # A ref missing from the fresh pool too would raise a bare
                        # KeyError halfway through rewriting the archive.
                        if ref not in pool:
                            sys.exit(f"{os.path.basename(f)}: ref {ref} is in neither "
                                     f"the shipped pool nor {os.path.basename(current_path)} "
                                     f"— regenerate the archive and pools together")
                        b["text"] = pool[ref]
                        del b["ref"]
                        n += 1
                for r in (day.get("readings") or []):
                    for ref_key, text_key in (("textRef", "text"), ("textWebRef", "textWeb")):
                        ref = r.get(ref_key)
                        if ref and ref not in shipped:
                            if ref not in pool:
                                sys.exit(f"{os.path.basename(f)}: {ref_key} {ref} is in "
                                         f"neither the shipped pool nor "
                                         f"{os.path.basename(current_path)} — regenerate "
                                         f"the archive and pools together")
                            r[text_key] = pool[ref]
                            del r[ref_key]
                            n += 1
            if n:
                json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
                print(f"inlined {n} texts missing from shipped pool into {os.path.basename(f)} "
                      f"({os.path.getsize(f) / 1e6:.1f} MB)")


def put(local_path, key, dry, attempts=4):
    # wrangler runs in worker/, so the file has to be named absolutely — a
    # relative <deduped_dir> would otherwise fail every upload with "does not
    # exist" after the closure check has already passed.
    cmd = ["npx", "wrangler", "r2", "object", "put", f"{BUCKET}/{key}",
           "--file", os.path.abspath(local_path), "--content-type", "application/json", "--remote"]
    if dry:
        print("DRY:", key)
        return key, True
    # A few objects per 300 fail with a bare "fetch failed" when several uploads
    # run at once. Retrying costs seconds; a partial publish costs a hunt through
    # the log for which years never landed.
    for attempt in range(attempts):
        r = subprocess.run(cmd, cwd=WORKER, capture_output=True, text=True)
        if r.returncode == 0:
            if attempt:
                print(f"  {key}: succeeded on attempt {attempt + 1}")
            return key, True
        if attempt < attempts - 1:
            time.sleep(2 ** attempt)
    print(f"FAILED {key}: {r.stderr.strip().splitlines()[-1] if r.stderr else '?'}")
    return key, False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    directory = sys.argv[1]
    dry = "--dry-run" in sys.argv
    with_config = "--config" in sys.argv
    shipped_dir = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--shipped-pools=")), None)

    files = sorted(glob.glob(os.path.join(directory, "calendar_*_*.json")))
    pools = sorted({pool_path(directory, loc) for loc in LOCALES})
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

    print(f"uploading {len(jobs)} objects to {BUCKET}...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda j: put(j[0], j[1], dry), jobs))
    failed = [k for k, ok in results if not ok]
    if failed:
        sys.exit(f"{len(failed)} uploads failed: {failed[:5]}")

    # config.json carries dataRevision, which makes every device drop its
    # download cache. Uploading it alongside the data meant a half-published
    # archive (some years still the old objects) with the cache already gone,
    # so it goes last, only once the archive itself is complete.
    if with_config:
        key, ok = put(os.path.join(WORKER, "config.json"), "config.json", dry)
        if not ok:
            sys.exit(f"data uploaded but config.json failed — retry --config, "
                     f"devices are still on the previous revision")
    print(f"done: {len(results)} objects uploaded" + (" + config" if with_config else ""))


if __name__ == "__main__":
    main()
