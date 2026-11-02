import os
import sys
import io
from PIL import Image
from tools.generate_map_assets import call_gemini_multimodal, clean_black_transparent, ICONS_DIR, BACKGROUNDS_DIR

bg_path = os.path.join(BACKGROUNDS_DIR, "ossuary.png")
prompt = (
    "Masterpiece 16-bit SNES pixel art circular emblem icon: ancient weathered drowned skull resting on ocean catacomb stones, "
    "surrounded by dark briny water and sea barnacles, inside an ornate weathered bone and stone circular medallion. "
    "Golden age 1990s JRPG UI icon (Secret of Evermore, Chrono Trigger). "
    "NO RECTANGLE, NO CARD, NO BORDER FRAME, NO WHITE BOX. "
    "Isolated on a SOLID PURE BLACK (#000000) background. High contrast, crisp 16-bit pixel art."
)

raw = call_gemini_multimodal(prompt, bg_path)
im = Image.open(io.BytesIO(raw))
im_clean = clean_black_transparent(im, threshold=30)
out_path = os.path.join(ICONS_DIR, "biome_ossuary.png")
im_clean.save(out_path, "PNG")
print("Regenerated biome_ossuary successfully!", im_clean.size)
