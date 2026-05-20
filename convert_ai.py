#!/usr/bin/env python3
"""
Convert pattern source artwork (.ai, .eps, .pdf) to clean SVG.

.ai files are PDF underneath, and .eps + .pdf go through pdftocairo cleanly,
so a single converter handles all three with vector fidelity intact.

Usage:
    python convert_ai.py <source_dir> <pattern_number> [--dest <dir>] [--force] [--dry-run]

    # Example: convert every M8445* source file into patterns/M8445/assets/
    python convert_ai.py ~/Downloads/M8445 M8445

Naming conventions auto-detected for design number M8445:

    M8445_<N>.ai           →  step-<N>.svg          (step illustration)
    M8445_<N><a-z>.ai      →  step-<N><suffix>.svg  (variant — e.g. 16a, 16b)
    M8445CC.{eps,ai,pdf}   →  M8445CC.svg           (front/back view)
    M8445G_pl.pdf          →  pieces-icons.svg      (piece-list overview image)
    M844<NN>.pdf           →  cl-<NN>.svg           (cutting layout — McCall's convention:
                                                     last char of design number dropped,
                                                     followed by two-digit layout number)
    anything else          →  <basename>.svg        (preserved name, .svg extension)

The script never overwrites existing files unless --force is given.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_target_name(filename, pattern_number):
    """Map source filename to the asset filename it should become."""
    name = Path(filename).name
    stem = Path(filename).stem

    p_full = pattern_number              # e.g. "M8445"
    p_trunc = pattern_number[:-1]        # e.g. "M844" — McCall's cutting-layout convention

    # %design%G_pl.pdf  →  pieces-icons.svg  (piece list overview)
    if re.fullmatch(rf'{re.escape(p_full)}G_pl', stem, re.IGNORECASE):
        return "pieces-icons.svg"

    # %design%CC  →  <design>CC.svg  (front/back view)
    if re.fullmatch(rf'{re.escape(p_full)}CC', stem, re.IGNORECASE):
        return f"{p_full}CC.svg"

    # %design[:-1]%<NN>  →  cl-<NN>.svg  (cutting layout — design with last char dropped + 2 digits)
    m = re.fullmatch(rf'{re.escape(p_trunc)}(\d{{2}})', stem, re.IGNORECASE)
    if m:
        return f"cl-{m.group(1)}.svg"

    # %design%_<N>[<letter>]  →  step-<N>[<letter>].svg
    m = re.fullmatch(rf'{re.escape(p_full)}_?(\d+)([a-z]?)', stem, re.IGNORECASE)
    if m:
        return f"step-{m.group(1)}{m.group(2)}.svg"

    # Anything else: keep base, swap extension
    return f"{stem}.svg"


def convert_one(src, dst):
    """Convert a single source (.ai/.eps/.pdf) to SVG via pdftocairo."""
    result = subprocess.run(
        ['pdftocairo', '-svg', str(src), str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ✗ {src.name}: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument('source_dir', type=Path, help="folder containing source artwork")
    p.add_argument('pattern_number', help="pattern number (e.g. M8445)")
    p.add_argument('--dest', type=Path, default=None,
                   help="destination folder (default: patterns/<NUM>/assets in this repo)")
    p.add_argument('--force', action='store_true', help="overwrite existing files")
    p.add_argument('--dry-run', action='store_true', help="show planned conversions, write nothing")
    args = p.parse_args()

    if not args.source_dir.is_dir():
        sys.exit(f"source_dir not found: {args.source_dir}")

    if args.dest is None:
        repo_root = Path(__file__).resolve().parent.parent
        args.dest = repo_root / "patterns" / args.pattern_number / "assets"
    args.dest.mkdir(parents=True, exist_ok=True)

    # Gather every convertible file
    extensions = ('.ai', '.eps', '.pdf')
    sources = sorted(
        f for f in args.source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    )
    if not sources:
        sys.exit(f"no .ai/.eps/.pdf files in {args.source_dir}")

    print(f"Converting {len(sources)} files from {args.source_dir} → {args.dest}")
    ok = skipped = failed = 0
    for src in sources:
        target = parse_target_name(src.name, args.pattern_number)
        dst = args.dest / target

        if dst.exists() and not args.force:
            print(f"  · {src.name} → {target} (exists, skip — use --force to overwrite)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  → {src.name} → {target}")
            continue

        if convert_one(src, dst):
            print(f"  ✓ {src.name} → {target}")
            ok += 1
        else:
            failed += 1

    print(f"\nDone. {ok} converted, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()
