# Guide# Simplicity Guidesheet Pipeline

Automated production of sewing pattern guidesheets from structured data files, across all our brands (Simplicity, McCall's, Vogue, Butterick, KnowMe, New Look, burda style).

## What it does

Each pattern lives in `patterns/<NUMBER>/` as a YAML data file plus an `assets/` folder of illustrations. The data declares which brand the pattern belongs to. One shared template renders every pattern — the brand only swaps the logo wordmark at the top of the left column.

```
patterns/ME2154/data.en.yaml  +  templates/guidesheet.html.j2  →  dist/ME2154_en/guidesheet.pdf
```

## First time setup

```
cd ~/Documents/simplicity-guidesheets
python3.12 -m venv venv
source venv/bin/activate
pip install jinja2 pyyaml playwright python-docx
playwright install chromium
```

## Every time you open a new terminal

```
cd ~/Documents/simplicity-guidesheets
source venv/bin/activate
```

## Building a guidesheet

```
python build_scripts/build.py ME2154 en
```

Produces `dist/ME2154_en/guidesheet.html` (open in browser to preview) and `dist/ME2154_en/ME2154_gs_en.pdf` (print-ready output).

## Building everything

```
python build_scripts/build_all.py --lang en      # all patterns, English only
python build_scripts/build_all.py                # all patterns × all languages
```

## Folder layout

```
simplicity-guidesheets/
├── patterns/                    ← one folder per pattern
│   ├── ME2154/                  ← KnowMe Donny Q cargo pants (production)
│   │   ├── data.en.yaml
│   │   └── assets/
│   └── M0000/                   ← McCall's Dress C (pipeline test stub)
│       ├── data.en.yaml
│       └── assets/              ← placeholder SVGs, swap for real artwork
├── templates/
│   ├── guidesheet.html.j2       ← main template — page 1 + page 2
│   ├── _sewing_info.html.j2     ← Sewing Info + Glossary + QR partial
│   ├── styles.css               ← all styling, Arial body, brand themes at bottom
│   └── brands/
│       ├── knowme/masthead.html.j2
│       └── mccalls/masthead.html.j2
├── build_scripts/
│   ├── build.py                 ← single-pattern build
│   └── build_all.py             ← batch build
├── dist/                        ← rendered output (gitignored)
└── venv/                        ← Python environment (gitignored)
```

## Layout

Every guidesheet uses the McCall's-derived 2-page layout:

**Page 1**
- Left column: brand logo, style number, FBV illustration, piece-thumbnail grid, piece list
- Right side, top: three columns of standing general instructions (Adjust If Necessary, Cutting And Marking, Pattern Markings) — same content on every guide
- Right side, bottom: cutting layouts in a 2- or 3-column grid (auto-switches on layout count)

**Page 2**
- Left sidebar: Sewing Information block (Fabric Key, Seam Allowances, Pin and Fit, Press), Glossary, Sewing Tutorials QR. Each block has `break-inside: avoid` so glossary and key can't split.
- Main area: sewing directions, 3-column auto-flow with subsections kept together.

Optional: setting `pattern.layout.sewing_info_on_page1: true` in YAML pulls the Sewing Info block up to the bottom-right of page 1, and gives the page-2 sewing directions the full width. Use this for patterns with few cutting layouts that leave room on page 1.

## Brand system

The `brand` field in YAML drives the logo:

```yaml
pattern:
  number: ME2154
  brand: knowme        # matches templates/brands/knowme/masthead.html.j2
  audience: men's
```

The body gets `class="brand-{id}"`, and the template includes `templates/brands/{id}/masthead.html.j2` at the top of the left column.

### Adding a brand

1. Create `templates/brands/<brand>/masthead.html.j2` with the logo. For now, the wordmark is plain text; when you have a vector logo, replace with an `<img>` referencing `brands/<brand>/logo.svg`.
2. In any pattern's YAML, set `pattern.brand: <brand>` and rebuild.

## Converting Illustrator (.ai) files to SVG

For patterns where the step illustrations and cutting layouts live as `.ai` files, the `convert_ai.py` script batches them to clean SVG. `.ai` files from modern Illustrator are PDF underneath, so `pdftocairo` handles them natively while keeping vector quality.

```
python build_scripts/convert_ai.py ~/Downloads/M8445_source M8445
```

By default the script writes into `patterns/M8445/assets/`. Pass `--dest` to override, `--dry-run` to preview the mapping, or `--force` to overwrite existing files.

Naming convention (auto-detected):

| Source filename       | Becomes                |
|-----------------------|------------------------|
| `M8445_1.ai`          | `step-1.svg`           |
| `M8445_16a.ai`        | `step-16a.svg`         |
| `M8445_0A.ai`         | `cl-A.svg`             |
| `M8445CC.ai`          | `M8445CC.svg`          |
| anything else         | (extension swapped)    |

Then reference the converted files from YAML:

```yaml
- { num: 1, illustration: "step-1.svg", text: "Fuse INTERFACING..." }
```

`illustration: true` still works as a generic placeholder when there's no real artwork yet.

## Adding a new pattern

1. Copy an existing pattern folder (e.g. `patterns/ME2154/`) to `patterns/<NEW_NUMBER>/`.
2. Edit `data.en.yaml`: change pattern number, set `pattern.brand`, `pattern.audience`, then fill in name, pieces, cutting layouts, sewing steps.
3. Replace the contents of `assets/` with the new pattern's illustrations.
4. Run `python build_scripts/build.py <NEW_NUMBER> en`.

## Known limitations & roadmap

- **Sewing-directions overflow**: Page 2's main area is a fixed 3-column flow. Patterns with very dense sewing directions (40+ steps with long copy) can overflow off the bottom edge. Auto-pagination across pages 3–8 with subsection-level break logic is the next step.
- **Brand logos are styled text**: The two existing masthead partials render the brand name as Arial text. Swap each to an `<img>` when vector assets are ready.
- **Only knowme and mccalls brands are set up**: Simplicity, Butterick, Vogue, New Look, burda style each need their own masthead partial.
- **English only**: The build script accepts a lang argument, but only `data.en.yaml` files exist so far.

## Troubleshooting

- **Output looks wrong**: Open the generated HTML in a browser. CSS issues are easier to debug there than in the PDF.
- **PDF render fails**: Confirm Chromium is installed (`playwright install chromium`).
- **Missing modules**: Activate the venv first (`source venv/bin/activate`).
_sheet_comp
