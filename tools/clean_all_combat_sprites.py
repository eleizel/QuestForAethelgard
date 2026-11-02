"""
Post-processing script to ensure 100% transparent backgrounds for all 48 enemies and 9 status badges.
Uses multi-point floodfill from all 4 borders to remove solid white or solid black backgrounds without affecting internal pixel art.
"""

import os
from collections import deque
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENEMIES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites", "enemies")
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"


def clean_image_transparency(path: str, is_badge: bool = False) -> bool:
    if not os.path.exists(path):
        return False

    im = Image.open(path).convert("RGBA")
    w, h = im.size
    pix = im.load()

    # Sample border pixels to detect background color
    samples = [
        pix[0, 0], pix[w - 1, 0], pix[0, h - 1], pix[w - 1, h - 1],
        pix[w // 2, 0], pix[w // 2, h - 1], pix[0, h // 2], pix[w - 1, h // 2]
    ]

    white_hits = sum(1 for p in samples if p[0] >= 200 and p[1] >= 200 and p[2] >= 200 and p[3] > 0)
    black_hits = sum(1 for p in samples if p[0] <= 45 and p[1] <= 45 and p[2] <= 45 and p[3] > 0)

    if white_hits < 2 and black_hits < 2:
        return False  # Already transparent or complex

    is_white = white_hits >= black_hits

    # Seed queue with all perimeter pixels
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))

    visited = set()

    def matches(p):
        r, g, b, a = p
        if a == 0:
            return True
        if is_white:
            return r >= 200 and g >= 200 and b >= 200
        else:
            return r <= 45 and g <= 45 and b <= 45

    while q:
        x, y = q.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))

        if 0 <= x < w and 0 <= y < h:
            if matches(pix[x, y]):
                pix[x, y] = (0, 0, 0, 0)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        q.append((nx, ny))

    # Tightly crop to bounding box
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)

    im.save(path, "PNG", optimize=True)
    return True


def main():
    print("--- Cleaning Enemy Sprites Transparency ---")
    enemies = sorted([f for f in os.listdir(ENEMIES_DIR) if f.endswith(".png")])
    cleaned_enemies = 0
    for f in enemies:
        p = os.path.join(ENEMIES_DIR, f)
        if clean_image_transparency(p):
            cleaned_enemies += 1
            print(f"  [+] Cleaned enemy: {f}")
    print(f"Cleaned {cleaned_enemies} / {len(enemies)} enemy sprites.")

    print("\n--- Cleaning Status Badges Transparency ---")
    badges = [f for f in os.listdir(ICONS_DIR) if f.startswith("status_") and f.endswith(".png")]
    cleaned_badges = 0
    for f in badges:
        p = os.path.join(ICONS_DIR, f)
        if clean_image_transparency(p, is_badge=True):
            cleaned_badges += 1
            print(f"  [+] Cleaned badge: {f}")
    print(f"Cleaned {cleaned_badges} / {len(badges)} status badges.")


if __name__ == "__main__":
    main()
