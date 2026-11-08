"""Verify release assets referenced by the UI manifest.

Run from the repository root with ``python tools/verify_assets.py``.  The
check is intentionally dependency-light: it validates manifest structure,
referenced file existence/non-emptiness, and decodes image files with Pillow.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "assets" / "ui_asset_manifest.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _asset_paths(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for nested_value in value.values():
            yield from _asset_paths(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            yield from _asset_paths(nested_value)
    elif isinstance(value, str) and value.startswith("assets/"):
        yield value


def verify_assets() -> list[str]:
    """Return a list of validation errors for all manifest-referenced assets."""
    errors: list[str] = []
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"Cannot read {MANIFEST_PATH}: {error}"]

    if not isinstance(manifest, dict):
        return [f"{MANIFEST_PATH} must contain a JSON object"]

    for relative_path in sorted(set(_asset_paths(manifest))):
        asset_path = PROJECT_ROOT / relative_path
        if not asset_path.is_file():
            errors.append(f"Missing asset: {relative_path}")
            continue
        if asset_path.stat().st_size == 0:
            errors.append(f"Empty asset: {relative_path}")
            continue
        if asset_path.suffix.lower() in IMAGE_SUFFIXES:
            try:
                with Image.open(asset_path) as image:
                    image.verify()
            except (OSError, UnidentifiedImageError) as error:
                errors.append(f"Unreadable image {relative_path}: {error}")
    return errors


def main() -> int:
    errors = verify_assets()
    if errors:
        print("Asset verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Asset verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
