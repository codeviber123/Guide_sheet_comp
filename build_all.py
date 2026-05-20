#!/usr/bin/env python3
"""
Build all guidesheets for all patterns × languages.

Usage:
    python build_all.py                    # all patterns, all languages
    python build_all.py --lang en          # all patterns, English only
    python build_all.py --pattern ME2154   # one pattern, all languages
"""
import sys, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from build import build

ROOT = Path(__file__).parent.parent
PATTERNS_DIR = ROOT / "patterns"
LANGS = ["en", "es", "fr", "de"]


def discover_jobs(pattern_filter=None, lang_filter=None):
    for pattern_dir in sorted(PATTERNS_DIR.iterdir()):
        if not pattern_dir.is_dir():
            continue
        pattern_number = pattern_dir.name
        if pattern_filter and pattern_number != pattern_filter:
            continue
        for lang in LANGS:
            if lang_filter and lang != lang_filter:
                continue
            if (pattern_dir / f"data.{lang}.yaml").exists():
                yield (pattern_number, lang)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", help="single pattern number, e.g. ME2154")
    ap.add_argument("--lang", help="single language, e.g. en")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    jobs = list(discover_jobs(args.pattern, args.lang))
    print(f"Building {len(jobs)} guidesheet(s) with {args.workers} workers...\n")

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(build, p, l): (p, l) for p, l in jobs}
        for f in as_completed(futures):
            p, l = futures[f]
            try:
                f.result()
            except Exception as e:
                failures.append((p, l, str(e)))
                print(f"  ✗ {p} ({l}): {e}")

    print(f"\nDone. {len(jobs) - len(failures)}/{len(jobs)} succeeded.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
