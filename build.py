#!/usr/bin/env python3
"""
Build a single guidesheet from its YAML data file + Jinja2 template.

Usage:
    python build.py ME2154 en
    python build.py ME2154 es

Outputs HTML and PDF to dist/<PATTERN>_<LANG>/.
"""
import sys
import re
import math
import yaml
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent.parent
PATTERNS_DIR = ROOT / "patterns"
TEMPLATES_DIR = ROOT / "templates"
FONTS_DIR = ROOT / "fonts"
DIST_DIR = ROOT / "dist"

# Layout tuning — content-height estimates for paginating sewing directions.
# Values are in px-equivalent units at PDF render scale. Tweak if pages
# come out over- or under-filled in practice.
COLUMN_CAPACITY_PX = 1200     # usable vertical height per column on a sewing page
CHARS_PER_LINE     = 55       # rough wrap width in a sewing-direction column
LINE_HEIGHT_PX     = 14
STEP_MARGIN_PX     = 6
ILLUSTRATION_PX    = 95
SECTION_HEADER_PX  = 50       # header + column-break overhead from break-inside: avoid


def load_data(pattern_number, lang):
    data_path = PATTERNS_DIR / pattern_number / f"data.{lang}.yaml"
    if not data_path.exists():
        raise FileNotFoundError(f"No data file at {data_path}")
    with data_path.open() as f:
        return yaml.safe_load(f)


def _strip_html(text):
    return re.sub(r'<[^>]+>', '', text or '')


def _estimate_step_px(step):
    plain = _strip_html(step.get('text', ''))
    keyword = step.get('keyword') or ''
    char_count = len(plain) + len(keyword) + 4   # "N. " prefix
    lines = max(1, math.ceil(char_count / CHARS_PER_LINE))
    h = lines * LINE_HEIGHT_PX + STEP_MARGIN_PX
    if step.get('illustration'):
        h += ILLUSTRATION_PX
    return h


def _estimate_subsection_px(subsection):
    return SECTION_HEADER_PX + sum(_estimate_step_px(s) for s in subsection.get('steps', []))


def _decide_si_on_page1(data):
    """Sewing Info rides on page 1 when there's room — i.e. few cutting layouts.
       Override per-pattern with `pattern.layout.sewing_info_on_page1: true|false`."""
    layout_cfg = (data.get('pattern') or {}).get('layout') or {}
    if 'sewing_info_on_page1' in layout_cfg:
        return bool(layout_cfg['sewing_info_on_page1'])
    return len(data.get('cutting_layouts') or []) <= 4


def paginate_sewing(subsections, first_page_capacity_px, other_page_capacity_px, max_pages=7):
    """Distribute subsections across sewing pages without splitting subsections.
       Returns a list of lists. Caps at max_pages (sewing pages only — page 1 is the cover)."""
    pages = []
    current = []
    current_h = 0
    capacity = first_page_capacity_px

    for sub in subsections:
        sub_h = _estimate_subsection_px(sub)
        if current and current_h + sub_h > capacity:
            pages.append(current)
            if len(pages) >= max_pages:
                # Out of pages — dump everything remaining onto the last one and stop
                pages[-1].extend([sub])
                current = []
                current_h = 0
                continue
            current = [sub]
            current_h = sub_h
            capacity = other_page_capacity_px
        else:
            current.append(sub)
            current_h += sub_h
    if current:
        pages.append(current)

    return pages or [[]]


def prepare_layout(data):
    """Compute layout decisions once in Python and attach to data dict.
       Template reads `_layout.*` instead of recomputing."""
    si_on_page1 = _decide_si_on_page1(data)

    # All sewing pages use 4 columns now. When the SI sidebar lives on the
    # first sewing page, it sits inside the column flow as the first item,
    # consuming roughly ~10in of vertical space in column 1.
    sidebar_consumed = 0 if si_on_page1 else int(8.5 * 96)   # ~8.5in in px-equiv
    first_cap = 4 * COLUMN_CAPACITY_PX - sidebar_consumed
    other_cap = 4 * COLUMN_CAPACITY_PX

    subsections = (data.get('sewing_directions') or {}).get('subsections', [])
    sewing_pages = paginate_sewing(subsections, first_cap, other_cap)

    data['_layout'] = {
        'si_on_page1':   si_on_page1,
        'first_page_cols': 4,
        'sewing_pages':  sewing_pages,
        'total_pages':   1 + len(sewing_pages),
    }
    return data


def render_html(pattern_number, lang, data):
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(['html']),
        trim_blocks=True, lstrip_blocks=True,
    )
    template = env.get_template("guidesheet.html.j2")
    return template.render(**data, _meta={"pattern_number": pattern_number, "lang": lang})


def copy_assets(pattern_number, brand, output_dir):
    # pattern's own illustrations
    src_assets = PATTERNS_DIR / pattern_number / "assets"
    if src_assets.exists():
        shutil.copytree(src_assets, output_dir / "assets", dirs_exist_ok=True)
    # brand logo + any other brand image assets (excluding .j2 partials)
    brand_src = TEMPLATES_DIR / "brands" / brand
    if brand_src.exists():
        brand_dst = output_dir / "brands" / brand
        brand_dst.mkdir(parents=True, exist_ok=True)
        for f in brand_src.iterdir():
            if f.is_file() and not f.name.endswith('.j2'):
                shutil.copy2(f, brand_dst / f.name)


def render_to_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path.absolute()}", wait_until="networkidle")
        page.wait_for_function("document.fonts.ready")
        page.pdf(
            path=str(pdf_path),
            width="18in", height="13.75in",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()


def build(pattern_number, lang):
    print(f"Building {pattern_number} ({lang})...")
    data = load_data(pattern_number, lang)
    data = prepare_layout(data)
    html = render_html(pattern_number, lang, data)

    output_dir = DIST_DIR / f"{pattern_number}_{lang}"
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_assets(pattern_number, data['pattern']['brand'], output_dir)

    html_path = output_dir / "guidesheet.html"
    html_path.write_text(html)
    print(f"  HTML → {html_path}")

    pdf_path = output_dir / f"{pattern_number}_gs_{lang}.pdf"
    try:
        render_to_pdf(html_path, pdf_path)
        print(f"  PDF  → {pdf_path}")
    except Exception as e:
        print(f"  PDF render failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python build.py <PATTERN_NUMBER> <LANG>")
        print("Example: python build.py ME2154 en")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
