"""
SNES Golden Age RPG Native Pixel Art Asset Generator.
Generates authentic 16-bit pixel art backgrounds directly using Gemini API.
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
# Always use the most economical Flash model to minimize costs / utilize free tier
MODEL_NAME = "gemini-3.1-flash-image"
FALLBACK_MODEL = "gemini-2.5-flash-image"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "backgrounds")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

PROMPTS = {
    "welcome": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Secret of Evermore, Terranigma, and Super Castlevania IV. "
        "A dramatic moonlit duel in the courtyard of an ancient crumbling gothic fortress under a gigantic ominous blood moon. "
        "On decaying stone stairs, a heroic lone warrior with a broadsword faces an ancient crowned lich king holding a staff with cold necrotic turquoise flames. "
        "Towering gothic spires, weeping gargoyles, creeping low ground fog, crumbling parapets, and dark stormy sky. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, 16-bit color palette with deep obsidian blues, cold stone grays, "
        "blood-crimson highlights, and glowing turquoise magic. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector illustration, no 3D rendering, no smooth digital brushstrokes, no text, no title logos, no game HUD."
    ),
    "cathedral": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Terranigma and Secret of Evermore. "
        "Interior of a ruined, desecrated gothic cathedral. Soaring ribbed stone vaults with cracks, shattered stained glass rose windows "
        "letting in pale silver moonlight and deep midnight blue mist. Crumbling stone pillars, statues of weeping saints in niches, "
        "flickering gothic candelabras with purple and blue flames along the nave. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette, deep gothic shadows, "
        "pale stone highlights, eerie purple candlelight. 16:9 widescreen landscape. "
        "Pure pixel art, no smooth vector art, no 3D rendering, no modern digital brushstrokes, no text, no HUD, no characters."
    ),
    "arboretum": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Secret of Evermore and Terranigma. "
        "Interior of a wilted, ruined Victorian gothic botanical glasshouse and arboretum. "
        "Twisted poisonous thorn-vines choking ornate wrought-iron glass arches. Giant bioluminescent mushrooms and glowing toxic flora, "
        "shattered glass ceiling panels open to a stormy night sky, eerie glowing emerald-green and turquoise spores floating in misty air. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette, deep jungle shadows, "
        "vivid emerald green and bioluminescent cyan highlights. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "ossuary": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Terranigma underworld and Secret of Evermore. "
        "A subterranean gothic catacomb and drowned ossuary flooded with still, dark murky brine. "
        "Ancient crumbling gothic stone arches, crypt walls completely lined and stacked with thousands of human skulls and bone ribcages. "
        "Half-submerged ancient stone sarcophagi resting in the dark water with gentle ripples. "
        "Cold cyan and eerie teal magical water reflections, deep navy blue shadows, murky moss-green and bone-white highlights. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "foundry": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Secret of Evermore and Chrono Trigger. "
        "An infernal underground industrial foundry of torment. "
        "Rivers and vats of glowing molten orange iron, massive rusted iron cogwheels and heavy chains hanging from high vaulted stone ceilings. "
        "Towering blast furnaces spewing dark smoke, glowing orange embers and sparks floating in the air against dark iron walls. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette with blazing magma oranges, "
        "smoldering yellows, and deep charred iron blacks. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "observatory": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Terranigma and Chrono Trigger. "
        "An ancient astral observatory atop a shattered gothic spire open to the infinite cosmos. "
        "Giant ornate brass and gold astrolabes, armillary spheres, and celestial telescopes. "
        "A breathtaking sky of swirling cosmic purple, indigo, and violet nebulae, star clusters, and spatial rifts. "
        "Polished black obsidian floor reflecting the glittering celestial starscape. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette, deep space indigos, "
        "glowing violet starlight, and shimmering brass. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "sanctum": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Super Castlevania IV and Secret of Evermore. "
        "A decadent, gothic vampire palace throne room and blood sanctum. "
        "Soaring gothic stone arches with gilded gold filigree, opulent blood-crimson velvet drapery and banners. "
        "A massive ornate gothic throne on an elevated stone dais, tall candelabras with burning candles, polished dark marble pillars. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette, deep vampire crimson reds, "
        "antique gold, and brooding gothic shadows. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "shop": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Secret of Evermore and Terranigma. "
        "A cozy, mysterious wandering merchant shop and apothecary tucked inside an ancient underground stone vault. "
        "A rustic wooden merchant counter lined with colorful glowing glass potion vials, alchemical jars, scrolls, and scales. "
        "Hanging dried herbs, glowing candle lanterns casting warm amber light on stacked wooden crates, barrels, and burlap sacks. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette with warm amber wood tones, "
        "glowing turquoise, ruby, and violet potion fluids, and deep cozy shadows. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    ),
    "rest": (
        "Masterpiece 16-bit SNES pixel art video game background, 1990s golden age Super Nintendo RPG aesthetic "
        "inspired by Secret of Evermore and Chrono Trigger. "
        "A quiet campfire rest site and sanctuary inside a weathered stone cloister alcove. "
        "A crackling campfire with dancing orange and yellow embers casting warm, comforting light on ancient carved stone runes and pillars. "
        "Bedrolls, resting supplies, and a small iron pot over the fire, with gentle smoke curling up toward moonlit stone arches. "
        "Handcrafted pixel art, visible pixel clusters, retro dithering, rich 16-bit color palette with warm glowing firelight, "
        "amber tones, and deep calming night shadows. 16:9 widescreen landscape. "
        "Pure pixel art, no modern vector art, no 3D rendering, no smooth digital brushstrokes, no text, no HUD, no characters."
    )
}

def generate_image(prompt: str, model: str = MODEL_NAME) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt.strip()}
                ]
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        return base64.b64decode(part["inlineData"]["data"])
            raise RuntimeError(f"No inlineData found in response: {result}")
    except urllib.error.HTTPError as e:
        if model != FALLBACK_MODEL:
            print(f"Model {model} failed with {e.code}, trying fallback {FALLBACK_MODEL}...")
            return generate_image(prompt, model=FALLBACK_MODEL)
        raise

def main():
    target_asset = sys.argv[1] if len(sys.argv) > 1 else None
    
    items = [(target_asset, PROMPTS[target_asset])] if target_asset else list(PROMPTS.items())
    
    print(f"Beginning direct 16-bit SNES asset generation with economical model '{MODEL_NAME}' for {len(items)} background(s)...", flush=True)
    for name, prompt in items:
        artifact_path = os.path.join(ARTIFACT_DIR, f"snes_native_{name}.png")
        if not target_asset and os.path.exists(artifact_path):
            print(f"\n[=] Skipping '{name}' (already generated in {artifact_path}).", flush=True)
            continue

        print(f"\n[+] Generating authentic SNES pixel art for '{name}'...", flush=True)
        try:
            raw_bytes = generate_image(prompt)
            # Process with PIL to ensure 960x540 aspect ratio while preserving pixel art sharpness
            im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
            
            # High-fidelity resize to 960x540
            im_resized = im.resize((960, 540), Image.Resampling.LANCZOS)
            
            # Destination path
            dest_path = os.path.join(OUTPUT_DIR, f"{name}.png")
            im_resized.save(dest_path, "PNG", optimize=True)
            print(f"    Saved asset to: {dest_path} ({os.path.getsize(dest_path)} bytes)", flush=True)
            
            # Save copy to brain artifact dir
            im_resized.save(artifact_path, "PNG", optimize=True)
            print(f"    Artifact copy: {artifact_path}", flush=True)
            
        except Exception as e:
            print(f"    [!] Error generating '{name}': {e}", flush=True)

if __name__ == "__main__":
    main()
