"""Automated Dual-Frontend Web Deployment Builder.

Builds both:
1. Root (`/`): 16-bit Super Nintendo Golden Age Edition (Pygame-CE via Pygbag WASM)
2. Subpath (`/pyxel/`): 8-bit Retro Classic Edition (Pyxel via Pyodide WASM)

Disables the on-screen virtual game pad across both distributions, enforces
landscape orientation metadata and PWA manifest configurations, and provides
responsive portrait rotation guidance for mobile browsers.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AUDIO_REJECTION_GUARD = """
    <!-- Audio Promise Rejection Guard for WebAssembly / Browsers -->
    <script>
        (function() {
            if (typeof window !== 'undefined' && typeof HTMLMediaElement !== 'undefined') {
                const originalPlay = HTMLMediaElement.prototype.play;
                HTMLMediaElement.prototype.play = function() {
                    const result = originalPlay.apply(this, arguments);
                    if (result !== undefined && typeof result.catch === 'function') {
                        result.catch(function(err) {
                            if (err && (err.name === 'AbortError' || (err.message && err.message.indexOf('interrupted by a call to pause') !== -1))) {
                                return;
                            }
                        });
                    }
                    return result;
                };

                window.addEventListener('unhandledrejection', function(event) {
                    const reason = event.reason;
                    if (reason && (reason.name === 'AbortError' || (reason.message && reason.message.indexOf('interrupted by a call to pause') !== -1))) {
                        event.preventDefault();
                    }
                });
            }
        })();
    </script>
"""



def ensure_assets() -> None:
    """Ensure game.pyxres is generated and verified before staging/packaging."""
    print("--> Verifying / generating Pyxel retro assets (game.pyxres)...")
    generator_script = PROJECT_ROOT / "src" / "tools" / "generate_assets.py"
    cmd = [sys.executable, str(generator_script)]
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    pyxres_file = PROJECT_ROOT / "assets" / "game.pyxres"
    if not pyxres_file.exists() or pyxres_file.stat().st_size == 0:
        raise RuntimeError(f"Failed to generate asset package at {pyxres_file}")
    print(f"    [OK] Verified {pyxres_file.name} ({pyxres_file.stat().st_size} bytes)")


def _convert_mp3_to_ogg(mp3_path: Path, ogg_path: Path) -> None:
    """Convert an MP3 file to OGG Vorbis for web deployment using ffmpeg or soundfile."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-i",
            str(mp3_path),
            "-c:a",
            "libvorbis",
            "-q:a",
            "4",
            str(ogg_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and ogg_path.exists():
            return

    try:
        import soundfile as sf

        with sf.SoundFile(str(mp3_path), "r") as r:
            with sf.SoundFile(
                str(ogg_path),
                "w",
                samplerate=r.samplerate,
                channels=r.channels,
                format="OGG",
                subtype="VORBIS",
            ) as w:
                while True:
                    chunk = r.read(65536, dtype="float32")
                    if len(chunk) == 0:
                        break
                    w.write(chunk)
    except Exception as e:
        print(f"Warning: Could not convert {mp3_path.name} to OGG: {e}")


def prepare_web_stage() -> Path:
    """Prepare clean staging directory for Pygbag."""
    ensure_assets()
    stage_dir = PROJECT_ROOT / "build" / "web_stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Copy src, assets, and main.py
    shutil.copytree(PROJECT_ROOT / "src", stage_dir / "src")
    shutil.copytree(PROJECT_ROOT / "assets", stage_dir / "assets")
    shutil.copy2(PROJECT_ROOT / "main.py", stage_dir / "main.py")

    # Pygbag and WebAssembly audio backends forbid MP3 files. Convert any MP3s to OGG for web staging.
    music_stage = stage_dir / "assets" / "music"
    if music_stage.is_dir():
        for mp3_file in list(music_stage.glob("*.mp3")):
            ogg_file = mp3_file.with_suffix(".ogg")
            if not ogg_file.exists():
                _convert_mp3_to_ogg(mp3_file, ogg_file)
            mp3_file.unlink()

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

    # Set dark gothic background in python preloader
    html = html.replace('platform.document.body.style.background = "#7f7f7f"', 'platform.document.body.style.background = "#0b0e14"')

    # Landscape, PWA, and meta enhancements for 16-Bit SNES Edition
    landscape_head_tags = """
    <!-- PWA & Mobile Landscape Directives -->
    <link rel="manifest" href="manifest.json">
    <meta name="screen-orientation" content="landscape">
    <meta name="x5-orientation" content="landscape">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    """

    # Disable virtual gamepad, style background & canvas, and provide portrait rotation prompt
    landscape_and_ui_css = """
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

        body {
            background-color: #0b0e14 !important;
            overflow: hidden;
            touch-action: manipulation;
        }

        /* Portrait orientation guidance prompt */
        #portrait-prompt {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(11, 14, 20, 0.96);
            backdrop-filter: blur(8px);
            z-index: 9999998;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 24px;
            box-sizing: border-box;
        }

        @media screen and (orientation: portrait) and (max-device-width: 1024px) {
            #portrait-prompt {
                display: flex !important;
            }
        }

        .rotate-anim-icon {
            font-size: 52px;
            margin-bottom: 18px;
            display: inline-block;
            animation: phone-rotate 2.4s infinite ease-in-out;
        }

        @keyframes phone-rotate {
            0%, 15% { transform: rotate(0deg); }
            50%, 65% { transform: rotate(-90deg); }
            100% { transform: rotate(0deg); }
        }

        .prompt-title {
            font-size: 21px;
            font-weight: 700;
            color: #ffd700;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }

        .prompt-desc {
            font-size: 14px;
            color: #cbd5e0;
            max-width: 320px;
            line-height: 1.6;
            margin-bottom: 24px;
        }

        .btn-prompt-landscape {
            background: #2b6cb0;
            color: #ffffff;
            border: 1px solid #4299e1;
            border-radius: 8px;
            padding: 11px 22px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            transition: background 0.2s;
        }

        .btn-prompt-landscape:hover {
            background: #3182ce;
        }

        .btn-prompt-dismiss {
            margin-top: 16px;
            background: transparent;
            border: none;
            color: #718096;
            font-size: 12px;
            cursor: pointer;
            text-decoration: underline;
        }
    </style>
    """

    landscape_ui_elements = """
    <!-- Mobile Portrait Guidance Overlay -->
    <div id="portrait-prompt">
        <div class="rotate-anim-icon">📱</div>
        <div class="prompt-title">Rotate to Landscape</div>
        <div class="prompt-desc">Quest for Aethelgard 16-Bit Edition is designed for widescreen landscape. Please turn your device horizontally for the optimal view.</div>
        <button class="btn-prompt-landscape" onclick="toggleLandscapeFullscreen()">⛶ Fullscreen Landscape</button>
        <button class="btn-prompt-dismiss" onclick="document.getElementById('portrait-prompt').style.display='none'">Continue in Portrait</button>
    </div>

    <!-- Landscape Fullscreen Toggle Button -->
    <button id="fullscreen-btn" onclick="toggleLandscapeFullscreen()" style="position:fixed; bottom:12px; left:14px; z-index:999999; background:rgba(20,24,36,0.92); color:#63b3ed; border:1px solid #4299e1; border-radius:6px; padding:7px 13px; font-family:'Segoe UI',system-ui,sans-serif; font-size:12px; font-weight:bold; cursor:pointer; box-shadow:0 3px 8px rgba(0,0,0,0.6); transition:all 0.2s;" onmouseover="this.style.background='#2c3652';this.style.borderColor='#90cdf4'" onmouseout="this.style.background='rgba(20,24,36,0.92)';this.style.borderColor='#4299e1'">⛶ Landscape Fullscreen</button>


    <!-- Landscape Orientation Locking & Resizing Script -->
    <script>
        async function lockLandscape() {
            try {
                if (screen.orientation && screen.orientation.lock) {
                    await screen.orientation.lock('landscape');
                }
            } catch (err) {}
        }

        async function toggleLandscapeFullscreen() {
            const doc = document.documentElement;
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                if (doc.requestFullscreen) {
                    await doc.requestFullscreen().catch(() => {});
                } else if (doc.webkitRequestFullscreen) {
                    await doc.webkitRequestFullscreen().catch(() => {});
                }
            } else {
                if (document.exitFullscreen) {
                    await document.exitFullscreen().catch(() => {});
                } else if (document.webkitExitFullscreen) {
                    await document.webkitExitFullscreen().catch(() => {});
                }
            }
            lockLandscape();
        }

        // Lock landscape on first user engagement (click/touch)
        window.addEventListener('click', lockLandscape, { passive: true });
        window.addEventListener('touchstart', lockLandscape, { passive: true });

        // Auto-retrigger Pygbag layout adjustment on orientation flip
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                if (typeof window_resize === 'function') {
                    window_resize();
                }
            }, 250);
        });
    </script>
    """

    if "</head>" in html:
        html = html.replace("</head>", f"{AUDIO_REJECTION_GUARD}\n{landscape_head_tags}\n{landscape_and_ui_css}\n</head>", 1)
    else:
        html += AUDIO_REJECTION_GUARD + landscape_head_tags + landscape_and_ui_css

    if "</body>" in html:
        html = html.replace("</body>", f"{landscape_ui_elements}\n</body>", 1)
    else:
        html += landscape_ui_elements

    index_file.write_text(html, encoding="utf-8")
    print("    [OK] Pygame-CE Web Edition built and patched.")


def build_pyxel_web(dist_web: Path) -> None:
    """Package Pyxel using pyxel package & app2html."""
    print("--> Packaging 8-Bit Retro Edition (Pyxel Web)...")
    ensure_assets()
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
        pyxel_html = pyxel_html.replace("<head>", f"<head>\n{AUDIO_REJECTION_GUARD}\n{pyxel_addons}", 1)
    else:
        pyxel_html = f"{AUDIO_REJECTION_GUARD}\n{pyxel_addons}\n{pyxel_html}"

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

    ensure_assets()
    build_pygame_web(dist_web)
    build_pyxel_web(dist_web)
    copy_pwa_metadata(dist_web)

    print("==================================================")
    print("SUCCESS: Dual-frontend web deployment ready in `dist/web/`!")
    print("==================================================")


if __name__ == "__main__":
    build_dual_web()
