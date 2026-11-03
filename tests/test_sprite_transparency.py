"""Automated regression prevention test suite for sprite silhouette transparency integrity.

Verifies that all 57 character and enemy PNG sprites have 0 unintended interior
transparent voids inside their body silhouettes, while properly preserving
authentic negative space loops (e.g. Rogue crouch, Warrior sword gap, Drowned
Patriarch water cascades, Ashen Overseer whip loop, Null Singularity vortex gaps).
"""

from collections import deque
import os
from pathlib import Path
from PIL import Image
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HERO_DIR = PROJECT_ROOT / "assets" / "sprites"
ENEMY_DIR = HERO_DIR / "enemies"

SOLID_HEROES = [
    "archmage.png",
    "berserker.png",
    "duelist.png",
    "mage.png",
    "paladin.png",
    "venomancer.png",
    "warlock.png",
]

ALL_HEROES = sorted([p.name for p in HERO_DIR.glob("*.png")])
ALL_ENEMIES = sorted([p.name for p in ENEMY_DIR.glob("*.png")])


def get_exterior_and_void_components(
    img_path: Path,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]], list[list[tuple[int, int]]]]:
    """Perform BFS exterior flood-fill from all 4 borders and identify all interior void components."""
    im = Image.open(img_path).convert("RGBA")
    w, h = im.size
    pix = im.load()

    # 1. 4-connected exterior flood fill seeded from canvas borders
    exterior = set()
    queue = deque()
    for x in range(w):
        if pix[x, 0][3] == 0 and (x, 0) not in exterior:
            exterior.add((x, 0))
            queue.append((x, 0))
        if pix[x, h - 1][3] == 0 and (x, h - 1) not in exterior:
            exterior.add((x, h - 1))
            queue.append((x, h - 1))
    for y in range(h):
        if pix[0, y][3] == 0 and (0, y) not in exterior:
            exterior.add((0, y))
            queue.append((0, y))
        if pix[w - 1, y][3] == 0 and (w - 1, y) not in exterior:
            exterior.add((w - 1, y))
            queue.append((w - 1, y))

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in exterior and pix[nx, ny][3] == 0:
                exterior.add((nx, ny))
                queue.append((nx, ny))

    # 2. Collect interior transparent void pixels
    void_pixels = {
        (x, y)
        for y in range(h)
        for x in range(w)
        if pix[x, y][3] == 0 and (x, y) not in exterior
    }

    # 3. Partition interior voids into 4-connected components
    components = []
    visited_voids = set()
    for vx, vy in void_pixels:
        if (vx, vy) not in visited_voids:
            comp = []
            cq = deque([(vx, vy)])
            visited_voids.add((vx, vy))
            while cq:
                curr = cq.popleft()
                comp.append(curr)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = curr[0] + dx, curr[1] + dy
                    if (nx, ny) in void_pixels and (nx, ny) not in visited_voids:
                        visited_voids.add((nx, ny))
                        cq.append((nx, ny))
            components.append(comp)

    components.sort(key=len, reverse=True)
    return exterior, void_pixels, components


def test_asset_inventory_completeness():
    """Verify that all 9 hero class sprites and 48 enemy sprites exist."""
    assert len(ALL_HEROES) == 9, f"Expected 9 hero class sprites, found {len(ALL_HEROES)}: {ALL_HEROES}"
    assert len(ALL_ENEMIES) == 48, f"Expected 48 enemy sprites, found {len(ALL_ENEMIES)}"


@pytest.mark.parametrize("hero_name", SOLID_HEROES)
def test_solid_hero_sprites_have_zero_interior_voids(hero_name: str):
    """Verify that solid hero sprites have exactly 0 interior transparent void pixels."""
    sprite_path = HERO_DIR / hero_name
    _, void_pixels, components = get_exterior_and_void_components(sprite_path)
    assert len(void_pixels) == 0, (
        f"Solid hero sprite '{hero_name}' has {len(void_pixels)} interior transparent pixels "
        f"across {len(components)} components! Sample coords: {list(void_pixels)[:5]}"
    )


def test_warlock_collar_breach_and_cowl_integrity():
    """Verify that warlock.png has its collar breach sealed and cowl face cavity fully opaque."""
    warlock_path = HERO_DIR / "warlock.png"
    im = Image.open(warlock_path).convert("RGBA")
    pix = im.load()

    # Verify zero interior voids across the entire sprite
    _, void_pixels, _ = get_exterior_and_void_components(warlock_path)
    assert len(void_pixels) == 0, f"Warlock sprite has {len(void_pixels)} interior voids!"

    # Cowl face bounding box (x in [230, 270], y in [100, 140]) must have 100% opaque pixels
    cowl_transparent = [
        (x, y)
        for y in range(100, 140)
        for x in range(230, 270)
        if pix[x, y][3] == 0
    ]
    assert len(cowl_transparent) == 0, (
        f"Warlock cowl face has {len(cowl_transparent)} transparent pixels! Sample: {cowl_transparent[:5]}"
    )

    # Glowing red eyes must be present and opaque
    red_eyes = [
        (x, y)
        for y in range(100, 110)
        for x in range(230, 270)
        if pix[x, y][3] == 255 and pix[x, y][0] > 150 and pix[x, y][1] < 60 and pix[x, y][2] < 60
    ]
    assert len(red_eyes) >= 10, f"Expected at least 10 red eye pixels, found {len(red_eyes)}"


def test_venomancer_silhouette_integrity():
    """Verify venomancer.png has zero interior voids across cowl, bandolier, and pedestal."""
    veno_path = HERO_DIR / "venomancer.png"
    _, void_pixels, _ = get_exterior_and_void_components(veno_path)
    assert len(void_pixels) == 0, f"Venomancer has {len(void_pixels)} interior voids!"


def test_rogue_negative_space_preservation():
    """Verify rogue.png preserves authentic negative space between legs and under arm, but has 0 void defects."""
    rogue_path = HERO_DIR / "rogue.png"
    im = Image.open(rogue_path).convert("RGBA")
    pix = im.load()

    _, void_pixels, components = get_exterior_and_void_components(rogue_path)

    # Exactly 2 components: between legs (>10000 px) and under arm (>2000 px)
    assert len(components) == 2, (
        f"Rogue expected exactly 2 negative space components, found {len(components)}: {[len(c) for c in components]}"
    )
    leg_comp, arm_comp = components[0], components[1]
    assert len(leg_comp) > 10000, f"Leg negative space loop too small: {len(leg_comp)} px"
    assert len(arm_comp) > 2000, f"Arm negative space loop too small: {len(arm_comp)} px"

    # Specific interior negative space coordinate checks
    assert pix[280, 340][3] == 0, "Expected negative space between Rogue's legs at (280, 340) to be transparent"
    assert pix[190, 220][3] == 0, "Expected negative space under Rogue's arm at (190, 220) to be transparent"


def test_warrior_negative_space_preservation():
    """Verify warrior.png preserves authentic negative space behind sword, but has 0 void defects."""
    warrior_path = HERO_DIR / "warrior.png"
    im = Image.open(warrior_path).convert("RGBA")
    pix = im.load()

    _, void_pixels, components = get_exterior_and_void_components(warrior_path)

    # Exactly 1 component: behind broadsword (>2000 px)
    assert len(components) == 1, (
        f"Warrior expected exactly 1 negative space component, found {len(components)}: {[len(c) for c in components]}"
    )
    sword_comp = components[0]
    assert len(sword_comp) > 2000, f"Sword negative space loop too small: {len(sword_comp)} px"

    # Specific interior negative space coordinate check
    assert pix[300, 450][3] == 0, "Expected negative space behind Warrior's sword at (300, 450) to be transparent"


@pytest.mark.parametrize("enemy_name", ALL_ENEMIES)
def test_enemy_sprite_transparency_integrity(enemy_name: str):
    """Verify enemy sprite has no accidental transparent void defects (< 100 px), and solid enemies have 0 voids."""
    enemy_path = ENEMY_DIR / enemy_name
    _, void_pixels, components = get_exterior_and_void_components(enemy_path)

    # Invariant across all 48 enemies: zero small void components (< 100 px)
    small_voids = [c for c in components if len(c) < 100]
    assert len(small_voids) == 0, (
        f"Enemy '{enemy_name}' has {len(small_voids)} internal void defects (<100 px)! "
        f"Component sizes: {[len(c) for c in small_voids]}"
    )

    # Negative-space allowed enemies
    if enemy_name == "drowned_patriarch.png":
        # Water cascade loops (>400 px)
        for c in components:
            assert len(c) >= 400, f"Unexpected void size in drowned_patriarch: {len(c)}"
    elif enemy_name == "ashen_overseer.png":
        # Scythe air and whip loop (>150 px)
        for c in components:
            assert len(c) >= 150, f"Unexpected void size in ashen_overseer: {len(c)}"
    elif enemy_name == "null_singularity.png":
        # Outer vortex arm gaps (>100 px)
        for c in components:
            assert len(c) >= 100, f"Unexpected void size in null_singularity: {len(c)}"
    else:
        # All other 45 enemies must have exactly zero interior voids
        assert len(void_pixels) == 0, (
            f"Enemy '{enemy_name}' has {len(void_pixels)} interior voids across {len(components)} components!"
        )


def test_pygame_scaled_bleedthrough_resilience():
    """Verify that downscaled sprites rendered over a high-contrast magenta surface exhibit no bleed-through."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    import pygame

    if not pygame.get_init():
        pygame.init()
    pygame.display.set_mode((1, 1))

    for hero_name in ["warlock.png", "venomancer.png", "mage.png"]:
        p = HERO_DIR / hero_name
        surf = pygame.image.load(str(p)).convert_alpha()
        ow, oh = surf.get_size()
        th = 88
        tw = int(ow * (th / oh))
        scaled = pygame.transform.smoothscale(surf, (tw, th))

        bg = pygame.Surface((tw + 20, th + 20))
        bg.fill((255, 0, 255))  # pure magenta
        bg.blit(scaled, (10, 10))

        # Check body center coordinate (inside body silhouette)
        center_color = bg.get_at((10 + tw // 2, 10 + th // 2))
        assert center_color != (255, 0, 255, 255), (
            f"Sprite '{hero_name}' has magenta background bleed-through at center! Got {center_color}"
        )
