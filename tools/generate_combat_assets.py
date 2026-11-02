"""
Asset Generation Script for Combat View Redesign.
Generates:
1. Status Badges (9 badges, 24x24 / 32x32 transparent PNGs)
2. Combat Arena Backgrounds (6 biomes with foreground battle stage)
3. Enemy Combat Sprites (48 enemies, strictly facing LEFT, transparent PNGs)
"""

import os
import sys
import json
import base64
import time
import urllib.request
import urllib.error
from PIL import Image
import io

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.data.enemies import ENEMY_CATALOG

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3.1-flash-image"

# Auto-load key from .env if not in environment
if not API_KEY and os.path.exists(os.path.join(PROJECT_ROOT, ".env")):
    with open(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]

STATUS_ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
BACKGROUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "backgrounds")
ENEMIES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites", "enemies")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

os.makedirs(STATUS_ICONS_DIR, exist_ok=True)
os.makedirs(BACKGROUNDS_DIR, exist_ok=True)
os.makedirs(ENEMIES_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)


def call_gemini_image(prompt: str, reference_image_path: str | None = None, max_retries: int = 3) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    parts = []
    
    if reference_image_path and os.path.exists(reference_image_path):
        with open(reference_image_path, "rb") as f:
            ref_bytes = f.read()
            mime = "image/png" if reference_image_path.endswith(".png") else "image/jpeg"
            parts.append({
                "inlineData": {
                    "mimeType": mime,
                    "data": base64.b64encode(ref_bytes).decode("utf-8")
                }
            })
            
    parts.append({"text": prompt.strip()})
    payload = {"contents": [{"parts": parts}]}
    data = json.dumps(payload).encode("utf-8")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    for p in candidates[0].get("content", {}).get("parts", []):
                        if "inlineData" in p:
                            return base64.b64decode(p["inlineData"]["data"])
                raise RuntimeError(f"No image data in response: {result}")
        except urllib.error.HTTPError as e:
            print(f"    [!] HTTP {e.code} on attempt {attempt + 1}: {e.reason}", flush=True)
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
            else:
                time.sleep(2)
        except Exception as e:
            print(f"    [!] Error on attempt {attempt + 1}: {e}", flush=True)
            time.sleep(2)

    raise RuntimeError(f"Failed to generate image after {max_retries} attempts.")


def clean_black_transparent(im: Image.Image, threshold: int = 30) -> Image.Image:
    """Make solid black background transparent and crop tightly."""
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


# ---------------------------------------------------------
# STATUS BADGES
# ---------------------------------------------------------
STATUS_PROMPTS = {
    "burn": "Masterpiece 16-bit SNES pixel art status badge icon: roaring vibrant orange-yellow flame fire symbol, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "poison": "Masterpiece 16-bit SNES pixel art status badge icon: bubbling bright toxic lime green potion vial with skull emblem, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "bleed": "Masterpiece 16-bit SNES pixel art status badge icon: deep crimson red blood droplet with dripping splatter, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "stun": "Masterpiece 16-bit SNES pixel art status badge icon: bright yellow lightning bolt and dizzy spiral stars, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "blind": "Masterpiece 16-bit SNES pixel art status badge icon: closed white eye with bold red diagonal slash across it, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "fortify": "Masterpiece 16-bit SNES pixel art status badge icon: sturdy royal blue iron kite shield with shining steel trim, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "haste": "Masterpiece 16-bit SNES pixel art status badge icon: glowing cyan winged runner boot with motion speed trails, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "weaken": "Masterpiece 16-bit SNES pixel art status badge icon: cracked shattered steel sword blade with downwards pointing peach arrow, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
    "vulnerable": "Masterpiece 16-bit SNES pixel art status badge icon: cracked pink shield with crosshair target reticle, inside a crisp square badge icon with dark border, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid, high contrast, 16-bit color palette.",
}


# ---------------------------------------------------------
# BELT ITEM & ABILITY ICONS
# ---------------------------------------------------------
ITEM_PROMPTS = {
    "potion_health": "Masterpiece 16-bit SNES pixel art icon: round glass potion bottle with glowing bright crimson red healing elixir and cork stopper, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid.",
    "potion_mana": "Masterpiece 16-bit SNES pixel art icon: round glass potion bottle with glowing vibrant cyan blue magical mana elixir and cork stopper, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid.",
    "herb": "Masterpiece 16-bit SNES pixel art icon: green medicinal herbal sprig with three fresh leaves and brown stem, isolated on SOLID PURE BLACK (#000000) background. Retro Super Nintendo JRPG UI icon, crisp pixel grid.",
}

def generate_item_icons():
    print("\n--- Generating Belt Item Icons ---", flush=True)
    for item_id, prompt in ITEM_PROMPTS.items():
        out_path = os.path.join(STATUS_ICONS_DIR, f"item_{item_id}.png")
        art_path = os.path.join(ARTIFACT_DIR, f"item_{item_id}.png")
        if os.path.exists(out_path):
            print(f"  [=] Skipping existing item icon '{item_id}'", flush=True)
            continue

        print(f"  [+] Generating item icon '{item_id}'...", flush=True)
        raw_bytes = call_gemini_image(prompt)
        im = Image.open(io.BytesIO(raw_bytes))
        im = clean_black_transparent(im, threshold=30)
        im = im.resize((32, 32), Image.Resampling.LANCZOS)
        im.save(out_path, "PNG", optimize=True)
        im.save(art_path, "PNG", optimize=True)
        print(f"      Saved: {out_path}", flush=True)

# ---------------------------------------------------------
ARENA_PROMPTS = {
    "arboretum": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Secret of Evermore, Chrono Trigger, Terranigma). "
        "A ruined Victorian gothic botanical glasshouse combat arena. "
        "In the lower foreground, an ancient weathered cobblestone garden courtyard floor where combatants stand in battle. "
        "In the midground and background, soaring arched wrought-iron glasshouse frames choked with twisted briar vines, glowing cyan bioluminescent mushrooms, and giant toxic ferns under a misty starry night sky. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with emerald greens, bioluminescent cyan, and dark stone. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
    "cathedral": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Terranigma, Super Castlevania IV). "
        "A desecrated gothic cathedral combat arena. "
        "In the lower foreground, a cracked flagstone nave floor where fighters duel. "
        "In the midground and background, soaring ribbed stone vaults, cracked gothic arches, shattered stained-glass rose windows letting in cold silver moonlight, and tall wrought-iron candelabras with flickering purple candlelight. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with deep obsidian blues, cold stone grays, and eerie purple candle flames. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
    "ossuary": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Secret of Evermore underworld). "
        "A subterranean gothic catacomb and drowned ossuary combat arena. "
        "In the lower foreground, a wide wet stone platform raised slightly above dark murky brine where combatants stand. "
        "In the midground and background, crypt walls stacked high with human skulls and ribcages, ancient stone sarcophagi, and cold pale cyan water reflections dancing on ancient arches. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with murky teals, bone-whites, and deep shadows. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
    "foundry": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Chrono Trigger, Secret of Evermore). "
        "An infernal underground industrial foundry of torment combat arena. "
        "In the lower foreground, a sturdy blackened iron battle platform above glowing embers. "
        "In the midground and background, rivers and vats of glowing molten orange iron, massive rusted iron cogwheels, heavy iron chains, and billowing smoke under high vaulted stone ceilings. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with blazing magma orange, fiery yellows, soot blacks, and rusted metals. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
    "observatory": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Chrono Trigger, Terranigma). "
        "A mystical celestial astral observatory combat arena. "
        "In the lower foreground, an ancient circular marble dais inscribed with zodiac runes where fighters stand. "
        "In the midground and background, an open gothic domed observatory looking out into a breathtaking cosmic starry void, with glowing spiral galaxies, starlight rifts, and floating astral orbs. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with cosmic indigos, violet nebulae, and shining silver stars. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
    "sanctum": (
        "Masterpiece 16-bit SNES pixel art video game battle arena background, 1990s golden age Super Nintendo RPG style (Castlevania, Secret of Evermore). "
        "A dark crimson blood sanctum and vampiric throne hall combat arena. "
        "In the lower foreground, a polished obsidian marble floor inlaid with glowing crimson runes where combatants clash. "
        "In the midground and background, towering gothic pillars draped in velvet crimson banners, gargoyle braziers with blood-red flames, and massive gothic arched windows overlooking an ominous blood moon. "
        "Visible handcrafted pixel clusters, dithering, rich 16-bit color palette with deep blood crimsons, obsidian blacks, and eerie red mist. 16:9 widescreen landscape. "
        "NO characters, NO monsters, NO UI elements, NO text, NO logos. Clean empty combat battle arena stage."
    ),
}


def generate_status_badges():
    print("\n--- Generating 9 Status Badges ---", flush=True)
    for status_id, prompt in STATUS_PROMPTS.items():
        out_path = os.path.join(STATUS_ICONS_DIR, f"status_{status_id}.png")
        art_path = os.path.join(ARTIFACT_DIR, f"status_{status_id}.png")
        if os.path.exists(out_path):
            print(f"  [=] Skipping existing badge '{status_id}'", flush=True)
            continue

        print(f"  [+] Generating badge '{status_id}'...", flush=True)
        raw_bytes = call_gemini_image(prompt)
        im = Image.open(io.BytesIO(raw_bytes))
        im = clean_black_transparent(im, threshold=30)
        im = im.resize((24, 24), Image.Resampling.LANCZOS)
        im.save(out_path, "PNG", optimize=True)
        im.save(art_path, "PNG", optimize=True)
        print(f"      Saved: {out_path}", flush=True)


def generate_arena_backgrounds():
    print("\n--- Generating 6 Combat Arena Backgrounds ---", flush=True)
    for biome_id, prompt in ARENA_PROMPTS.items():
        out_path = os.path.join(BACKGROUNDS_DIR, f"combat_{biome_id}.png")
        art_path = os.path.join(ARTIFACT_DIR, f"combat_{biome_id}.png")
        ref_path = os.path.join(BACKGROUNDS_DIR, f"{biome_id}.png")
        if os.path.exists(out_path):
            print(f"  [=] Skipping existing arena background '{biome_id}'", flush=True)
            continue

        print(f"  [+] Generating arena background for '{biome_id}' (ref: {ref_path})...", flush=True)
        raw_bytes = call_gemini_image(prompt, reference_image_path=ref_path if os.path.exists(ref_path) else None)
        im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        im = im.resize((960, 540), Image.Resampling.LANCZOS)
        im.save(out_path, "PNG", optimize=True)
        im.save(art_path, "PNG", optimize=True)
        print(f"      Saved: {out_path}", flush=True)


def generate_enemy_sprites(target_id: str | None = None, act: int | None = None):
    print("\n--- Generating Enemy Combat Sprites (Facing LEFT) ---", flush=True)
    all_keys = list(ENEMY_CATALOG.keys())
    
    if target_id:
        enemies_to_gen = [target_id]
    elif act:
        # 8 enemies per act
        start_idx = (act - 1) * 8
        enemies_to_gen = all_keys[start_idx:start_idx + 8]
    else:
        enemies_to_gen = all_keys

    print(f"Targeting {len(enemies_to_gen)} enemies...", flush=True)

    for enemy_id in enemies_to_gen:
        if enemy_id not in ENEMY_CATALOG:
            print(f"  [!] Unknown enemy '{enemy_id}', skipping", flush=True)
            continue

        arch = ENEMY_CATALOG[enemy_id]
        out_path = os.path.join(ENEMIES_DIR, f"{enemy_id}.png")
        art_path = os.path.join(ARTIFACT_DIR, f"enemy_{enemy_id}.png")
        if os.path.exists(out_path):
            print(f"  [=] Skipping existing enemy sprite '{enemy_id}'", flush=True)
            continue

        prompt = (
            f"Masterpiece 16-bit SNES pixel art video game battle monster sprite of '{arch.name}': {arch.description}. "
            "Classic 1990s Super Nintendo JRPG monster battle sprite (Final Fantasy VI, Chrono Trigger, Secret of Evermore). "
            "Full body combat monster sprite strictly FACING LEFT (profile or three-quarter facing towards the left side of the screen). "
            "Dynamic menacing combat pose. Handcrafted pixel art, crisp pixel grid, rich 16-bit retro color palette, dark outline. "
            "Isolated on a SOLID PURE BLACK (#000000) background. "
            "NO ground tiles, NO floor shadow, NO background scenery, NO UI, NO text, ONLY the single monster sprite."
        )

        print(f"  [+] Generating sprite for '{enemy_id}' ({arch.name})...", flush=True)
        try:
            raw_bytes = call_gemini_image(prompt)
            im = Image.open(io.BytesIO(raw_bytes))
            im = clean_black_transparent(im, threshold=30)
            
            # Maintain aspect ratio, max dimension 160px for rich SNES detail
            max_dim = 160
            w, h = im.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)

            im.save(out_path, "PNG", optimize=True)
            im.save(art_path, "PNG", optimize=True)
            print(f"      Saved: {out_path} ({im.size})", flush=True)
        except Exception as e:
            print(f"      [!] Error generating '{enemy_id}': {e}", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "badges"):
        generate_status_badges()
    if mode in ("all", "items"):
        generate_item_icons()
    if mode in ("all", "arenas"):
        generate_arena_backgrounds()
    if mode in ("all", "enemies"):
        act_arg = None
        target_arg = None
        if len(sys.argv) > 2:
            arg = sys.argv[2]
            if arg.startswith("act"):
                act_arg = int(arg[3:])
            else:
                target_arg = arg
        generate_enemy_sprites(target_id=target_arg, act=act_arg)
