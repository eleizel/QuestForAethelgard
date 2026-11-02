"""Automated Desktop Standalone Executable Builder using PyInstaller.

Packages Quest for Aethelgard into a standalone single-file binary with all assets embedded.
Output is placed in `dist/desktop/QuestForAethelgard.exe`.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import PyInstaller.__main__
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def ensure_icon() -> Path:
    """Generate icon.ico from icon-192.png if needed."""
    ico_path = PROJECT_ROOT / "assets" / "icon.ico"
    png_path = PROJECT_ROOT / "assets" / "icon-192.png"

    if not ico_path.exists() and png_path.exists():
        print(f"Generating {ico_path} from {png_path}...")
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])

    return ico_path


def ensure_assets() -> None:
    """Ensure game.pyxres is generated and verified before PyInstaller packaging."""
    print("--> Verifying / generating Pyxel retro assets (game.pyxres)...")
    generator_script = PROJECT_ROOT / "src" / "tools" / "generate_assets.py"
    cmd = [sys.executable, str(generator_script)]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    pyxres_file = PROJECT_ROOT / "assets" / "game.pyxres"
    if not pyxres_file.exists() or pyxres_file.stat().st_size == 0:
        raise RuntimeError(f"Failed to generate asset package at {pyxres_file}")
    print(f"    [OK] Verified {pyxres_file.name} ({pyxres_file.stat().st_size} bytes)")


def build_desktop() -> None:
    """Run PyInstaller build."""
    ensure_assets()
    ico_path = ensure_icon()

    dist_dir = PROJECT_ROOT / "dist" / "desktop"
    work_dir = PROJECT_ROOT / "build" / "pyinstaller"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Building Quest for Aethelgard Desktop Executable...")
    print("==================================================")

    data_separator = ";" if sys.platform.startswith("win") else ":"

    args = [
        str(PROJECT_ROOT / "main.py"),
        "--onefile",
        "--windowed",
        "--name=QuestForAethelgard",
        f"--add-data={PROJECT_ROOT / 'assets'}{data_separator}assets",
        f"--distpath={dist_dir}",
        f"--workpath={work_dir}",
        "--clean",
        "--noconfirm",
    ]

    if ico_path.exists():
        args.append(f"--icon={ico_path}")

    PyInstaller.__main__.run(args)

    exe_name = "QuestForAethelgard.exe" if sys.platform.startswith("win") else "QuestForAethelgard"
    exe_file = dist_dir / exe_name

    if exe_file.exists():
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        print("==================================================")
        print(f"SUCCESS: Desktop executable built at {exe_file} ({size_mb:.2f} MB)")
        print("==================================================")
    else:
        raise RuntimeError(f"Build failed: executable not found at {exe_file}")


if __name__ == "__main__":
    build_desktop()
