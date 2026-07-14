"""
generate_toy_data.py

Scans the Toy_Instructions folder and automatically builds the data used
by the "Toy Instructions" page (cards + filters).

Folder convention:

    Toy_Instructions/
        <Category Folder>/
            <Toy Folder>/
                <photo>.jpg / .png / .webp   (thumbnail - required)
                info.txt                     (optional overrides)
                ... any other files (assembly guides, 3D files, etc.)
                                              (ignored by this script)

info.txt (optional) format - one item per line:

    Name: Bubble Blower
    Link: https://github.com/makersmakingchange/Switch-Adapted-Bubble-Blower
    Description: A switch-adapted bubble machine for younger kids.

If info.txt is missing entirely, the script falls back to:
    Name  -> the toy folder name, with underscores/hyphens turned into spaces
    Link  -> an auto-built link to that folder on GitHub
    Description -> left blank

Run this BEFORE `mkdocs build` / `mkdocs gh-deploy` in the GitHub Action.
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

GITHUB_ORG = "makersmakingchange"
GITHUB_REPO = "Switch_Adapted_Toys"
GITHUB_BRANCH = "main"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def prettify(folder_name: str) -> str:
    """Turn 'Battery_Interrupter_Toys' into 'Battery Interrupter Toys'."""
    return folder_name.replace("_", " ").replace("-", " ").strip()


def slugify(text: str) -> str:
    """Turn 'Bubble Blower' into 'bubble-blower' (safe for filenames)."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_info_txt(info_path: Path) -> dict:
    """Reads a simple 'Key: value' formatted info.txt file."""
    data = {}
    if not info_path.exists():
        return data
    for line in info_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip().lower()] = value.strip()
    return data


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


def main():
    if not TOY_INSTRUCTIONS_DIR.exists():
        print(f"WARNING: {TOY_INSTRUCTIONS_DIR} does not exist - skipping.")
        return

    IMAGES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    JS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    categories = []
    toys = []

    category_dirs = sorted(
        [d for d in TOY_INSTRUCTIONS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )

    for category_dir in category_dirs:
        category_name = prettify(category_dir.name)
        categories.append(category_name)

        toy_dirs = sorted(
            [d for d in category_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )

        for toy_dir in toy_dirs:
            info = parse_info_txt(toy_dir / "info.txt")

            name = info.get("name") or prettify(toy_dir.name)
            link = info.get("link") or build_github_link(category_dir.name, toy_dir.name)
            description = info.get("description", "")

            thumbnail = find_thumbnail(toy_dir)
            if thumbnail:
                image_filename = f"{slugify(category_name)}-{slugify(name)}{thumbnail.suffix.lower()}"
                shutil.copyfile(thumbnail, IMAGES_OUT_DIR / image_filename)
                image_path = f"images/toys/{image_filename}"
            else:
                image_path = "images/placeholder.png"
                print(f"NOTE: no thumbnail found for '{name}' - using placeholder.")

            toys.append(
                {
                    "name": name,
                    "image": image_path,
                    "link": link,
                    "category": category_name,
                    "description": description,
                }
            )

    js_content = (
        "// AUTO-GENERATED by scripts/generate_toy_data.py - do not edit by hand.\n"
        f"window.TOY_CATEGORIES = {json.dumps(categories, indent=2)};\n"
        f"window.TOY_DATA = {json.dumps(toys, indent=2)};\n"
    )
    JS_OUT_PATH.write_text(js_content, encoding="utf-8")

    print(f"Generated {len(toys)} toy cards across {len(categories)} categories.")
    print(f"-> {JS_OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()