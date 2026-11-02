"""
Regenerates the 7 status badges (keeping 'burn' and 'haste' as golden references).
Passes status_burn.png and status_haste.png to Gemini API as multimodal style references.
"""

import os
import sys
import json
import base64
import time
import urllib.request
from PIL import Image
import io

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# Load API key
API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY and os.path.exists(os.path.join(PROJECT_ROOT, ".env")):
    with open(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]

MODEL_NAME = "gemini-3.1-flash-image"

REF_BURN = os.path.join(ICONS_DIR, "status_burn.png")
REF_HASTE = os.path.join(ICONS_DIR, "status_haste.png")

BADGES_TO_REGEN = {
    "poison": "Masterpiece 16-bit SNES status effect badge: a bubbling toxic lime green chemical flask with skull emblem, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "bleed": "Masterpiece 16-bit SNES status effect badge: dripping deep crimson blood droplets with bright highlights, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "stun": "Masterpiece 16-bit SNES status effect badge: bright electric yellow lightning bolt with dizzy golden stars, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "blind": "Masterpiece 16-bit SNES status effect badge: a closed white eye with a bold red diagonal slash across it, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "fortify": "Masterpiece 16-bit SNES status effect badge: a sturdy royal blue iron tower shield with polished steel rim and blue glint, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "weaken": "Masterpiece 16-bit SNES status effect badge: a cracked broken steel sword with a downwards pointing peach-colored arrow, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
    "vulnerable": "Masterpiece 16-bit SNES status effect badge: a cracked pink-magenta armor shield with a bright target crosshair reticle, inside a square dark beveled badge with golden trim. Style must match the reference images exactly in framing, pixel grid, and square badge border. Isolated on solid pure black (#000000) background.",
}


def call_gemini_multimodal(prompt: str, ref_paths: list[str]) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    parts = []
    
    for rp in ref_paths:
        if os.path.exists(rp):
            with open(rp, "rb") as f:
                ref_bytes = f.read()
                parts.append({
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": base64.b64encode(ref_bytes).decode("utf-8")
                    }
                })
                
    parts.append({"text": prompt.strip()})
    payload = {"contents": [{"parts": parts}]}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates:
            for p in candidates[0].get("content", {}).get("parts", []):
                if "inlineData" in p:
                    return base64.b64decode(p["inlineData"]["data"])
        raise RuntimeError(f"No image data in response: {result}")


def clean_badge(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    pix = im.load()
    
    # Outer black transparency
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if r <= 25 and g <= 25 and b <= 25:
                pix[x, y] = (0, 0, 0, 0)
                
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
        
    return im.resize((24, 24), Image.Resampling.LANCZOS)


def main():
    print("--- Regenerating 7 Status Badges using Burn and Haste as visual examples ---")
    refs = [REF_BURN, REF_HASTE]
    for status_id, prompt in BADGES_TO_REGEN.items():
        out_path = os.path.join(ICONS_DIR, f"status_{status_id}.png")
        art_path = os.path.join(ARTIFACT_DIR, f"status_{status_id}.png")
        print(f"Generating badge '{status_id}' with reference examples...", flush=True)
        try:
            raw = call_gemini_multimodal(prompt, refs)
            im = Image.open(io.BytesIO(raw))
            cleaned = clean_badge(im)
            cleaned.save(out_path, "PNG", optimize=True)
            cleaned.save(art_path, "PNG", optimize=True)
            print(f"  [+] Saved: {out_path}", flush=True)
            time.sleep(1)
        except Exception as e:
            print(f"  [!] Error generating '{status_id}': {e}", flush=True)


if __name__ == "__main__":
    main()
