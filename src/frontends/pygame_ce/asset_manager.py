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

    def get_bust_portrait(self, class_id: str, size: tuple[int, int] = (40, 40)) -> pygame.Surface | None:
        """Retrieve neck-up cropped 16-bit bust portrait scaled to size preserving aspect ratio."""
        cid = class_id.lower()
        cache_key = f"bust_{cid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        raw_portrait = self.get_class_portrait(cid)
        if raw_portrait is None:
            return None

        # Crop neck-up: top ~68% height, center 85% width
        w, h = raw_portrait.get_size()
        crop_h = int(h * 0.68)
        crop_w = int(w * 0.85)
        left = (w - crop_w) // 2
        sub = raw_portrait.subsurface((left, 0, crop_w, crop_h))

        tw, th = size
        scale = min(tw / crop_w, th / crop_h)
        scaled_w = max(1, int(crop_w * scale))
        scaled_h = max(1, int(crop_h * scale))
        scaled = pygame.transform.smoothscale(sub, (scaled_w, scaled_h))

        final_surf = pygame.Surface(size, pygame.SRCALPHA)
        final_surf.blit(scaled, ((tw - scaled_w) // 2, (th - scaled_h) // 2))
        self.sprite_cache[cache_key] = final_surf
        return final_surf

    def get_biome_icon(self, biome_id: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES biome emblem icon."""
        bid = biome_id.lower()
        cache_key = f"biome_{bid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "icons" / f"biome_{bid}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_node_icon(self, node_type: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES map node medallion icon (combat, event, rest, elite, treasure, shop, boss)."""
        ntype = node_type.lower()
        cache_key = f"node_{ntype}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "icons" / f"node_{ntype}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_status_icon(self, status_id: str, size: tuple[int, int] = (24, 24)) -> pygame.Surface | None:
        """Retrieve 16-bit SNES status effect badge icon (burn, poison, bleed, stun, blind, fortify, haste, weaken, vulnerable)."""
        sid = status_id.lower()
        cache_key = f"status_{sid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "icons" / f"status_{sid}.png"
        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_item_icon(self, item_id: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES inventory / belt item icon."""
        iid = item_id.lower()
        cache_key = f"item_{iid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        candidate_names = [f"item_{iid}.png", f"{iid}.png"]
        if "potion" in iid or "health" in iid:
            candidate_names.append("item_potion_health.png")
        elif "mana" in iid or "blue" in iid:
            candidate_names.append("item_potion_mana.png")
        elif "herb" in iid or "antidote" in iid:
            candidate_names.append("item_herb.png")

        for c in candidate_names:
            p = PROJECT_ROOT / "assets" / "icons" / c
            if p.exists():
                surf = pygame.image.load(str(p))
                if pygame.display.get_surface():
                    surf = surf.convert_alpha()
                if size is not None:
                    surf = pygame.transform.smoothscale(surf, size)
                self.sprite_cache[cache_key] = surf
                return surf
        return None

    def get_pyxel_icon(self, u: int, v: int, size: tuple[int, int] = (24, 24)) -> pygame.Surface | None:
        """Extract an 8x8 retro item tile from Bank 0 and scale it nearest-neighbor."""
        cache_key = f"pyxel_tile_{u}_{v}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        bank_surf = self.get_ui_component("pyxel_bank0")
        if bank_surf is None:
            return None

        tile_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        tile_surf.blit(bank_surf, (0, 0), (u, v, 8, 8))
        scaled = pygame.transform.scale(tile_surf, size)
        self.sprite_cache[cache_key] = scaled
        return scaled

    def get_combat_arena_bg(self, biome_id: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        """Retrieve 16-bit SNES combat arena background with foreground battle platform."""
        bid = biome_id.lower()
        cache_key = f"combat_bg_{bid}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        png_path = PROJECT_ROOT / "assets" / "backgrounds" / f"combat_{bid}.png"
        if not png_path.exists():
            png_path = PROJECT_ROOT / "assets" / "backgrounds" / f"{bid}.png"

        if png_path.exists():
            surf = pygame.image.load(str(png_path))
            if pygame.display.get_surface():
                surf = surf.convert()
            if size is not None:
                surf = pygame.transform.smoothscale(surf, size)
            self.sprite_cache[cache_key] = surf
            return surf
        return None

    def get_enemy_sprite(
        self,
        enemy_id_or_name: str,
        size: tuple[int, int] | None = None,
        max_height: int = 120,
        scale: int = 3,
    ) -> pygame.Surface | None:
        """Retrieve authentic 16-bit SNES enemy combat sprite facing left."""
        raw_key = enemy_id_or_name.lower().replace(" ", "_").replace("-", "_").replace(",", "").replace(".", "")
        cache_key = f"enemy_sprite_{raw_key}_{size}_{max_height}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        # 1. Check generated high-res 16-bit enemy sprites
        enemy_dir = PROJECT_ROOT / "assets" / "sprites" / "enemies"
        candidate_paths = [
            enemy_dir / f"{raw_key}.png",
        ]
        # Also match substrings if needed
        for p in candidate_paths:
            if p.exists():
                surf = pygame.image.load(str(p))
                if pygame.display.get_surface():
                    surf = surf.convert_alpha()
                if size is not None:
                    surf = pygame.transform.smoothscale(surf, size)
                elif max_height:
                    w, h = surf.get_size()
                    if h > max_height or w > 200:
                        ratio = min(max_height / h, 200 / w)
                        new_w = max(1, int(w * ratio))
                        new_h = max(1, int(h * ratio))
                        surf = pygame.transform.smoothscale(surf, (new_w, new_h))
                self.sprite_cache[cache_key] = surf
                return surf

        # Check all files in enemy_dir for substring match
        if enemy_dir.exists():
            for p in enemy_dir.glob("*.png"):
                stem = p.stem.lower()
                if stem in raw_key or raw_key in stem:
                    surf = pygame.image.load(str(p))
                    if pygame.display.get_surface():
                        surf = surf.convert_alpha()
                    if size is not None:
                        surf = pygame.transform.smoothscale(surf, size)
                    elif max_height:
                        w, h = surf.get_size()
                        ratio = min(max_height / h, 200 / w)
                        new_w = max(1, int(w * ratio))
                        new_h = max(1, int(h * ratio))
                        surf = pygame.transform.smoothscale(surf, (new_w, new_h))
                    self.sprite_cache[cache_key] = surf
                    return surf

        # 2. Fallback to 16x16 sprite banks upscaled
        coords = ENEMY_COORDS.get(raw_key)
        if coords:
            u, v = coords
            return self.get_sprite(0, u, v, 16, 16, scale=scale)
        return self.get_sprite(0, 16, 0, 16, 16, scale=scale)

    def get_enemy_bust(self, enemy_id_or_name: str, size: tuple[int, int] = (38, 38)) -> pygame.Surface | None:
        """Retrieve cropped headshot/bust of an enemy sprite for the enemy status window."""
        raw_key = enemy_id_or_name.lower().replace(" ", "_").replace("-", "_")
        cache_key = f"enemy_bust_{raw_key}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        sprite = self.get_enemy_sprite(enemy_id_or_name, max_height=180)
        if sprite is None:
            return None

        w, h = sprite.get_size()
        # Crop headshot: upper 65% height, center 75% width
        crop_h = max(1, int(h * 0.65))
        crop_w = max(1, int(w * 0.75))
        left = max(0, (w - crop_w) // 2)
        sub = sprite.subsurface((left, 0, min(crop_w, w - left), min(crop_h, h)))

        tw, th = size
        # Fill the square headshot frame nicely
        scale = max(tw / sub.get_width(), th / sub.get_height())
        scaled_w = max(1, int(sub.get_width() * scale))
        scaled_h = max(1, int(sub.get_height() * scale))
        scaled = pygame.transform.smoothscale(sub, (scaled_w, scaled_h))

        final_surf = pygame.Surface(size, pygame.SRCALPHA)
        final_surf.blit(scaled, ((tw - scaled_w) // 2, (th - scaled_h) // 2))
        self.sprite_cache[cache_key] = final_surf
        return final_surf


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
        draw_center: bool = True,
        edge_margin: int | None = None,
    ) -> pygame.Surface:
        """Scale an ornate frame to arbitrary width and height using 9-slice tiling/stretching."""
        w, h = src_surf.get_size()
        # Scale margin down if target dimensions are small (use // 2 to support narrow bars)
        m = min(margin, target_w // 2, target_h // 2)
        if m <= 0:
            return pygame.transform.scale(src_surf, (target_w, target_h))

        em = min(edge_margin if edge_margin is not None else m, m)

        out = pygame.Surface((target_w, target_h), pygame.SRCALPHA)

        # 4 corners
        tl = src_surf.subsurface((0, 0, m, m))
        tr = src_surf.subsurface((w - m, 0, m, m))
        bl = src_surf.subsurface((0, h - m, m, m))
        br = src_surf.subsurface((w - m, h - m, m, m))

        # 4 edges
        src_inner_w = max(1, w - 2 * m)
        src_inner_h = max(1, h - 2 * m)
        dest_inner_w = max(1, target_w - 2 * m)
        dest_inner_h = max(1, target_h - 2 * m)

        t_edge = src_surf.subsurface((m, 0, src_inner_w, em))
        b_edge = src_surf.subsurface((m, h - em, src_inner_w, em))
        l_edge = src_surf.subsurface((0, m, em, src_inner_h))
        r_edge = src_surf.subsurface((w - em, m, em, src_inner_h))

        center = src_surf.subsurface((m, m, src_inner_w, src_inner_h))

        # Blit center and edges
        if draw_center:
            out.blit(pygame.transform.scale(center, (dest_inner_w, dest_inner_h)), (m, m))
        out.blit(pygame.transform.scale(t_edge, (dest_inner_w, em)), (m, 0))
        out.blit(pygame.transform.scale(b_edge, (dest_inner_w, em)), (m, target_h - em))
        out.blit(pygame.transform.scale(l_edge, (em, dest_inner_h)), (0, m))
        out.blit(pygame.transform.scale(r_edge, (em, dest_inner_h)), (target_w - em, m))

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
        draw_center: bool = True,
        edge_margin: int | None = None,
    ) -> pygame.Surface | None:
        """Retrieve a cached 9-slice rendered ornate frame of target dimensions."""
        cache_key = f"9slice_{name}_{target_w}_{target_h}_{margin}_{draw_center}_{edge_margin}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        base_frame = self.get_ui_component(name)
        if base_frame is None:
            return None

        scaled = self.render_9slice(
            base_frame, target_w, target_h, margin=margin, draw_center=draw_center, edge_margin=edge_margin
        )
        self.sprite_cache[cache_key] = scaled
        return scaled


# Global singleton helper
assets = AssetManager()
