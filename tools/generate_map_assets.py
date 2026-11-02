"""
Map Asset Generator for Biome Icons and Node Icons using gemini-3.1-flash-image.
Passes existing biome background images to Gemini as multimodal reference.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import io
from PIL import Image

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3.1-flash-image"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
BACKGROUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "backgrounds")
os.makedirs(ICONS_DIR, exist_ok=True)

# Auto-load key from .env if not in environment
if not API_KEY and os.path.exists(os.path.join(PROJECT_ROOT, ".env")):
    with open(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]

def call_gemini_multimodal(prompt: str, ref_image_path: str | None = None) -> bytes:
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set!")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    parts = []
    
    if ref_image_path and os.path.exists(ref_image_path):
        with Image.open(ref_image_path) as ref_im:
            ref_thumb = ref_im.copy()
            ref_thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            ref_thumb.save(buf, format="JPEG", quality=85)
            b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": b64_data
                }
            })
            
    parts.append({"text": prompt.strip()})
    
    payload = {"contents": [{"parts": parts}]}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates:
            res_parts = candidates[0].get("content", {}).get("parts", [])
            for p in res_parts:
                if "inlineData" in p:
                    return base64.b64decode(p["inlineData"]["data"])
        raise RuntimeError(f"No image returned: {result}")

def clean_black_transparent(im: Image.Image, threshold: int = 25) -> Image.Image:
    im = im.convert("RGBA")
    pix = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if r <= threshold and g <= threshold and b <= threshold:
                pix[x, y] = (0, 0, 0, 0)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im

def clean_solid_background(im: Image.Image, corner_tol: int = 30) -> Image.Image:
    """Flood-fill or corner-sample background removal for solid backgrounds."""
    im = im.convert("RGBA")
    w, h = im.size
    corners = [im.getpixel((0, 0)), im.getpixel((w - 1, 0)), im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1))]
    # Check if corners are near black
    avg_corner = [sum(c[i] for c in corners) // 4 for i in range(3)]
    pix = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if all(abs(pix[x, y][i] - avg_corner[i]) <= corner_tol for i in range(3)):
                pix[x, y] = (0, 0, 0, 0)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im

BIOMES = {
    "arboretum": {
        "name": "The Wilted Arboretum",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: glowing bioluminescent fungal spore pod with thorny briar vines and glowing cyan mushrooms, matching the provided conservatory background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon (Secret of Evermore, Terranigma, Chrono Trigger), crisp pixel grid, high contrast.",
        "bg": "arboretum.png"
    },
    "cathedral": {
        "name": "The Desecrated Cathedral",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: gothic stained glass vaulted window arch with candelabra and purple sacred flame, matching the provided cathedral background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon, crisp pixel grid, high contrast.",
        "bg": "cathedral.png"
    },
    "ossuary": {
        "name": "The Drowned Ossuary",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: sunken ancient skull covered in barnacles and briny dark waters, matching the provided flooded ossuary background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon, crisp pixel grid, high contrast.",
        "bg": "ossuary.png"
    },
    "foundry": {
        "name": "The Foundry of Torment",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: glowing molten metal crucible, fiery forge anvil and brass mechanical gears, matching the provided foundry background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon, crisp pixel grid, high contrast.",
        "bg": "foundry.png"
    },
    "observatory": {
        "name": "The Astral Observatory",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: celestial brass astrolabe armillary sphere with glowing starry cosmos and orbiting constellation ring, matching the provided observatory background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon, crisp pixel grid, high contrast.",
        "bg": "observatory.png"
    },
    "sanctum": {
        "name": "The Blood Sanctum",
        "prompt": "Masterpiece 16-bit SNES pixel art biome icon: ornate gothic vampire chalice goblet overflowing with crimson blood with bat wings sigil, matching the provided blood sanctum background. Isolated on a SOLID PURE BLACK (#000000) background. Retro 16-bit JRPG UI badge icon, crisp pixel grid, high contrast.",
        "bg": "sanctum.png"
    }
}

NODES = {
    "combat": "Masterpiece 16-bit SNES pixel art map node icon: circular crimson-red medallion with golden rim, containing crossed silver combat swords with golden hilts. Golden age 1990s JRPG map node (Secret of Evermore, Chrono Trigger). Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "event": "Masterpiece 16-bit SNES pixel art map node icon: circular royal-purple medallion with golden rim, containing a glowing mystical question mark symbol '?'. Golden age 1990s JRPG map node. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "rest": "Masterpiece 16-bit SNES pixel art map node icon: circular dark-teal medallion with golden rim, containing a cozy green traveler bed / camp cot. Golden age 1990s JRPG map node. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "elite": "Masterpiece 16-bit SNES pixel art map node icon: circular deep violet medallion with golden rim, containing a menacing horned demon skull with glowing lavender eyes. Golden age 1990s JRPG map node. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "treasure": "Masterpiece 16-bit SNES pixel art map node icon: circular dark amber medallion with golden rim, containing an ornate golden treasure chest with jeweled latch. Golden age 1990s JRPG map node. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "shop": "Masterpiece 16-bit SNES pixel art map node icon: circular warm bronze medallion with golden rim, containing a brown leather merchant money pouch with gold coins spilling out. Golden age 1990s JRPG map node. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, clear circular emblem.",
    "boss": "Masterpiece 16-bit SNES pixel art map node icon: large radiant golden ornate royal boss crest with a majestic golden crown with rubies inside a winged sunburst medallion. Golden age 1990s JRPG boss icon. Isolated on a SOLID PURE BLACK (#000000) background. Crisp pixel art, triumphant ornate crown seal."
}

def generate_biomes():
    print("--- Generating Biome Icons (6 items) ---", flush=True)
    for b_id, data in BIOMES.items():
        out_path = os.path.join(ICONS_DIR, f"biome_{b_id}.png")
        if os.path.exists(out_path):
            print(f"[=] Skipping biome_{b_id} (already exists)", flush=True)
            continue
        bg_path = os.path.join(BACKGROUNDS_DIR, data["bg"])
        print(f"[+] Generating biome_{b_id} using background '{data['bg']}'...", flush=True)
        try:
            raw = call_gemini_multimodal(data["prompt"], bg_path)
            im = Image.open(io.BytesIO(raw))
            im_clean = clean_black_transparent(im, threshold=30)
            im_clean.save(out_path, "PNG")
            print(f"    Saved: {out_path} ({im_clean.size})", flush=True)
        except Exception as e:
            print(f"    [!] Error generating biome_{b_id}: {e}", flush=True)

def generate_nodes():
    print("--- Generating Node Icons (7 items) ---", flush=True)
    for n_id, prompt in NODES.items():
        out_path = os.path.join(ICONS_DIR, f"node_{n_id}.png")
        if os.path.exists(out_path):
            print(f"[=] Skipping node_{n_id} (already exists)", flush=True)
            continue
        print(f"[+] Generating node_{n_id}...", flush=True)
        try:
            raw = call_gemini_multimodal(prompt, None)
            im = Image.open(io.BytesIO(raw))
            im_clean = clean_black_transparent(im, threshold=30)
            im_clean.save(out_path, "PNG")
            print(f"    Saved: {out_path} ({im_clean.size})", flush=True)
        except Exception as e:
            print(f"    [!] Error generating node_{n_id}: {e}", flush=True)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "biomes"):
        generate_biomes()
    if mode in ("all", "nodes"):
        generate_nodes()
