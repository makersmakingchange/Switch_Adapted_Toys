"""
generate_toy_data.py

Scans the Toy_Instructions folder and automatically builds the data used
by the "Toy Instructions" page (cards + filters).

Folder convention:

    Toy_Instructions/
        <Category Folder>/
            <Toy Folder>/
                <photo>.jpg / .png / .webp   (thumbnail - optional)
                toy_info.md                  (optional overrides, see below)
                ... any other files (assembly guides, 3D files, etc.)
                                              (ignored by this script)

toy_info.md now uses YAML frontmatter (a --- delimited block at the very
top of the file) rather than plain "Key: value" lines - see
Toy_Instructions/_TEMPLATE/toy_info.md for the full template with
comments. Example:

    ---
    last_updated: 2026-07-29
    tags: [Bubble, HFTH]
    activation_type:
      - Press and Hold
    requires_3d_printing: No
    adaptation_method:
      - Battery Interrupter
    number_of_switches:
      - 2
    hfth_collection_year: 2026
    available_to_purchase: Yes
    toy_purchase_link: https://example.com/product
    toy_purchase_link_alt:
    general_notes: Works best with a jelly bean switch.
    device_uid:
    name:
    category:
    link:
    battery_type: AA
    battery_required: 2
    battery_included: 2
    ---

    (any markdown body text below the closing --- is ignored by this
    script - it's just a place for human-readable notes if wanted)

Tags, Activation Type, Method of Adaptation, and Number of Switches can
all hold more than one value (as a YAML list) and each toy shows up
under every value it has. Tags drive the main filter chips; the other
three feed a secondary set of grouped filters (shown collapsed under
"Filters" so the page isn't overwhelming) - a filter chip only appears
for values that at least one toy actually has. Requires 3D Printing and
Available To Purchase are simple Yes/No toggles. HFTH Collection Year is
its own chip group too (not hardcoded to 2026 - any year works, and
years only show up as filter options once some toy actually has them).
All of these are optional per toy; leaving one blank just means that toy
won't show up under that particular filter, without affecting any other
filter.

Still reads the older, pre-frontmatter "Key: value" line format too
(including the very old "toy-info.txt" filename), for any folder that
hasn't been migrated yet - both formats can coexist across different
toys at once.

If toy_info.md is missing entirely, the script falls back to:
    Name     -> the toy folder name, with underscores/hyphens turned into spaces
    Category -> the name of the folder this toy sits directly inside
    Tags     -> [Category] (a single tag matching the category)
    Link     -> an auto-built link to that folder on GitHub
    Available, Description, Battery/Adaptation/template fields -> left blank/default

Also still reads the older, simpler "toy-info.txt" (richer format) or
"info.txt" (legacy Name/Link/Description only) filenames, in that order,
for anyone with folders set up before "toy_info.md" became the convention.

Run this BEFORE `mkdocs build` / `mkdocs gh-deploy` in the GitHub Action.

In addition to the toy-data.js used by the "Toy Instructions" grid, this
script also generates, per toy:
  - docs/toys/<slug>.md      a dedicated detail page (image, description,
                              battery/input info, download button)
  - docs/downloads/<slug>.zip  a zip of that toy's whole folder, so the
                              "Download Instructions" button on the detail
                              page doesn't depend on any third-party
                              zip-a-github-subfolder service.
Both are fully regenerated on every build, so nothing needs to be committed
by hand when a new toy folder is added.
"""

import json
import os
import re
import shutil
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG - adjust these if your repo layout changes
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent

# Toy_Instructions lives on the `main` branch, while this script and the
# website files live on the website branch. The GitHub Actions workflow
# checks out `main` into a separate folder (see workflow step) and passes
# its location in here via the TOY_INSTRUCTIONS_DIR environment variable.
# Falls back to a local Toy_Instructions/ folder for local testing.
TOY_INSTRUCTIONS_DIR = Path(
    os.environ.get("TOY_INSTRUCTIONS_DIR", REPO_ROOT / "Toy_Instructions")
)
DOCS_DIR = REPO_ROOT / "docs"
IMAGES_OUT_DIR = DOCS_DIR / "images" / "toys"
JS_OUT_PATH = DOCS_DIR / "js" / "toy-data.js"
TOY_PAGES_OUT_DIR = DOCS_DIR / "toys"          # one .md per toy, auto-generated
DOWNLOADS_OUT_DIR = DOCS_DIR / "downloads"      # one .zip per toy, auto-generated

GITHUB_ORG = "makersmakingchange"
GITHUB_REPO = "Switch_Adapted_Toys"
GITHUB_BRANCH = "main"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Folder names under Toy_Instructions that are NOT real toy categories,
# and should be skipped entirely (case-insensitive match).
IGNORED_FOLDERS = {
    "_template",
    "template",
}


def prettify(folder_name: str) -> str:
    """Turn 'Battery_Interrupter_Toys' into 'Battery Interrupter Toys'."""
    return folder_name.replace("_", " ").replace("-", " ").strip()


def slugify(text: str) -> str:
    """Turn 'Bubble Blower' into 'bubble-blower' (safe for filenames)."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# Lines matching any of these (case-insensitive, ignoring surrounding
# whitespace/punctuation) mark the start of the "overrides and extra info"
# section at the bottom of toy_info.md. Parsing stops there so unfilled
# placeholder text like "Name: (overrides the toy's display name...)"
# never gets read as real data. This is intentionally NOT just "any line
# starting with ---", since templates can have other dividers earlier in
# the file (e.g. separating intro copy from the actual fields) that must
# NOT stop parsing.
STOP_PARSING_MARKERS = [
    "overrides and extra info",
    "everything below this line is optional",
]


def parse_info_txt(info_path: Path | None) -> dict:
    """Reads a simple 'Key: value' formatted info.txt file (legacy format)."""
    data = {}
    if not info_path or not info_path.exists():
        return data
    for line in info_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        stripped_check = stripped.lower().rstrip(":").strip()
        if any(stripped_check.startswith(marker) for marker in STOP_PARSING_MARKERS):
            break
        if stripped.startswith("---") or stripped.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip().lower()] = value.strip()
    return data


def to_bool(value, default=True):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("true", "yes", "1")


def to_int(value):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def to_list(value):
    """Turns 'Bubble, HFTH 2026, Battery Powered' into ['Bubble', 'HFTH 2026', 'Battery Powered']."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)


def extract_frontmatter(text: str) -> dict | None:
    """
    If the file starts with a '---' delimited YAML block, parses and
    returns it as a dict. Returns None if there's no frontmatter block at
    all (meaning: the caller should try the legacy flat 'Key: value' line
    format instead). Returns {} (not None) if there IS a frontmatter
    block but it's empty or invalid YAML - that still counts as "this
    toy has an info file", just with no usable fields in it.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        print(f"WARNING: invalid YAML frontmatter in a toy_info.md file - {e}")
        return {}
    return data if isinstance(data, dict) else {}


def as_list(value) -> list[str]:
    """Normalizes a YAML value (None / scalar / list) into a clean list
    of non-empty strings, e.g. for toy_features, activation_type, etc."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip() != ""]
    s = str(value).strip()
    return [s] if s else []


def merge_lists(*lists) -> list[str]:
    """Combines several lists into one, de-duplicated, preserving order.
    Used to merge the current 'toy_features' field with the older 'tags'
    field name, so any toy already using 'tags' keeps working without
    needing to be manually migrated."""
    seen: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.append(item)
    return seen


def as_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def as_short_str(value, field_label: str, max_len: int = 80) -> str | None:
    """Like as_str, but rejects implausibly long values for fields that
    should always be short (a toy name, a category, a battery type).
    This exists specifically to catch YAML's line-folding behavior: an
    unquoted value left wrapped across multiple lines by mistake (rather
    than kept on one line, or quoted) gets silently folded into one very
    long string - this rejects that outright and prints a build-log
    warning, rather than letting garbled placeholder text quietly become
    a toy's real name/category/etc."""
    s = as_str(value)
    if s is None:
        return None
    if len(s) > max_len:
        print(
            f"WARNING: '{field_label}' value looks like corrupted/wrapped "
            f"text ({len(s)} chars, expected a short value) - ignoring it: "
            f"{s[:60]}..."
        )
        return None
    return s


def as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_from_yaml(raw: dict) -> dict:
    """Maps a parsed YAML frontmatter dict (clean snake_case keys, native
    types) to the single unified info schema used everywhere else in this
    script."""
    hfth_year = as_int(raw.get("hfth_collection_year"))
    return {
        "name": as_short_str(raw.get("name"), "name"),
        "available": to_bool(raw.get("available")),
        "last_update": as_str(raw.get("last_updated")),
        "category": as_short_str(raw.get("category"), "category"),
        "toy_features": merge_lists(as_list(raw.get("toy_features")), as_list(raw.get("tags"))),
        "link": as_str(raw.get("link")),
        "toy_purchase_link": clean_url(as_str(raw.get("toy_purchase_link"))),
        "toy_purchase_link_alt": clean_url(as_str(raw.get("toy_purchase_link_alt"))),
        "description": as_str(raw.get("description")),
        "battery_type": as_short_str(raw.get("battery_type"), "battery_type"),
        "battery_required": as_int(raw.get("battery_required")),
        "battery_included": as_int(raw.get("battery_included")),
        "adaptation_inputs": as_int(raw.get("adaptation_inputs")),
        "activation_type": as_list(raw.get("activation_type")),
        "requires_3d_printing": to_bool(raw.get("requires_3d_printing"), default=False),
        "adaptation_method": as_list(raw.get("adaptation_method")),
        "number_of_switches": as_list(raw.get("number_of_switches")),
        "hfth_collection_year": str(hfth_year) if hfth_year else None,
        "available_to_purchase": to_bool(raw.get("available_to_purchase"), default=False),
        "general_notes": as_str(raw.get("general_notes")),
        "device_uid": as_str(raw.get("device_uid")),
    }


def normalize_from_legacy(raw: dict) -> dict:
    """Maps the old flat 'Key: value' line format (fuzzy lowercase keys,
    all-string values, from parse_info_txt) to the same unified info
    schema normalize_from_yaml produces, for backwards compatibility with
    toy folders that haven't been migrated to frontmatter yet."""
    hfth_flag = to_bool(raw.get("hfth 2026") or raw.get("hfth_2026"), default=False)
    return {
        "name": as_short_str(raw.get("name"), "name"),
        "available": to_bool(raw.get("available")),
        "last_update": (
            raw.get("info last updated (mm/dd/yyyy)")
            or raw.get("info last updated (yyyy/mm/dd)")
            or raw.get("last updated")
            or raw.get("last update")
            or raw.get("last_update")
        ),
        "category": as_short_str(raw.get("category"), "category"),
        "toy_features": merge_lists(
            to_list(raw.get("toy features") or raw.get("toy_features")), to_list(raw.get("tags"))
        ),
        "link": raw.get("link"),
        "toy_purchase_link": clean_url(raw.get("toy purchase link") or raw.get("toy_purchase_link")),
        "toy_purchase_link_alt": clean_url(
            raw.get("toy purchase link (alternate)")
            or raw.get("toy purchase link alternate")
            or raw.get("toy_purchase_link_alt")
        ),
        "description": raw.get("description"),
        "battery_type": as_short_str(raw.get("battery type") or raw.get("battery_type"), "battery_type"),
        "battery_required": to_int(raw.get("battery required") or raw.get("battery_required")),
        "battery_included": to_int(raw.get("battery included") or raw.get("battery_included")),
        "adaptation_inputs": to_int(raw.get("adaptation inputs") or raw.get("adaptation_inputs")),
        "activation_type": as_list(raw.get("activation type") or raw.get("activation_type")),
        "requires_3d_printing": to_bool(raw.get("requires 3d printing") or raw.get("requires_3d_printing"), default=False),
        "adaptation_method": as_list(
            raw.get("method of adaption") or raw.get("method of adaptation") or raw.get("adaptation_method")
        ),
        "number_of_switches": as_list(raw.get("number of switches") or raw.get("number_of_switches")),
        # The old template hardcoded the year into the field name itself
        # ("HFTH 2026: Yes/No"), so a truthy legacy flag always means 2026.
        "hfth_collection_year": "2026" if hfth_flag else None,
        "available_to_purchase": to_bool(
            raw.get("available to purchase as of last update") or raw.get("available_to_purchase"), default=False
        ),
        "general_notes": raw.get("general notes") or raw.get("general_notes"),
        "device_uid": raw.get("device uid") or raw.get("device_uid"),
    }


def parse_toy_info(info_path: Path | None) -> dict:
    """
    Reads a toy's info file - either the current YAML-frontmatter
    toy_info.md format, or the older flat 'Key: value' line format - and
    returns a dict in one unified schema regardless of which format was
    used. Returns {} if the file doesn't exist.
    """
    if not info_path or not info_path.exists():
        return {}

    text = info_path.read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(text)
    if frontmatter is not None:
        return normalize_from_yaml(frontmatter)

    raw = parse_info_txt(info_path)
    if not raw:
        return {}
    return normalize_from_legacy(raw)


def find_thumbnail(toy_dir: Path) -> Path | None:
    """Finds the first image file in a toy folder, alphabetically."""
    images = sorted(
        [f for f in toy_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    )
    return images[0] if images else None


def clean_url(value: str | None) -> str | None:
    """Only accept a value that actually looks like a URL. Guards against
    two common real-world cases: an unfilled placeholder left as-is (e.g.
    '(adds a button if filled in...)'), and a real URL that still has the
    template's trailing instructional text stuck on the same line (e.g.
    'https://example.com (adds a button...)') - in that second case, only
    the URL itself is kept and the rest is discarded."""
    if not value:
        return None
    first_token = value.strip().split()[0] if value.strip() else ""
    if first_token.lower().startswith(("http://", "https://")):
        return first_token
    return None


def build_github_link(category_folder: str, toy_folder: str) -> str:
    return (
        f"https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/tree/"
        f"{GITHUB_BRANCH}/Toy_Instructions/{category_folder}/{toy_folder}"
    )


# Filenames checked, in priority order, for the richer per-toy info format.
# "toy_info.md" is the current convention; "toy-info.txt" is kept for
# anyone who set folders up before that convention settled.
# Priority order for locating a toy's info file. "toy_info*.md" is a glob
# pattern, not an exact filename - it matches "toy_info.md" as well as
# per-toy variants like "toy_info_bubble_blower.md", so you can name these
# however you like without any code changes. "toy-info.txt" is kept as an
# exact-match fallback for anyone who set folders up before "toy_info.md"
# became the convention.
INFO_FILENAME_PATTERNS = ["toy_info*.md", "toy-info.txt", "info.txt"]


def find_info_file(toy_dir: Path) -> Path | None:
    for pattern in INFO_FILENAME_PATTERNS:
        matches = sorted(toy_dir.glob(pattern))
        if matches:
            if len(matches) > 1:
                print(
                    f"NOTE: multiple files matched '{pattern}' in "
                    f"{toy_dir.name} - using {matches[0].name}"
                )
            return matches[0]
    return None


# The known option sets from the toy_info.md template, used to pre-seed
# the filter groups so every option shows up on the page immediately -
# even before any toy actually has that value set yet. Anything a toy
# has that ISN'T in these lists still gets added as its own filter
# option (see the "add if new" logic in main()); these lists are just
# the starting point, not a hard restriction on allowed values.
KNOWN_TOY_FEATURES = [
    "Music", "Sound", "Light", "Vibration", "Movement",
    "Bubble", "RC", "Lamp/Projector", "Blaster", "Water",
]
KNOWN_ACTIVATION_TYPES = ["Press and Hold", "Single Press", "Latch"]
KNOWN_ADAPTATION_METHODS = ["Battery Interrupter", "Mono Jack + Wire", "Mono Cable"]
KNOWN_SWITCH_COUNTS = ["1", "2", "3", "4", "5", "6"]


def normalize_to_known(value: str, known_list: list[str]) -> str:
    """
    Case-insensitively matches a raw toy_info.md value (e.g. 'press and
    hold') to its canonical display form from KNOWN_ACTIVATION_TYPES etc.
    (e.g. 'Press and Hold'), so filter matching works regardless of how
    someone capitalized it in the file. Falls back to the value as typed
    if it doesn't match anything known, so new/unexpected values still
    work as their own filter option rather than being silently dropped.
    """
    if not value:
        return ""
    value = value.strip()
    for known in known_list:
        if known.lower() == value.lower():
            return known
    return value


# Static boilerplate shown on every toy detail page, regardless of whether
# that toy has a toy_info.md - edit this text directly whenever real copy
# is ready; it isn't pulled from anywhere per-toy.
GENERAL_TOY_HACKING_INFO = """Every child deserves to play. But for many kids with disabilities, toys can be hard to use independently, and commercially adapted versions can run upwards of $300. However, with a little bit of tinkering, we can switch-adapt toys and make them accessible for a fraction of the cost.

Annually, from September to December, Makers Making Change hosts the [Hacking for the Holidays](https://www.makersmakingchange.com/hacking-for-the-holidays) campaign, where we engage volunteers — students, corporate partners, and other community members — in many build events across Canada to help us adapt and donate thousands of toys and switches to families and clinicians all over Canada.

*Please note: the information on this page is only accurate as of when it was last updated.*

If you are looking for more information on where to purchase the materials to adapt a toy, please visit the [Component & Tool List](../../toy-components-and-tools/) page on this resource."""


def render_toy_page(toy: dict) -> str:
    """
    Builds the markdown for a toy's dedicated detail page. This file lives
    at docs/toys/<slug>.md, which MkDocs (use_directory_urls: true) serves
    at /toys/<slug>/. That means relative links need to climb two levels
    ("../../") to reach the docs root - one for the "toys" folder, one for
    the "<slug>" directory itself.
    """
    image_rel = f"../../{toy['image']}"
    zip_rel = f"../../downloads/{toy['slug']}.zip"

    meta_rows = []
    if toy.get("toy_features"):
        meta_rows.append(f"**Toy Features:** {', '.join(toy['toy_features'])}")
    if toy.get("activation_type"):
        meta_rows.append(f"**Activation Type:** {', '.join(toy['activation_type'])}")
    if toy.get("adaptation_method"):
        meta_rows.append(f"**Method of Adaptation:** {', '.join(toy['adaptation_method'])}")
    if toy.get("number_of_switches"):
        meta_rows.append(f"**Number of Switches:** {', '.join(toy['number_of_switches'])}")
    if toy.get("battery_type"):
        req = toy.get("battery_required")
        inc = toy.get("battery_included")
        battery_line = f"**Battery:** {toy['battery_type']}"
        if req:
            battery_line += f" ({req} required"
            battery_line += f", {inc} included)" if inc else ")"
        meta_rows.append(battery_line)
    if toy.get("adaptation_inputs"):
        meta_rows.append(f"**Switch Inputs:** {toy['adaptation_inputs']}")
    if toy.get("has_info_file"):
        meta_rows.append(f"**Requires 3D Printing:** {'Yes' if toy.get('requires_3d_printing') else 'No'}")
    if toy.get("available_to_purchase"):
        meta_rows.append("**Available to Purchase:** Yes, as of last update")
    if toy.get("last_update"):
        meta_rows.append(f"**Last Updated:** {toy['last_update']}")

    meta_block = "\n".join(f"- {row}" for row in meta_rows)

    hfth_badge = ""
    if toy.get("hfth_collection_year"):
        hfth_badge = f'\n<span class="hfth-badge">🎄 HFTH {toy["hfth_collection_year"]} Collection</span>\n'

    notes_block = ""
    if toy.get("general_notes"):
        notes_block = f"\n**Notes:** {toy['general_notes']}\n"

    availability_note = ""
    if not toy.get("available", True):
        availability_note = (
            '\n!!! warning "Currently unavailable"\n'
            "    This toy adaptation is not currently available/supported.\n"
        )

    if toy.get("has_info_file"):
        # Real toy_info.md data exists - the meta list below already
        # covers it, no filler text needed here.
        description = ""
    else:
        # No toy_info.md at all - most likely a newly added toy folder.
        description = (
            "This toy doesn't have any information added yet (no `toy_info.md` "
            "has been created for it). Check back soon for full details — "
            "in the meantime, the instructions can still be downloaded below."
        )

    purchase_buttons = ""
    if toy.get("toy_purchase_link"):
        purchase_buttons += (
            f'<a href="{toy["toy_purchase_link"]}" class="btn btn-secondary" '
            f'target="_blank" rel="noopener">🛒 Where to Buy This Toy</a>\n'
        )
    if toy.get("toy_purchase_link_alt"):
        purchase_buttons += (
            f'<a href="{toy["toy_purchase_link_alt"]}" class="btn btn-outline" '
            f'target="_blank" rel="noopener">🛒 Alternate Purchase Link</a>\n'
        )

    return f"""# {toy['name']}
{hfth_badge}
<img src="{image_rel}" class="toy-page-image" style="max-width:200px;" alt="Photo of the {toy['name']}">
{availability_note}
{description}
{notes_block}
{meta_block}

<div class="toy-page-buttons">
<a href="{zip_rel}" class="btn btn-primary" download>⬇ Download Instructions (.zip)</a>
{purchase_buttons}<a href="{toy['link']}" class="btn btn-secondary">View Source Folder on GitHub</a>
<a href="https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/issues" class="btn btn-outline">⚠ Report an Issue</a>
</div>

## General Toy Hacking Info

{GENERAL_TOY_HACKING_INFO}

[← Back to all toys](../../toy-instructions/)
"""


def main():
    if not TOY_INSTRUCTIONS_DIR.exists():
        print(f"WARNING: {TOY_INSTRUCTIONS_DIR} does not exist - skipping.")
        return

    IMAGES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    JS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOY_PAGES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_toy_features = list(KNOWN_TOY_FEATURES)
    all_activation_types = list(KNOWN_ACTIVATION_TYPES)
    all_adaptation_methods = list(KNOWN_ADAPTATION_METHODS)
    all_switch_counts = list(KNOWN_SWITCH_COUNTS)
    all_hfth_years = []
    toys = []

    category_dirs = sorted(
        [
            d for d in TOY_INSTRUCTIONS_DIR.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name.lower() not in IGNORED_FOLDERS
        ]
    )

    for category_dir in category_dirs:
        folder_category_name = prettify(category_dir.name)

        toy_dirs = sorted(
            [d for d in category_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )

        for toy_dir in toy_dirs:
            info_file_path = find_info_file(toy_dir)
            info = parse_toy_info(info_file_path)
            has_info_file = info_file_path is not None

            name = info.get("name") or prettify(toy_dir.name)
            # Category can be overridden by toy-info.txt; otherwise use the
            # folder it's actually sitting in.
            category_name = info.get("category") or folder_category_name
            link = clean_url(info.get("link")) or build_github_link(category_dir.name, toy_dir.name)
            description = info.get("description") or ""

            slug = f"{slugify(category_name)}-{slugify(name)}"

            # Toy Features drive the filter bar, and come from
            # toy_info.md's "toy_features" field (or the older "tags"
            # field name, merged in for backwards compatibility) -
            # deliberately not tied to which category folder the toy
            # happens to live in, so a toy can have e.g. "Bubble, RC"
            # regardless of its folder. A toy with none set just has no
            # features (still shows up normally when no filters are
            # active).
            toy_features = [
                normalize_to_known(f, KNOWN_TOY_FEATURES) for f in (info.get("toy_features") or [])
            ]
            for f in toy_features:
                if f and f not in all_toy_features:
                    all_toy_features.append(f)

            activation_types = [
                normalize_to_known(a, KNOWN_ACTIVATION_TYPES) for a in (info.get("activation_type") or [])
            ]
            for a in activation_types:
                if a and a not in all_activation_types:
                    all_activation_types.append(a)

            adaptation_methods = [
                normalize_to_known(m, KNOWN_ADAPTATION_METHODS) for m in (info.get("adaptation_method") or [])
            ]
            for m in adaptation_methods:
                if m and m not in all_adaptation_methods:
                    all_adaptation_methods.append(m)

            number_of_switches = info.get("number_of_switches") or []
            for s in number_of_switches:
                if s and s not in all_switch_counts:
                    all_switch_counts.append(s)

            hfth_year = info.get("hfth_collection_year")
            if hfth_year and hfth_year not in all_hfth_years:
                all_hfth_years.append(hfth_year)

            thumbnail = find_thumbnail(toy_dir)
            if thumbnail:
                image_filename = f"{slug}{thumbnail.suffix.lower()}"
                shutil.copyfile(thumbnail, IMAGES_OUT_DIR / image_filename)
                image_path = f"images/toys/{image_filename}"
            else:
                image_path = "images/placeholder.png"
                print(f"NOTE: no thumbnail found for '{name}' - using placeholder.")

            toy = {
                "name": name,
                "slug": slug,
                "image": image_path,
                "link": link,
                "toy_purchase_link": clean_url(info.get("toy_purchase_link")) or "",
                "toy_purchase_link_alt": clean_url(info.get("toy_purchase_link_alt")) or "",
                "category": category_name,
                "toy_features": toy_features,
                "description": description,
                "available": info.get("available", True),
                "last_update": info.get("last_update") or "",
                "battery_type": info.get("battery_type") or "",
                "battery_required": info.get("battery_required"),
                "battery_included": info.get("battery_included"),
                "adaptation_inputs": info.get("adaptation_inputs"),
                "activation_type": activation_types,
                "requires_3d_printing": info.get("requires_3d_printing", False),
                "adaptation_method": adaptation_methods,
                "number_of_switches": number_of_switches,
                "hfth_collection_year": hfth_year,
                "available_to_purchase": info.get("available_to_purchase", False),
                "general_notes": info.get("general_notes") or "",
                "has_info_file": has_info_file,
            }

            # Zip up the toy's whole folder (instructions, extra photos, CAD
            # files, etc.) as a flat archive - shutil.make_archive with
            # root_dir=toy_dir zips the *contents* of the folder rather than
            # nesting everything one level deeper inside a folder named
            # after the toy.
            shutil.make_archive(
                str(DOWNLOADS_OUT_DIR / slug), "zip", root_dir=str(toy_dir)
            )

            # Write the toy's dedicated detail page (docs/toys/<slug>.md).
            (TOY_PAGES_OUT_DIR / f"{slug}.md").write_text(
                render_toy_page(toy), encoding="utf-8"
            )

            toys.append(toy)

    all_toy_features = sorted(all_toy_features)
    # activation types / adaptation methods / switch counts are left in
    # their seeded order (template order, with any brand-new values
    # encountered in the data appended after) rather than re-sorted, so
    # the known options stay in a sensible, intentional order.

    js_content = (
        "// AUTO-GENERATED by scripts/generate_toy_data.py - do not edit by hand.\n"
        f"window.TOY_FEATURES = {json.dumps(all_toy_features, indent=2)};\n"
        "window.TOY_FILTERS = {\n"
        f"  activationTypes: {json.dumps(all_activation_types, indent=2)},\n"
        f"  adaptationMethods: {json.dumps(all_adaptation_methods, indent=2)},\n"
        f"  switchCounts: {json.dumps(all_switch_counts, indent=2)},\n"
        f"  hfthYears: {json.dumps(sorted(all_hfth_years), indent=2)}\n"
        "};\n"
        f"window.TOY_DATA = {json.dumps(toys, indent=2)};\n"
    )
    JS_OUT_PATH.write_text(js_content, encoding="utf-8")

    print(f"Generated {len(toys)} toy cards across {len(all_toy_features)} toy features.")
    print(f"-> {JS_OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"-> {len(toys)} detail pages in {TOY_PAGES_OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"-> {len(toys)} zip downloads in {DOWNLOADS_OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()