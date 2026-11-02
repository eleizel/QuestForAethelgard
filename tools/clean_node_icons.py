"""
Clean and normalize node icons into crisp circular medallions with transparent backgrounds.
"""

import os
from PIL import Image, ImageDraw

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# Target icon size for gameplay & UI
TARGET_SIZE = (48, 48)

def clean_circle_icon(in_path: str, center_xy: tuple[int, int], radius: int) -> Image.Image:
    im = Image.open(in_path).convert("RGBA")
    cx, cy = center_xy
    # Crop to bounding square
    crop_box = (cx - radius, cy - radius, cx + radius, cy + radius)
    im_cropped = im.crop(crop_box)
    
    # Create smooth circular mask
    mask = Image.new("L", im_cropped.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, im_cropped.width - 1, im_cropped.height - 1), fill=255)
    
    im_cropped.putalpha(mask)
    return im_cropped

def process_all_nodes():
    results = {}
    
    # 1. node_combat: cx = (363 + 1044)//2 = 703, cy = (35 + 727)//2 = 381, radius ~ 335
    results["node_combat"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_combat.png"),
        center_xy=(703, 381),
        radius=335
    )
    
    # 2. node_event: cx = (410 + 997)//2 = 703, cy = (93 + 680)//2 = 386, radius ~ 290
    results["node_event"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_event.png"),
        center_xy=(703, 386),
        radius=290
    )
    
    # 3. node_rest: already 634x634 square, cx=317, cy=317, radius=310
    results["node_rest"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_rest.png"),
        center_xy=(317, 317),
        radius=310
    )
    
    # 4. node_elite: cx=306, cy=308, radius=300
    results["node_elite"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_elite.png"),
        center_xy=(306, 308),
        radius=300
    )
    
    # 5. node_treasure: cx = (440 + 967)//2 = 703, cy = (123 + 644)//2 = 383, radius ~ 258
    results["node_treasure"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_treasure.png"),
        center_xy=(703, 383),
        radius=258
    )
    
    # 6. node_shop: medallion center is at cx=704, cy=384, radius ~ 275
    results["node_shop"] = clean_circle_icon(
        os.path.join(ICONS_DIR, "node_shop.png"),
        center_xy=(704, 384),
        radius=275
    )
    
    # 7. node_boss: keep full shape with wings, just clean black/alpha
    im_boss = Image.open(os.path.join(ICONS_DIR, "node_boss.png")).convert("RGBA")
    # boss is already transparent on solid black
    results["node_boss"] = im_boss

    # Save hi-res versions and 48x48 versions
    for name, img in results.items():
        # Save 48x48
        img_48 = img.resize((48, 48), Image.Resampling.LANCZOS)
        out_path = os.path.join(ICONS_DIR, f"{name}.png")
        img_48.save(out_path, "PNG")
        print(f"Saved {name}.png as 48x48")

    # Generate a montage for artifact inspection
    montage = Image.new("RGBA", (7 * 64, 64), (30, 30, 35, 255))
    for i, name in enumerate(["node_combat", "node_event", "node_rest", "node_elite", "node_treasure", "node_shop", "node_boss"]):
        img = results[name].resize((48, 48), Image.Resampling.LANCZOS)
        montage.paste(img, (i * 64 + 8, 8), img)
    
    montage.save(os.path.join(ARTIFACT_DIR, "nodes_clean_montage.png"), "PNG")
    print("Saved nodes_clean_montage.png to artifacts!")

if __name__ == "__main__":
    process_all_nodes()
