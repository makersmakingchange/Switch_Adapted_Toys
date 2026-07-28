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
    Tags: Bubble, HFTH 2026, Battery Powered
    Link: https://github.com/makersmakingchange/Switch-Adapted-Bubble-Blower
    Description: A switch-adapted bubble machine for younger kids.
    Battery Type: AA
    Battery Required: 2
    Battery Included: 2
    Adaptation Inputs: 2

Tags drive the filter chips on the "Toy Instructions" page (rather than
category/folder). A toy can have as many comma-separated tags as you want,
and shows up under every one of them - e.g. tagging a toy with
"HFTH 2026" makes it show up both under its usual category tag AND under
an "HFTH 2026" filter alongside any other toy tagged that way, regardless
of which category folder either one lives in. If a toy has no Tags line
yet, it just falls back to using its Category as its one tag, so nothing
disappears from the filters for toys that haven't been retagged.

If toy-info.txt is missing entirely, the script falls back to:
    Name     -> the toy folder name, with underscores/hyphens turned into spaces
    Category -> the name of the folder this toy sits directly inside
    Tags     -> [Category] (a single tag matching the category)
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

import os
import re
import json
import shutil
import zipfile
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
TOYS_SOURCE_DIR = ROOT_DIR / "toys"
TOYS_DOCS_DIR = DOCS_DIR / "toys"
DOWNLOADS_DIR = DOCS_DIR / "downloads"
JS_OUTPUT_PATH = DOCS_DIR / "js" / "toy-data.js"


def parse_info_txt(info_path: Path) -> dict:
    if not info_path.exists():
        return {}
    data = {}
    with open(info_path, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip().lower()] = val.strip()
    return data


def to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if not val:
        return True
    return str(val).strip().lower() not in ("false", "no", "0", "off")


def to_int(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def parse_toy_info(info_path: Path) -> dict:
    raw = parse_info_txt(info_path)
    if not raw:
        return {}

    return {
        "name": raw.get("name"),
        "available": to_bool(raw.get("available")),
        "last_update": raw.get("last update") or raw.get("last_update"),
        "category": raw.get("category"),
        "tags": raw.get("tags"),
        "link": raw.get("link"),
        "description": raw.get("description"),
        "battery_type": raw.get("battery type") or raw.get("battery_type"),
        "battery_required": to_int(raw.get("battery required") or raw.get("battery_required")),
        "battery_included": to_int(raw.get("battery included") or raw.get("battery_included")),
        "adaptation_inputs": to_int(raw.get("adaptation inputs") or raw.get("adaptation_inputs")),
        "build_type": raw.get("build type") or raw.get("build_type") or "",
        "method": raw.get("method") or "",
        "activation_type": raw.get("activation type") or raw.get("activation_type") or "",
        "requires_3d": raw.get("requires 3d printed parts") or raw.get("requires_3d") or "",
    }


def find_toy_image(toy_dir: Path) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        for img in toy_dir.glob(f"*{ext}"):
            if img.name.lower() != "cover.jpg":
                return f"images/toys/{toy_dir.name}/{img.name}"
    return "images/placeholder.png"


def create_zip_archive(toy_dir: Path, zip_path: Path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(toy_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(toy_dir)
                zf.write(file_path, arcname)


def render_toy_page(toy: dict) -> str:
    image_rel = f"../../{toy['image']}"
    zip_rel = f"../../downloads/{toy['slug']}.zip"
    issue_link = "https://github.com/makersmakingchange/Switch_Adapted_Toys/issues"

    meta_rows = []
    if toy.get("tags"):
        meta_rows.append(f"**Tags:** {', '.join(toy['tags'])}")
    if toy.get("build_type"):
        meta_rows.append(f"**Build Type:** {toy['build_type']}")
    if toy.get("battery_type"):
        req = toy.get("battery_required")
        inc = toy.get("battery_included")
        battery_line = f"**Battery:** {toy['battery_type']}"
        if req:
            battery_line += f" ({req} required"
            battery_line += f", {inc} included)" if inc else ")"
        meta_rows.append(battery_line)
    if toy.get("method"):
        meta_rows.append(f"**Method:** {toy['method']}")
    if toy.get("adaptation_inputs"):
        meta_rows.append(f"**Number of Inputs:** {toy['adaptation_inputs']}")
    if toy.get("activation_type"):
        meta_rows.append(f"**Activation Type:** {toy['activation_type']}")
    if toy.get("requires_3d"):
        meta_rows.append(f"**Requires 3D Printed Parts:** {toy['requires_3d']}")
    if toy.get("last_update"):
        meta_rows.append(f"**Last Updated:** {toy['last_update']}")

    meta_block = "\n".join(f"- {row}" for row in meta_rows)

    availability_note = ""
    if not toy.get("available", True):
        availability_note = (
            '\n!!! warning "Currently unavailable"\n'
            "    This toy adaptation is not currently available/supported.\n"
        )

    has_info = bool(toy.get("description")) or bool(toy.get("battery_type")) or bool(toy.get("adaptation_inputs"))
    if toy.get("description"):
        description = toy["description"]
    elif has_info:
        description = "No written description has been added for this toy yet."
    else:
        description = (
            "This toy doesn't have any information added yet (no `toy-info.txt` "
            "has been created for it). Check back soon for a full description — "
            "in the meantime, the instructions can still be downloaded below."
        )

    return f"""# {toy['name']}

<img src="{image_rel}" class="toy-page-image-half" alt="Photo of the {toy['name']}">

**Category:** {toy['category']}
{availability_note}
{description}

{meta_block}

<div class="toy-action-buttons">
  <a href="{zip_rel}" class="download-button" download>⬇ Download Instructions (.zip)</a>
  <a href="{toy['link']}" class="secondary-button" target="_blank" rel="noopener">View Source Folder on GitHub</a>
  <a href="{issue_link}" class="issue-button" target="_blank" rel="noopener">Report an Issue with the Toy or Instructions</a>
</div>

[← Back to all toys](../../toy-instructions/)
"""


def main():
    if not TOYS_SOURCE_DIR.exists():
        print(f"Error: Toys source directory {TOYS_SOURCE_DIR} does not exist.")
        return

    TOYS_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    JS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    toys_data = []
    all_tags = set()

    for category_dir in sorted(TOYS_SOURCE_DIR.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue
        category_name = category_dir.name.replace("_", " ").title()

        for toy_dir in sorted(category_dir.iterdir()):
            if not toy_dir.is_dir() or toy_dir.name.startswith("."):
                continue

            slug = toy_dir.name
            info_path = toy_dir / "toy-info.txt"
            info = parse_toy_info(info_path)

            name = info.get("name") or slug.replace("_", " ").title()
            image_path = find_toy_image(toy_dir)
            link = info.get("link") or f"https://github.com/makersmakingchange/Switch_Adapted_Toys/tree/main/toys/{category_dir.name}/{slug}"
            
            raw_tags = info.get("tags", "")
            tags = [t.strip() for t in raw_tags.split(",")] if raw_tags else [category_name]
            for t in tags:
                if t:
                    all_tags.add(t)

            description = info.get("description", "")

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
                "build_type": info.get("build_type") or "",
                "method": info.get("method") or "",
                "activation_type": info.get("activation_type") or "",
                "requires_3d": info.get("requires_3d") or "",
            }
            toys_data.append(toy)

            # Generate markdown page
            page_content = render_toy_page(toy)
            toy_doc_dir = TOYS_DOCS_DIR / slug
            toy_doc_dir.mkdir(parents=True, exist_ok=True)
            with open(toy_doc_dir / "index.md", "w", encoding="utf-8") as f:
                f.write(page_content)

            # Generate ZIP archive
            zip_path = DOWNLOADS_DIR / f"{slug}.zip"
            create_zip_archive(toy_dir, zip_path)

    # Write out JSON/JS file for the frontend app
    js_content = f"""// Generated automatically by scripts/generate_toy_data.py
window.TOY_DATA = {json.dumps(toys_data, indent=2)};
window.TOY_TAGS = {json.dumps(sorted(list(all_tags)), indent=2)};
"""
    with open(JS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Successfully processed {len(toys_data)} toys.")


if __name__ == "__main__":
    main()