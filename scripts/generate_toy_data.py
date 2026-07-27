"""
generate_toy_data.py

Scans the Toy_Instructions folder and automatically builds the data used
by the "Toy Instructions" page (cards + filters).

Folder convention:

    Toy_Instructions/
        <Category Folder>/
            <Toy Folder>/
                <photo>.jpg / .png / .webp   (thumbnail - optional)
                toy-info.txt                 (optional overrides, see below)
                ... any other files (assembly guides, 3D files, etc.)
                                              (ignored by this script)

toy-info.txt (optional) format - one item per line, e.g.:

    Name: Bubble Blower
    Available: true
    Last Update: 2025-09-23
    Category: Bubble
    Link: https://github.com/makersmakingchange/Switch-Adapted-Bubble-Blower
    Description: A switch-adapted bubble machine for younger kids.
    Battery Type: AA
    Battery Required: 2
    Battery Included: 2
    Adaptation Inputs: 2

If toy-info.txt is missing entirely, the script falls back to:
    Name     -> the toy folder name, with underscores/hyphens turned into spaces
    Category -> the name of the folder this toy sits directly inside
    Link     -> an auto-built link to that folder on GitHub
    Available, Description, Battery/Adaptation fields -> left blank/default

Also still reads the older, simpler "info.txt" format (Name/Link/Description
only) if toy-info.txt isn't present, for backwards compatibility.

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


def parse_info_txt(info_path: Path) -> dict:
    """Reads a simple 'Key: value' formatted info.txt file (legacy format)."""
    data = {}
    if not info_path.exists():
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
        "last_update": raw.get("last update") or raw.get("last_update"),
        "category": raw.get("category"),
        "link": raw.get("link"),
        "description": raw.get("description"),
        "battery_type": raw.get("battery type") or raw.get("battery_type"),
        "battery_required": to_int(raw.get("battery required") or raw.get("battery_required")),
        "battery_included": to_int(raw.get("battery included") or raw.get("battery_included")),
        "adaptation_inputs": to_int(raw.get("adaptation inputs") or raw.get("adaptation_inputs")),
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
    if toy.get("last_update"):
        meta_rows.append(f"**Last Updated:** {toy['last_update']}")

    meta_block = "\n".join(f"- {row}" for row in meta_rows)

    availability_note = ""
    if not toy.get("available", True):
        availability_note = (
            '\n!!! warning "Currently unavailable"\n'
            "    This toy adaptation is not currently available/supported.\n"
        )

    description = toy.get("description") or "No description has been added for this toy yet."

    return f"""# {toy['name']}

<img src="{image_rel}" class="toy-page-image" alt="Photo of the {toy['name']}">

**Category:** {toy['category']}
{availability_note}
{description}

{meta_block}

<a href="{zip_rel}" class="download-button" download>⬇ Download Instructions (.zip)</a>

[View this toy's source folder on GitHub]({toy['link']})

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

    categories = []
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
            info = parse_toy_info(toy_dir / "toy-info.txt")
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

            name = info.get("name") or prettify(toy_dir.name)
            # Category can be overridden by toy-info.txt; otherwise use the
            # folder it's actually sitting in.
            category_name = info.get("category") or folder_category_name
            link = info.get("link") or build_github_link(category_dir.name, toy_dir.name)
            description = info.get("description") or ""

            slug = f"{slugify(category_name)}-{slugify(name)}"

            thumbnail = find_thumbnail(toy_dir)
            if thumbnail:
                image_filename = f"{slug}{thumbnail.suffix.lower()}"
                shutil.copyfile(thumbnail, IMAGES_OUT_DIR / image_filename)
                image_path = f"images/toys/{image_filename}"
            else:
                image_path = "images/placeholder.png"
                print(f"NOTE: no thumbnail found for '{name}' - using placeholder.")

            if category_name not in categories:
                categories.append(category_name)

            toy = {
                "name": name,
                "slug": slug,
                "image": image_path,
                "link": link,
                "category": category_name,
                "description": description,
                "available": info.get("available", True),
                "last_update": info.get("last_update") or "",
                "battery_type": info.get("battery_type") or "",
                "battery_required": info.get("battery_required"),
                "battery_included": info.get("battery_included"),
                "adaptation_inputs": info.get("adaptation_inputs"),
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

    categories = sorted(categories)

    js_content = (
        "// AUTO-GENERATED by scripts/generate_toy_data.py - do not edit by hand.\n"
        f"window.TOY_CATEGORIES = {json.dumps(categories, indent=2)};\n"
        f"window.TOY_DATA = {json.dumps(toys, indent=2)};\n"
    )
    JS_OUT_PATH.write_text(js_content, encoding="utf-8")

    print(f"Generated {len(toys)} toy cards across {len(categories)} categories.")
    print(f"-> {JS_OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"-> {len(toys)} detail pages in {TOY_PAGES_OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"-> {len(toys)} zip downloads in {DOWNLOADS_OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()