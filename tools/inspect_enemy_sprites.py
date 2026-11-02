import os
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENEMIES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites", "enemies")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

def inspect_enemies(output_filename="inspect_enemies_sheet.png"):
    files = sorted([f for f in os.listdir(ENEMIES_DIR) if f.endswith(".png")])
    if not files:
        print("No enemies found.")
        return

    cols = 4
    rows = (len(files) + cols - 1) // cols
    cell_w = 200
    cell_h = 200

    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (30, 30, 45, 255))
    for idx, fname in enumerate(files):
        c = idx % cols
        r = idx // cols
        im = Image.open(os.path.join(ENEMIES_DIR, fname))
        
        # Scale to fit cell while preserving aspect ratio
        w, h = im.size
        scale = min(160 / w, 160 / h)
        tw = int(w * scale)
        th = int(h * scale)
        im_scaled = im.resize((tw, th), Image.Resampling.NEAREST)

        x = c * cell_w + (cell_w - tw) // 2
        y = r * cell_h + (cell_h - th) // 2
        sheet.paste(im_scaled, (x, y), im_scaled)

    out_path = os.path.join(ARTIFACT_DIR, output_filename)
    sheet.save(out_path)
    print(f"Saved inspection sheet with {len(files)} enemies to: {out_path}")

if __name__ == "__main__":
    inspect_enemies()
