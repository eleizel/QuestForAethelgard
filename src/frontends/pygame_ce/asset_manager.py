"""Asset Manager for Pygame-CE: loads background illustrations and extracts retro sprites."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final
import zipfile
import tomllib
import pygame

from src.core.theme import PYXEL_DEFAULT_PALETTE

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKGROUNDS_DIR = PROJECT_ROOT / "assets" / "backgrounds"
PYXRES_PATH = PROJECT_ROOT / "assets" / "game.pyxres"

# Enemy coordinates on Bank 0 (16x16)
ENEMY_COORDS: Final[dict[str, tuple[int, int]]] = {
    # 1A: Arboretum
    "thornvein_creeper": (0, 48), "spore_pod": (16, 48), "bramble_hound": (32, 48),
    "rotting_woodwose": (48, 48), "mandragora_matron": (64, 48), "corpse_treant": (80, 48),
    "malignant_belladonna": (96, 48), "verdant_abomination": (112, 48),
    # 1B: Cathedral
    "cathedral_imp": (0, 64), "possessed_grimoire": (16, 64), "candelabra_fiend": (32, 64),
    "penitent_zealot": (48, 64), "belltower_gargoyle": (64, 64), "inquisitor_automaton": (80, 64),
    "blind_archbishop": (96, 64), "chorus_of_damned": (112, 64),
    # 2A: Ossuary
    "mire_ghoul": (0, 80), "drowned_skulls": (16, 80), "leech_husk": (32, 80),
    "crypt_lurker": (48, 80), "tide_gravekeeper": (64, 80), "carrion_behemoth": (80, 80),
    "drowned_patriarch": (96, 80), "scylla_bone_weaver": (112, 80),
    # 2B: Foundry
    "slag_homunculus": (0, 96), "cinder_sprite": (16, 96), "clockwork_flayer": (32, 96),
    "ashen_overseer": (48, 96), "furnace_warden": (64, 96), "retching_alchemist": (80, 96),
    "ironforge_tyrant": (96, 96), "molten_sovereign": (112, 96),
    # 3A: Observatory
    "void_mirror": (0, 112), "stareater_wisp": (16, 112), "comet_stalker": (32, 112),
    "celestial_hermit": (48, 112), "rift_warden": (64, 112), "null_singularity": (80, 112),
    "chronomancer_praetor": (96, 112), "devouring_constellation": (112, 112),
    # 3B: Sanctum
    "sanguine_thrall": (0, 128), "crimson_gargoyle": (16, 128), "hemomancer_acolyte": (32, 128),
    "flayed_duelist": (48, 128), "baroness_vespera": (64, 128), "amalgam_of_veins": (80, 128),
    "high_lord_carmilla": (96, 128), "blood_god_avatar": (112, 128),
}

# Class Portrait coordinates
STARTER_PORTRAITS: Final[dict[str, tuple[int, int, int, int]]] = {
    "warrior": (0, 0, 144, 48, 64),  # bank, u, v, w, h
    "rogue": (0, 48, 144, 48, 64),
    "mage": (0, 96, 144, 48, 64),
}

PROMOTED_PORTRAITS: Final[dict[str, tuple[int, int, int, int]]] = {
    "paladin": (2, 0, 0, 48, 64),
    "berserker": (2, 48, 0, 48, 64),
    "venomancer": (2, 96, 0, 48, 64),
    "duelist": (2, 144, 0, 48, 64),
    "archmage": (2, 192, 0, 48, 64),
    "warlock": (2, 0, 64, 48, 64),
}


class AssetManager:
    """Singleton managing loaded backgrounds and cached spritesheets for Pygame-CE."""

    _instance: AssetManager | None = None

    def __new__(cls) -> AssetManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self) -> None:
        self.background_surfaces: dict[str, pygame.Surface] = {}
        self.scaled_bg_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self.bank_surfaces: dict[int, pygame.Surface] = {}
        self.sprite_cache: dict[tuple[int, int, int, int, int, int], pygame.Surface] = {}
        self._load_backgrounds()
        self._load_banks_from_pyxres()

    def _load_backgrounds(self) -> None:
        """Load all static illustrations from assets/backgrounds."""
        if not BACKGROUNDS_DIR.exists():
            return

        for path in BACKGROUNDS_DIR.glob("*.png"):
            key = path.stem.lower()
            try:
                surf = pygame.image.load(str(path))
                self.background_surfaces[key] = surf.convert() if pygame.display.get_surface() else surf
            except Exception:
                pass

    def _load_banks_from_pyxres(self) -> None:
        """Extract Bank 0, Bank 1, and Bank 2 spritesheets from game.pyxres."""
        if not PYXRES_PATH.exists():
            return

        try:
            with zipfile.ZipFile(str(PYXRES_PATH), "r") as z:
                toml_text = z.read("pyxel_resource.toml").decode("utf-8")
                doc = tomllib.loads(toml_text)

            images = doc.get("images", [])
            for bank_idx, img_def in enumerate(images):
                w = img_def.get("width", 256)
                h = img_def.get("height", 256)
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                data = img_def.get("data", [])

                for y, row in enumerate(data):
                    for x, col_idx in enumerate(row):
                        if 1 <= col_idx < len(PYXEL_DEFAULT_PALETTE):
                            rgb = PYXEL_DEFAULT_PALETTE[col_idx]
                            surf.set_at((x, y), (rgb.r, rgb.g, rgb.b, 255))

                self.bank_surfaces[bank_idx] = surf
        except Exception:
            pass

    def get_background(self, key: str, width: int = 960, height: int = 540) -> pygame.Surface | None:
        """Retrieve or cache-scale a background illustration."""
        cache_key = (key.lower(), width, height)
        if cache_key in self.scaled_bg_cache:
            return self.scaled_bg_cache[cache_key]

        raw = self.background_surfaces.get(key.lower())
        if raw is None:
            # Fallback for aliases
            raw = self.background_surfaces.get("welcome")
            if raw is None:
                return None

        scaled = pygame.transform.smoothscale(raw, (width, height))
        self.scaled_bg_cache[cache_key] = scaled
        return scaled

    def draw_background(
        self,
        surface: pygame.Surface,
        key: str,
        vignette_alpha: int = 150,
    ) -> None:
        """Draw background on target surface with atmospheric dark vignette overlay."""
        w, h = surface.get_width(), surface.get_height()
        bg = self.get_background(key, width=w, height=h)
        if bg:
            surface.blit(bg, (0, 0))

        if vignette_alpha > 0:
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((8, 10, 16, min(255, max(0, vignette_alpha))))
            surface.blit(overlay, (0, 0))

    def get_sprite(
        self,
        bank: int,
        u: int,
        v: int,
        w: int,
        h: int,
        scale: int = 2,
    ) -> pygame.Surface | None:
        """Extract and upscale a sub-region from a bank spritesheet."""
        cache_key = (bank, u, v, w, h, scale)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        bank_surf = self.bank_surfaces.get(bank)
        if bank_surf is None:
            return None

        # Clamp rect to bank boundaries
        rect = pygame.Rect(u, v, min(w, 256 - u), min(h, 256 - v))
        sub = bank_surf.subsurface(rect)
        if scale > 1:
            scaled = pygame.transform.scale(sub, (w * scale, h * scale))
        else:
            scaled = sub

        self.sprite_cache[cache_key] = scaled
        return scaled

    def get_class_portrait(self, class_id: str, scale: int = 2, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve hero or promoted class portrait, preferring SNES-style PNG assets."""
        cid = class_id.lower()
        cache_key = f"portrait_{cid}_{scale}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "portraits" / f"{cid}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            elif scale > 1:
                surf = pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))
            self.sprite_cache[cache_key] = surf
            return surf

        # Fallback to Pyxel banks
        if cid in STARTER_PORTRAITS:
            bank, u, v, w, h = STARTER_PORTRAITS[cid]
            return self.get_sprite(bank, u, v, w, h, scale=scale)
        elif cid in PROMOTED_PORTRAITS:
            bank, u, v, w, h = PROMOTED_PORTRAITS[cid]
            return self.get_sprite(bank, u, v, w, h, scale=scale)
        return None

    def get_class_sprite(self, class_id: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES class combat/pedestal sprite."""
        cid = class_id.lower()
        cache_key = f"sprite_{cid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "sprites" / f"{cid}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_class_crest(self, class_id: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES class emblem/crest icon."""
        cid = class_id.lower()
        cache_key = f"crest_{cid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "icons" / f"crest_{cid}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_stat_icon(self, stat_name: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit stat icon (hp, atk, def, spd, crit)."""
        sname = stat_name.lower()
        cache_key = f"stat_{sname}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "icons" / f"{sname}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_enemy_sprite(self, enemy_id: str, scale: int = 3) -> pygame.Surface | None:
        """Retrieve 16x16 enemy sprite upscaled for combat arena."""
        coords = ENEMY_COORDS.get(enemy_id.lower())
        if coords:
            u, v = coords
            return self.get_sprite(0, u, v, 16, 16, scale=scale)
        # Fallback skeleton at (16, 0)
        return self.get_sprite(0, 16, 0, 16, 16, scale=scale)


    def get_ui_component(self, name: str) -> pygame.Surface | None:
        """Retrieve a registered reusable UI component (frame, border, banner, button)."""
        cache_key = f"ui_{name}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        candidate = PROJECT_ROOT / "assets" / "ui" / f"{name}.png"
        if candidate.exists():
            surf = pygame.image.load(str(candidate))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def render_9slice(
        self,
        src_surf: pygame.Surface,
        target_w: int,
        target_h: int,
        margin: int = 54,
    ) -> pygame.Surface:
        """Scale an ornate frame to arbitrary width and height using 9-slice tiling/stretching."""
        w, h = src_surf.get_size()
        # Scale margin down if target dimensions are small
        m = min(margin, target_w // 3, target_h // 3)
        if m <= 0:
            m = min(margin, target_w // 2, target_h // 2)
        if m <= 0:
            return pygame.transform.scale(src_surf, (target_w, target_h))

        out = pygame.Surface((target_w, target_h), pygame.SRCALPHA)

        # 4 corners
        tl = src_surf.subsurface((0, 0, m, m))
        tr = src_surf.subsurface((w - m, 0, m, m))
        bl = src_surf.subsurface((0, h - m, m, m))
        br = src_surf.subsurface((w - m, h - m, m, m))

        # 4 edges
        inner_w = max(1, target_w - 2 * m)
        inner_h = max(1, target_h - 2 * m)
        src_inner_w = max(1, w - 2 * m)
        src_inner_h = max(1, h - 2 * m)

        t_edge = src_surf.subsurface((m, 0, src_inner_w, m))
        b_edge = src_surf.subsurface((m, h - m, src_inner_w, m))
        l_edge = src_surf.subsurface((0, m, m, src_inner_h))
        r_edge = src_surf.subsurface((w - m, m, m, src_inner_h))

        center = src_surf.subsurface((m, m, src_inner_w, src_inner_h))

        # Blit center and edges
        out.blit(pygame.transform.scale(center, (inner_w, inner_h)), (m, m))
        out.blit(pygame.transform.scale(t_edge, (inner_w, m)), (m, 0))
        out.blit(pygame.transform.scale(b_edge, (inner_w, m)), (m, target_h - m))
        out.blit(pygame.transform.scale(l_edge, (m, inner_h)), (0, m))
        out.blit(pygame.transform.scale(r_edge, (m, inner_h)), (target_w - m, m))

        # Blit corners
        out.blit(tl, (0, 0))
        out.blit(tr, (target_w - m, 0))
        out.blit(bl, (0, target_h - m))
        out.blit(br, (target_w - m, target_h - m))
        return out

    def get_9slice_frame(
        self,
        name: str = "frame_gold_ornate",
        target_w: int = 400,
        target_h: int = 280,
        margin: int = 54,
    ) -> pygame.Surface | None:
        """Retrieve a cached 9-slice rendered ornate frame of target dimensions."""
        cache_key = f"9slice_{name}_{target_w}_{target_h}_{margin}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        base_frame = self.get_ui_component(name)
        if base_frame is None:
            return None

        scaled = self.render_9slice(base_frame, target_w, target_h, margin=margin)
        self.sprite_cache[cache_key] = scaled
        return scaled


# Global singleton helper
assets = AssetManager()
