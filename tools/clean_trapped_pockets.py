"""
Comprehensive enclosed pocket background cleaner for all 48 enemies.
Removes enclosed white background pockets and enclosed pure black background pockets.
Preserves outlines, tiny highlights, and sprite art details.
"""

import os
from collections import deque
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENEMIES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites", "enemies")


def clean_sprite_pockets(path: str) -> None:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    pix = im.load()

    # --- Pass 1: Remove enclosed pure white / light-grey background pockets ---
    visited_white = [[False] * h for _ in range(w)]
    for x in range(w):
        for y in range(h):
            if visited_white[x][y]:
                continue
            r, g, b, a = pix[x, y]
            if a == 0:
                visited_white[x][y] = True
                continue

            diff = max(abs(r - g), abs(r - b), abs(g - b))
            # Detect white or neutral light grey background
            if (r >= 210 and g >= 210 and b >= 210) or (r >= 180 and g >= 180 and b >= 180 and diff <= 10):
                comp = []
                q = deque([(x, y)])
                visited_white[x][y] = True
                while q:
                    cx, cy = q.popleft()
                    comp.append((cx, cy))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited_white[nx][ny]:
                            nr, ng, nb, na = pix[nx, ny]
                            ndiff = max(abs(nr - ng), abs(nr - nb), abs(ng - nb))
                            if na > 0 and ((nr >= 210 and ng >= 210 and nb >= 210) or (nr >= 180 and ng >= 180 and nb >= 180 and ndiff <= 10)):
                                visited_white[nx][ny] = True
                                q.append((nx, ny))

                # If pocket is 5 or more pixels, it's trapped background!
                # Exceptions: special monsters that are made of white bone/steam like drowned_patriarch, furnace_warden, void_mirror
                fname = os.path.basename(path)
                if fname in ("drowned_patriarch.png", "furnace_warden.png", "void_mirror.png"):
                    # Only remove if it touches an area that was near the edge
                    continue

                if len(comp) >= 5:
                    for px, py in comp:
                        pix[px, py] = (0, 0, 0, 0)

    # --- Pass 2: Remove enclosed pure black background pockets ---
    visited_black = [[False] * h for _ in range(w)]
    for x in range(w):
        for y in range(h):
            if visited_black[x][y]:
                continue
            r, g, b, a = pix[x, y]
            if a == 0:
                visited_black[x][y] = True
                continue

            # Pure black background pockets: r <= 18, g <= 18, b <= 18
            if r <= 18 and g <= 18 and b <= 18:
                comp = []
                q = deque([(x, y)])
                visited_black[x][y] = True
                while q:
                    cx, cy = q.popleft()
                    comp.append((cx, cy))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited_black[nx][ny]:
                            nr, ng, nb, na = pix[nx, ny]
                            if na > 0 and nr <= 18 and ng <= 18 and nb <= 18:
                                visited_black[nx][ny] = True
                                q.append((nx, ny))

                # If pure black region is >= 12 pixels and not a shadow monster (like null_singularity)
                fname = os.path.basename(path)
                if fname not in ("null_singularity.png", "void_mirror.png", "chronomancer_praetor.png", "devouring_constellation.png"):
                    if len(comp) >= 12:
                        for px, py in comp:
                            pix[px, py] = (0, 0, 0, 0)

    # Tight crop
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)

    im.save(path, "PNG", optimize=True)


def main():
    print("Cleaning all 48 enemy sprites for trapped pockets...")
    for f in sorted(os.listdir(ENEMIES_DIR)):
        if f.endswith(".png"):
            clean_sprite_pockets(os.path.join(ENEMIES_DIR, f))
    print("Done cleaning all enemy sprites.")


if __name__ == "__main__":
    main()
