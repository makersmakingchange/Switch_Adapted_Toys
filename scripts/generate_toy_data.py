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

toy_info.md (optional) format - one item per line, e.g.:

    Name: Bubble Blower
    Available: true
    Last Update: 2025-09-23
    Category: Bubble
    Tags: Bubble, Battery Powered
    Link: https://github.com/makersmakingchange/Switch-Adapted-Bubble-Blower
    Description: A switch-adapted bubble machine for younger kids.
    Battery Type: AA
    Battery Required: 2
    Battery Included: 2
    Adaptation Inputs: 2
    Activation Type: Single Press
    Requires 3D Printing: No
    Method Of Adaption: Battery Interrupter
    Number Of Switches: 2
    HFTH 2026: Yes
    Available To Purchase As Of Last Update: Yes
    General Notes: Works best with a jelly bean switch.

Tags drive the main filter chips on the "Toy Instructions" page (rather
than category/folder). A toy can have as many comma-separated tags as you
want, and shows up under every one of them. If a toy has no Tags line yet,
it just falls back to using its Category as its one tag, so nothing
disappears from the filters for toys that haven't been retagged.

Activation Type, Method Of Adaption, and Number Of Switches feed a
secondary set of grouped filters (shown collapsed under "More Filters" so
the page isn't overwhelming with chips) - a filter chip only appears for
values that at least one toy actually has. HFTH 2026, Requires 3D
Printing, and Available To Purchase As Of Last Update are simple Yes/No
toggles rather than chip groups, since they're binary. All of these are
optional per toy; leaving one blank just means that toy won't show up
under that particular filter, without affecting any other filter.

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


def parse_info_txt(info_path: Path | None) -> dict:
    """Reads a simple 'Key: value' formatted info.txt file (legacy format)."""
    data = {}
    if not info_path or not info_path.exists():
        return data
    for line in info_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("---"):
            break  # stop at the "what each line means" divider, if present
        if ":" not in line or stripped.startswith("#"):
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


def parse_toy_info(info_path: Path) -> dict:
    """
    Reads the richer plain-text toy-info.txt format (Key: value lines,
    same style as the legacy info.txt but with more fields) and returns
    a dict of the fields the site uses. Returns {} if the file doesn't
    exist. Lines starting with '#' are treated as comments and ignored,
    so the instructional text at the bottom of the template is safely
    skipped.
    """
    raw = parse_info_txt(info_path)  # reuses the same "Key: value" parsing
    if not raw:
        return {}

    return {
        "name": raw.get("name"),
        "available": to_bool(raw.get("available")),
        "last_update": (
            raw.get("info last updated (mm/dd/yyyy)")
            or raw.get("last updated")
            or raw.get("last update")
            or raw.get("last_update")
        ),
        "category": raw.get("category"),
        "tags": raw.get("tags"),
        "link": raw.get("link"),
        "description": raw.get("description"),
        "battery_type": raw.get("battery type") or raw.get("battery_type"),
        "battery_required": to_int(raw.get("battery required") or raw.get("battery_required")),
        "battery_included": to_int(raw.get("battery included") or raw.get("battery_included")),
        "adaptation_inputs": to_int(raw.get("adaptation inputs") or raw.get("adaptation_inputs")),
        # Fields from the newer toy-info template:
        "activation_type": raw.get("activation type") or raw.get("activation_type"),
        "requires_3d_printing": to_bool(raw.get("requires 3d printing") or raw.get("requires_3d_printing"), default=False),
        "adaptation_method": raw.get("method of adaption") or raw.get("method of adaptation") or raw.get("adaptation_method"),
        "number_of_switches": to_int(raw.get("number of switches") or raw.get("number_of_switches")),
        "hfth_2026": to_bool(raw.get("hfth 2026") or raw.get("hfth_2026"), default=False),
        "available_to_purchase": to_bool(raw.get("available to purchase as of last update") or raw.get("available_to_purchase"), default=False),
        "general_notes": raw.get("general notes") or raw.get("general_notes"),
    }


def find_thumbnail(toy_dir: Path) -> Path | None:
    """Finds the first image file in a toy folder, alphabetically."""
    images = sorted(
        [f for f in toy_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    )
    return images[0] if images else None


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
INFO_FILENAME_PATTERNS = ["toy_info*.md", "toy-info.txt"]


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
KNOWN_ACTIVATION_TYPES = ["Press and Hold", "Single Press"]
KNOWN_ADAPTATION_METHODS = ["Battery Interrupter", "Mono Jack + Wire", "Mono Cable"]
KNOWN_SWITCH_COUNTS = [1, 2, 3, 4, 5, 6]


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
GENERAL_TOY_HACKING_INFO = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat."
)


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
    if toy.get("tags"):
        meta_rows.append(f"**Tags:** {', '.join(toy['tags'])}")
    if toy.get("activation_type"):
        meta_rows.append(f"**Activation Type:** {toy['activation_type']}")
    if toy.get("adaptation_method"):
        meta_rows.append(f"**Method of Adaptation:** {toy['adaptation_method']}")
    if toy.get("number_of_switches"):
        meta_rows.append(f"**Number of Switches:** {toy['number_of_switches']}")
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
    if toy.get("hfth_2026"):
        hfth_badge = '\n<span class="hfth-badge">🎄 HFTH 2026</span>\n'

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

    return f"""# {toy['name']}
{hfth_badge}
<img src="{image_rel}" class="toy-page-image" style="max-width:200px;" alt="Photo of the {toy['name']}">
{availability_note}
{description}
{notes_block}
{meta_block}

<div class="toy-page-buttons">
<a href="{zip_rel}" class="btn btn-primary" download>⬇ Download Instructions (.zip)</a>
<a href="{toy['link']}" class="btn btn-secondary">View Source Folder on GitHub</a>
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

    all_tags = []
    all_activation_types = list(KNOWN_ACTIVATION_TYPES)
    all_adaptation_methods = list(KNOWN_ADAPTATION_METHODS)
    all_switch_counts = list(KNOWN_SWITCH_COUNTS)
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
            info = parse_toy_info(find_info_file(toy_dir))
            if not info:
                # Fall back to the old info.txt format, in case some
                # folders were set up before this richer format existed.
                legacy = parse_info_txt(toy_dir / "info.txt")
                if legacy:
                    info = {
                        "name": legacy.get("name"),
                        "link": legacy.get("link"),
                        "description": legacy.get("description"),
                    }
            has_info_file = bool(info)

            name = info.get("name") or prettify(toy_dir.name)
            # Category can be overridden by toy-info.txt; otherwise use the
            # folder it's actually sitting in.
            category_name = info.get("category") or folder_category_name
            link = info.get("link") or build_github_link(category_dir.name, toy_dir.name)
            description = info.get("description") or ""

            slug = f"{slugify(category_name)}-{slugify(name)}"

            # Tags drive the filter bar, and come ONLY from toy_info.md's
            # "Tags: a, b, c" field - deliberately not tied to which
            # category folder the toy happens to live in, so a toy can be
            # tagged e.g. "Bubble, RC" regardless of its folder. A toy
            # with no Tags line set just has no tags (still shows up
            # normally when no filters are active).
            tags = to_list(info.get("tags"))
            for t in tags:
                if t not in all_tags:
                    all_tags.append(t)

            activation_type = normalize_to_known(info.get("activation_type") or "", KNOWN_ACTIVATION_TYPES)
            if activation_type and activation_type not in all_activation_types:
                all_activation_types.append(activation_type)

            adaptation_method = normalize_to_known(info.get("adaptation_method") or "", KNOWN_ADAPTATION_METHODS)
            if adaptation_method and adaptation_method not in all_adaptation_methods:
                all_adaptation_methods.append(adaptation_method)

            number_of_switches = info.get("number_of_switches")
            if number_of_switches and number_of_switches not in all_switch_counts:
                all_switch_counts.append(number_of_switches)

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
                "category": category_name,
                "tags": tags,
                "description": description,
                "available": info.get("available", True),
                "last_update": info.get("last_update") or "",
                "battery_type": info.get("battery_type") or "",
                "battery_required": info.get("battery_required"),
                "battery_included": info.get("battery_included"),
                "adaptation_inputs": info.get("adaptation_inputs"),
                "activation_type": activation_type,
                "requires_3d_printing": info.get("requires_3d_printing", False),
                "adaptation_method": adaptation_method,
                "number_of_switches": number_of_switches,
                "hfth_2026": info.get("hfth_2026", False),
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

    all_tags = sorted(all_tags)
    # activation types / adaptation methods / switch counts are left in
    # their seeded order (template order, with any brand-new values
    # encountered in the data appended after) rather than re-sorted, so
    # the known options stay in a sensible, intentional order.

    js_content = (
        "// AUTO-GENERATED by scripts/generate_toy_data.py - do not edit by hand.\n"
        f"window.TOY_TAGS = {json.dumps(all_tags, indent=2)};\n"
        "window.TOY_FILTERS = {\n"
        f"  activationTypes: {json.dumps(all_activation_types, indent=2)},\n"
        f"  adaptationMethods: {json.dumps(all_adaptation_methods, indent=2)},\n"
        f"  switchCounts: {json.dumps(all_switch_counts, indent=2)}\n"
        "};\n"
        f"window.TOY_DATA = {json.dumps(toys, indent=2)};\n"
    )
    JS_OUT_PATH.write_text(js_content, encoding="utf-8")

    print(f"Generated {len(toys)} toy cards across {len(all_tags)} tags.")
    print(f"-> {JS_OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"-> {len(toys)} detail pages in {TOY_PAGES_OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"-> {len(toys)} zip downloads in {DOWNLOADS_OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()