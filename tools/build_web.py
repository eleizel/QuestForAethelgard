"""Automated Dual-Frontend Web Deployment Builder.

Builds both:
1. Root (`/`): 16-bit Super Nintendo Golden Age Edition (Pygame-CE via Pygbag WASM)
2. Subpath (`/pyxel/`): 8-bit Retro Classic Edition (Pyxel via Pyodide WASM)

Disables the on-screen virtual game pad across both distributions and injects
cross-edition switching links and PWA manifest metadata.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def prepare_web_stage() -> Path:
    """Prepare clean staging directory for Pygbag."""
    stage_dir = PROJECT_ROOT / "build" / "web_stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Copy src, assets, and main.py
    shutil.copytree(PROJECT_ROOT / "src", stage_dir / "src")
    shutil.copytree(PROJECT_ROOT / "assets", stage_dir / "assets")
    shutil.copy2(PROJECT_ROOT / "main.py", stage_dir / "main.py")
    return stage_dir


def build_pygame_web(dist_web: Path) -> None:
    """Package Pygame-CE using Pygbag for WebAssembly."""
    print("--> Packaging 16-Bit SNES Edition (Pygame-CE Web)...")
    stage_dir = prepare_web_stage()

    cmd = [
        sys.executable,
        "-m",
        "pygbag",
        "--build",
        "--app_name",
        "QuestForAethelgard",
        str(stage_dir),
    ]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    built_web = stage_dir / "build" / "web"
    if not built_web.exists():
        raise RuntimeError(f"Pygbag build directory not found at {built_web}")

    # Copy built files to dist/web root
    for item in built_web.iterdir():
        dest = dist_web / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Patch dist/web/index.html
    index_file = dist_web / "index.html"
    html = index_file.read_text(encoding="utf-8")

    # Title update
    html = re.sub(
        r"<title>.*?</title>",
        "<title>Quest for Aethelgard — 16-Bit SNES Golden Age Edition</title>",
        html,
        flags=re.IGNORECASE,
    )

    # Disable virtual gamepad / mobile joysticks & style canvas
    no_gamepad_css = """
    <!-- Disable Virtual Gamepad and Embedded Diagnostic Overlays -->
    <style>
        #pyxel-gamepad-cross, #pyxel-gamepad-button,
        #crt, #system, .virtual-gamepad, .dpad,
        #aiostop, #aiopaused_true, #aiopaused_false,
        #pygame_mixer_music_pause, .button-container {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
    </style>
    <!-- Cross-Edition Navigation Link -->
    <a id="retro-edition-btn" href="pyxel/" style="position:fixed; bottom:12px; right:14px; z-index:999999; background:rgba(20,24,36,0.92); color:#ffd700; border:1px solid #e2a829; border-radius:6px; padding:7px 13px; font-family:'Segoe UI',system-ui,sans-serif; font-size:12px; font-weight:bold; text-decoration:none; box-shadow:0 3px 8px rgba(0,0,0,0.6); transition:all 0.2s;" onmouseover="this.style.background='#2c3652';this.style.borderColor='#ffea75'" onmouseout="this.style.background='rgba(20,24,36,0.92)';this.style.borderColor='#e2a829'">🕹️ Switch to 8-Bit Pyxel Edition</a>
    """

    if "</head>" in html:
        html = html.replace("</head>", f"{no_gamepad_css}\n</head>", 1)
    else:
        html += no_gamepad_css

    index_file.write_text(html, encoding="utf-8")
    print("    [OK] Pygame-CE Web Edition built and patched.")


def build_pyxel_web(dist_web: Path) -> None:
    """Package Pyxel using pyxel package & app2html."""
    print("--> Packaging 8-Bit Retro Edition (Pyxel Web)...")
    dist_pyxel = dist_web / "pyxel"
    dist_pyxel.mkdir(parents=True, exist_ok=True)

    stage_dir = PROJECT_ROOT / "build" / "pyxel_stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Copy clean runtime assets & code
    shutil.copytree(PROJECT_ROOT / "src", stage_dir / "src")
    shutil.copytree(PROJECT_ROOT / "assets", stage_dir / "assets")
    shutil.copy2(PROJECT_ROOT / "pyxel_main.py", stage_dir / "pyxel_main.py")

    # 1. Package pyxapp using pyxel_main.py entrypoint from staging
    subprocess.run(
        [sys.executable, "-m", "pyxel", "package", str(stage_dir), str(stage_dir / "pyxel_main.py")],
        check=True,
        cwd=PROJECT_ROOT,
    )

    pyxapp_path = PROJECT_ROOT / "pyxel_stage.pyxapp"
    html_path = PROJECT_ROOT / "pyxel_stage.html"

    # 2. Convert pyxapp to standalone HTML
    subprocess.run(
        [sys.executable, "-m", "pyxel", "app2html", str(pyxapp_path)],
        check=True,
        cwd=PROJECT_ROOT,
    )

    dest_index = dist_pyxel / "index.html"
    shutil.move(str(html_path), str(dest_index))

    # Clean up temporary pyxapp from root
    if pyxapp_path.exists():
        pyxapp_path.unlink()

    # 3. Patch Pyxel index.html: Disable virtual gamepad and add cross-edition link
    pyxel_html = dest_index.read_text(encoding="utf-8")

    # Disable gamepad parameter in launchPyxel call
    pyxel_html = pyxel_html.replace('gamepad: "enabled"', 'gamepad: "disabled"')

    # Inject CSS to ensure gamepad images never render, plus navigation button
    pyxel_addons = """
    <!-- Disable Pyxel Virtual Gamepad -->
    <style>
        #pyxel-gamepad-cross, #pyxel-gamepad-button {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }
    </style>
    <!-- Cross-Edition Navigation Link -->
    <a id="snes-edition-btn" href="../" style="position:fixed; bottom:12px; right:14px; z-index:999999; background:rgba(16,20,32,0.92); color:#50d7eb; border:1px solid #50d7eb; border-radius:6px; padding:7px 13px; font-family:'Segoe UI',system-ui,sans-serif; font-size:12px; font-weight:bold; text-decoration:none; box-shadow:0 3px 8px rgba(0,0,0,0.6); transition:all 0.2s;" onmouseover="this.style.background='#222c42';this.style.borderColor='#8ce8f5'" onmouseout="this.style.background='rgba(16,20,32,0.92)';this.style.borderColor='#50d7eb'">⚔️ Switch to 16-Bit SNES Edition</a>
    """

    if "<head>" in pyxel_html:
        pyxel_html = pyxel_html.replace("<head>", f"<head>\n{pyxel_addons}", 1)
    else:
        pyxel_html = f"{pyxel_addons}\n{pyxel_html}"

    dest_index.write_text(pyxel_html, encoding="utf-8")
    print("    [OK] Pyxel Web Edition built and patched (Virtual Gamepad Disabled).")


def copy_pwa_metadata(dist_web: Path) -> None:
    """Copy PWA manifests, icons, and metadata to webroot."""
    print("--> Copying PWA assets & manifests...")
    assets_dir = PROJECT_ROOT / "assets"

    manifest_src = assets_dir / "manifest.json"
    if manifest_src.exists():
        shutil.copy2(manifest_src, dist_web / "manifest.json")

    for icon in ["icon-192.png", "icon-512.png", "icon.ico"]:
        src = assets_dir / icon
        if src.exists():
            shutil.copy2(src, dist_web / icon)

    screenshots_dir = assets_dir / "screenshots"
    if screenshots_dir.exists():
        for s in screenshots_dir.glob("*"):
            shutil.copy2(s, dist_web / s.name)

    well_known = assets_dir / ".well-known"
    if well_known.exists():
        dest_wk = dist_web / ".well-known"
        if dest_wk.exists():
            shutil.rmtree(dest_wk)
        shutil.copytree(well_known, dest_wk)

    print("    [OK] PWA assets copied.")


def build_dual_web() -> None:
    """Build complete dual-frontend web deployment."""
    dist_web = PROJECT_ROOT / "dist" / "web"
    dist_web.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Building Dual-Frontend Web Deployment...")
    print("1. Root (/): Pygame-CE 16-Bit SNES Edition")
    print("2. Subpath (/pyxel/): Pyxel 8-Bit Retro Edition")
    print("==================================================")

    build_pygame_web(dist_web)
    build_pyxel_web(dist_web)
    copy_pwa_metadata(dist_web)

    print("==================================================")
    print("SUCCESS: Dual-frontend web deployment ready in `dist/web/`!")
    print("==================================================")


if __name__ == "__main__":
    build_dual_web()
