"""
Asset Generation Script for Class Selection Redesign.
Generates Stat Icons, Class Crests, Combat Sprites, and Bust Portraits using gemini-3.1-flash-image.
Always skips existing assets to prevent duplicate costs.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
from PIL import Image
import io

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3.1-flash-image"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
PORTRAITS_DIR = os.path.join(PROJECT_ROOT, "assets", "portraits")
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "assets", "ui_asset_manifest.json")

# Auto-load key from .env if not in environment
if not API_KEY and os.path.exists(os.path.join(PROJECT_ROOT, ".env")):
    with open(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]

os.makedirs(ICONS_DIR, exist_ok=True)
os.makedirs(SPRITES_DIR, exist_ok=True)
os.makedirs(PORTRAITS_DIR, exist_ok=True)

def call_gemini_image(prompt: str) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt.strip()}]}]}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    return base64.b64decode(p["inlineData"]["data"])
        raise RuntimeError(f"No image returned: {result}")

def clean_black_transparent(im: Image.Image, threshold: int = 25) -> Image.Image:
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

# ---------------- 1. STAT ICONS ----------------
STAT_ICONS = {
    "hp": "Masterpiece 16-bit SNES pixel art icon: bright red heart with white pixel shine and dark outline, isolated on a SOLID PURE BLACK (#000000) background. Retro JRPG UI icon, limited 16-bit palette, crisp pixel grid.",
    "atk": "Masterpiece 16-bit SNES pixel art icon: sharp silver steel sword with golden crossguard pointing diagonally, dark outline, isolated on a SOLID PURE BLACK (#000000) background. Retro JRPG UI icon, limited 16-bit palette, crisp pixel grid.",
    "def": "Masterpiece 16-bit SNES pixel art icon: blue steel knight shield with gold rim and heraldic cross, dark outline, isolated on a SOLID PURE BLACK (#000000) background. Retro JRPG UI icon, limited 16-bit palette, crisp pixel grid.",
    "spd": "Masterpiece 16-bit SNES pixel art icon: brown leather adventurer boot with white winged ankle, dark outline, isolated on a SOLID PURE BLACK (#000000) background. Retro JRPG UI icon, limited 16-bit palette, crisp pixel grid.",
    "crit": "Masterpiece 16-bit SNES pixel art icon: golden sparkling eight-point starburst critical hit flare, dark outline, isolated on a SOLID PURE BLACK (#000000) background. Retro JRPG UI icon, limited 16-bit palette, crisp pixel grid.",
}

# ---------------- 2. CLASS CRESTS ----------------
CLASS_CRESTS = {
    "crest_warrior": "Masterpiece 16-bit SNES pixel art class badge icon: silver broadsword with golden hilt inside a golden heraldic shield border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_rogue": "Masterpiece 16-bit SNES pixel art class badge icon: crossed curved steel daggers with dark leather wraps inside a silver border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_mage": "Masterpiece 16-bit SNES pixel art class badge icon: wooden wizard staff topped with glowing blue crystal orb and magical sparkles inside a gold border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_paladin": "Masterpiece 16-bit SNES pixel art class badge icon: golden winged radiant cross shield with holy light aura inside a gold border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_berserker": "Masterpiece 16-bit SNES pixel art class badge icon: crossed bloody barbarian battleaxes with spiked iron heads inside a spiked bronze border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_venomancer": "Masterpiece 16-bit SNES pixel art class badge icon: glass skull alchemy flask bubbling with glowing emerald toxic poison inside an obsidian border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_duelist": "Masterpiece 16-bit SNES pixel art class badge icon: slender fencing rapier with ornate basket hilt crossed with small parrying dagger inside an ornate gold border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_archmage": "Masterpiece 16-bit SNES pixel art class badge icon: floating open arcane spellbook with glowing cosmic starlight orb and runes inside an ethereal violet border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
    "crest_warlock": "Masterpiece 16-bit SNES pixel art class badge icon: demonic horned skull with purple dark flame eye inside a spiked blood-red border, dark outline, isolated on a SOLID PURE BLACK (#000000) background. 16-bit JRPG UI crest.",
}

# ---------------- 3. FULL BODY SPRITES ON PEDESTAL ----------------
SPRITE_PROMPTS = {
    "warrior": "Full-body 16-bit SNES pixel art character sprite: brave young blonde spiky-haired male warrior standing in proud battle stance on a circular carved stone pedestal. Wearing polished steel breastplate, blue tunic, crimson cape, holding an upright silver broadsword. Golden age 1990s JRPG style (Secret of Evermore, Terranigma). Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art, crisp pixel grid, no vector, no 3D.",
    "rogue": "Full-body 16-bit SNES pixel art character sprite: nimble agile hooded rogue standing in low stealth stance on a circular carved stone pedestal. Wearing dark cowl hood with yellow glowing eyes in deep shadow, dark charcoal leather armor, red scarf, holding two sharp curved daggers. Golden age 1990s JRPG style (Secret of Evermore, Terranigma). Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art, crisp pixel grid.",
    "mage": "Full-body 16-bit SNES pixel art character sprite: mystical young lavender-haired female mage standing on a circular carved stone pedestal. Wearing purple pointed wizard hat with star buckle, purple wizard robe, holding tall wooden staff topped with glowing turquoise crystal orb. Golden age 1990s JRPG style (Secret of Evermore, Terranigma). Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art, crisp pixel grid.",
    "paladin": "Full-body 16-bit SNES pixel art character sprite: towering holy paladin knight in radiant gold-trimmed steel plate armor with winged helmet, flowing pure white cape, holding a massive golden heraldic tower shield and glowing longsword on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "berserker": "Full-body 16-bit SNES pixel art character sprite: ferocious barbarian berserker with wild spiky mane, red war paint, dark fur mantle, spiked iron bracers, dual wielding heavy broad battleaxes on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "venomancer": "Full-body 16-bit SNES pixel art character sprite: sinister masked poisoner assassin in dark green and obsidian leather vestments, bandolier of glowing emerald venom vials, wielding jagged poisoned kris daggers on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "duelist": "Full-body 16-bit SNES pixel art character sprite: dashing aristocratic master fencer in deep crimson tailored doublet, white lace cravat, cavalier hat with peacock feather, holding an elegant silver rapier poised to thrust on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "archmage": "Full-body 16-bit SNES pixel art character sprite: grand high sorceress in celestial midnight blue and gold robes adorned with star constellations, floating hovering arcane glyphs, holding an ornate celestial star staff on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "warlock": "Full-body 16-bit SNES pixel art character sprite: dark occult warlock in ragged black and purple robes, horned shadow cowl, holding a floating chained necrotic grimoire with dark purple flame swirling around his hand on a circular carved stone pedestal. Golden age 1990s JRPG style. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
}

# ---------------- 4. BUST PORTRAITS ----------------
PORTRAIT_PROMPTS = {
    "warrior": "16-bit SNES pixel art character bust portrait (head and shoulders): determined young blonde male warrior with spiky anime hair, bright blue eyes, wearing silver steel gorget and red cape collar. Three-quarter view facing slightly right. 1990s golden age JRPG portrait (Secret of Evermore, Terranigma, Chrono Trigger). Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art, crisp pixels.",
    "rogue": "16-bit SNES pixel art character bust portrait (head and shoulders): mysterious hooded rogue with glowing yellow eyes peering out from beneath deep black shadow cowl, red scarf wrapped around lower face, dark leather pauldron. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "mage": "16-bit SNES pixel art character bust portrait (head and shoulders): charming mystical young female mage with flowing lavender hair, soft confident expression, wearing dark purple pointed wizard hat with star buckle and gold trim. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "paladin": "16-bit SNES pixel art character bust portrait (head and shoulders): noble holy knight with golden circlet or winged helmet, calm resolute expression, polished golden pauldron and white mantle. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "berserker": "16-bit SNES pixel art character bust portrait (head and shoulders): battle-scarred fierce barbarian warrior with wild dark hair, piercing amber eyes, crimson war paint across nose, fur collar. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "venomancer": "16-bit SNES pixel art character bust portrait (head and shoulders): calculating sinister assassin with dark teal hood, cloth face mask, cold piercing green eyes, faint toxic glow. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "duelist": "16-bit SNES pixel art character bust portrait (head and shoulders): handsome dashing swordsman with stylish swept-back hair, confident smirk, cavalier hat with sweeping feather, ornate crimson collar. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "archmage": "16-bit SNES pixel art character bust portrait (head and shoulders): serene high sorceress with glowing celestial violet eyes, silver tiara with sapphire gem, deep indigo mantle adorned with gold constellations. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
    "warlock": "16-bit SNES pixel art character bust portrait (head and shoulders): pale dark warlock with shadowed gaunt face, sinister knowing smile, obsidian horned crown, dark purple necrotic aura. 1990s golden age JRPG portrait. Isolated on a SOLID PURE BLACK (#000000) background. Pure pixel art.",
}

def generate_asset_group(group_name: str, item_dict: dict[str, str], out_dir: str, target_size: tuple[int, int] | None = None):
    print(f"\n--- Generating {group_name} ({len(item_dict)} items) ---", flush=True)
    for key, prompt in item_dict.items():
        out_path = os.path.join(out_dir, f"{key}.png")
        if os.path.exists(out_path):
            print(f"[=] Skipping {key} (already exists: {out_path})", flush=True)
            continue
        print(f"[+] Generating 16-bit asset '{key}'...", flush=True)
        try:
            raw_bytes = call_gemini_image(prompt)
            im = Image.open(io.BytesIO(raw_bytes))
            im_clean = clean_black_transparent(im, threshold=30)
            if target_size:
                im_clean = im_clean.resize(target_size, Image.Resampling.LANCZOS)
            im_clean.save(out_path, "PNG")
            print(f"    Saved to: {out_path} ({im_clean.size})", flush=True)
        except Exception as e:
            print(f"    [!] Error generating '{key}': {e}", flush=True)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if target in ("all", "icons"):
        generate_asset_group("Stat Icons", STAT_ICONS, ICONS_DIR, target_size=(24, 24))
    if target in ("all", "crests"):
        generate_asset_group("Class Crests", CLASS_CRESTS, ICONS_DIR, target_size=(32, 32))
    if target in ("all", "sprites"):
        generate_asset_group("Combat Sprites", SPRITE_PROMPTS, SPRITES_DIR)
    if target in ("all", "portraits"):
        generate_asset_group("Bust Portraits", PORTRAIT_PROMPTS, PORTRAITS_DIR)

if __name__ == "__main__":
    main()
