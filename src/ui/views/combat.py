"""View switching architecture including CombatView, MapView, and InventoryView."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pyxel

from src.config import (
    COLOR_BLACK,
    COLOR_BROWN,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PEACH,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    SCREEN_WIDTH,
)
from src.core.audio import audio
from src.core.i18n import t
from src.entities import Enemy
from src.data.abilities import get_random_abilities
from src.systems.combat import ACTION_THRESHOLD
from src.systems.inventory import MAX_BELT_SLOTS
from src.ui.renderer import Renderer
from src.ui.views.base import View, CombatPopup, ENEMY_SPRITE_COORDS, SPEED_INTERVALS, SPEED_LABELS

if TYPE_CHECKING:
    from src.core.game_state import GameState


# =============================================================================
# BIOME ENEMY SPRITE COORDINATE MAP (Bank 0)
# =============================================================================
class CombatView(View):
    """Renders retro dungeon combat arena, detailed stat cards, split command panel, and battle log."""

    def __init__(self) -> None:
        self.popups: list[CombatPopup] = []
        self.player_flash: int = 0
        self.enemy_flash: int = 0
        self.shake_frames: int = 0
        self.speed_index: int = 0

    def _detect_combat_deltas(self, game_state: GameState, old_p_hp: int, old_e_hp: int) -> None:
        if game_state.combat is None:
            return

        combat = game_state.combat
        new_p_hp = game_state.player.current_hp
        new_e_hp = combat.enemy.current_hp

        # Player damage / heal
        if new_p_hp < old_p_hp:
            dmg = old_p_hp - new_p_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_RED if is_crit else COLOR_PEACH
            self.popups.append(CombatPopup(x=62, y=44, text=txt, color=col))
            self.player_flash = 3
            if is_crit:
                self.shake_frames = 5
        elif new_p_hp > old_p_hp:
            heal = new_p_hp - old_p_hp
            self.popups.append(CombatPopup(x=62, y=44, text=f"+{heal}", color=COLOR_LIME))

        # Enemy damage / heal
        if new_e_hp < old_e_hp:
            dmg = old_e_hp - new_e_hp
            is_crit = any("CRIT" in log or "CRÍTICO" in log for log in combat.combat_logs[-2:])
            txt = f"-{dmg}!" if is_crit else f"-{dmg}"
            col = COLOR_YELLOW if is_crit else COLOR_WHITE
            self.popups.append(CombatPopup(x=184, y=44, text=txt, color=col))
            self.enemy_flash = 3
            if is_crit:
                self.shake_frames = 6

    def update(self, game_state: GameState) -> None:
        if game_state.combat is None:
            self.popups.clear()
            return

        for p in self.popups:
            if p.lifetime % 2 == 0:
                p.y -= 1
            p.lifetime -= 1
        self.popups = [p for p in self.popups if p.lifetime > 0]

        # Speed toggle [Z] or click at bottom-right corner of dungeon arena (222, 79, 28, 11)
        if pyxel.btnp(pyxel.KEY_Z) or Renderer.is_clicked(222, 79, 28, 11):
            self.speed_index = (self.speed_index + 1) % len(SPEED_INTERVALS)
            audio.play_sfx( 3)
            return

        speed_frames = SPEED_INTERVALS[self.speed_index]

        # Advance combat (auto-tick, space, or tap on arena/log)
        if pyxel.btnp(pyxel.KEY_SPACE) or (pyxel.frame_count % speed_frames == 0) or Renderer.is_clicked(0, 24,
                                                                                                         SCREEN_WIDTH,
                                                                                                         68) or Renderer.is_clicked(
                0, 202, SCREEN_WIDTH, 54):
            old_p_hp = game_state.player.current_hp
            old_e_hp = game_state.combat.enemy.current_hp
            game_state.update_combat()
            self._detect_combat_deltas(game_state, old_p_hp, old_e_hp)

        if game_state.combat is None:
            return

        # Belt hotkeys: [1, 2, 3] or click on command panel
        belt_y_positions = [162, 174, 186]
        for idx, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            by = belt_y_positions[idx]
            if pyxel.btnp(key) or Renderer.is_clicked(6, by, 114, 11):
                old_p_hp = game_state.player.current_hp
                if game_state.player.inventory.use_belt_item(idx, game_state.player):
                    pyxel.play(1, 2)
                    game_state.combat.combat_logs.append(
                        t("combat_belt_use", player=game_state.player.name, slot=idx + 1)
                    )
                    self._detect_combat_deltas(game_state, old_p_hp, game_state.combat.enemy.current_hp)

        # Ability hotkeys: [4, 5] or click on right action panel
        for idx, key in enumerate((pyxel.KEY_4, pyxel.KEY_5)):
            ay = 164 + idx * 16
            if (pyxel.btnp(key) or Renderer.is_clicked(130, ay, 118, 14)) and idx < len(
                    game_state.player.abilities.active):
                ab = game_state.player.abilities.active[idx]
                rem_cd = game_state.combat.get_cooldown(ab)
                if rem_cd <= 0:
                    game_state.combat.queued_ability = ab
                    game_state.combat.combat_logs.append(t("combat_queued", ability=ab.name))
                else:
                    game_state.combat.combat_logs.append(t("combat_cooldown", cooldown=rem_cd))

    def _get_enemy_sprite(self, enemy: Enemy) -> tuple[int, int]:
        arch_id = getattr(enemy, "archetype_id", None)
        if arch_id and arch_id in ENEMY_SPRITE_COORDS:
            return ENEMY_SPRITE_COORDS[arch_id]

        name_lower = enemy.name.lower()
        for key, coords in ENEMY_SPRITE_COORDS.items():
            if key.replace("_", " ") in name_lower:
                return coords

        tier_val = enemy.tier.value if hasattr(enemy.tier, "value") else int(enemy.tier)
        if tier_val >= 4 or "lich" in name_lower or "dragon" in name_lower:
            return (48, 0)
        if "goblin" in name_lower or "scavenger" in name_lower or "cultist" in name_lower:
            return (32, 0)
        return (16, 0)

    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        # Camera screen shake
        if self.shake_frames > 0:
            sx = random.randint(-2, 2)
            sy = random.randint(-2, 2)
            pyxel.camera(sx, sy)
            self.shake_frames -= 1
        else:
            pyxel.camera(0, 0)

        renderer.draw_hud(game_state.player, game_state.floor)

        if game_state.combat is None:
            pyxel.camera(0, 0)
            return

        combat = game_state.combat
        fc = pyxel.frame_count

        # =====================================================================
        # 1. RETRO DUNGEON STAGE ARENA (y=24 to y=92)
        # =====================================================================
        arena_x, arena_y, arena_w, arena_h = 4, 24, SCREEN_WIDTH - 8, 68
        pyxel.rect(arena_x, arena_y, arena_w, arena_h, COLOR_BLACK)

        # Stone wall masonry & vaulted arch columns
        for col_x in [12, 44, 94, 150, 200, 232]:
            pyxel.rect(col_x, arena_y, 8, arena_h - 14, COLOR_NAVY)
            for by in range(arena_y + 4, arena_y + arena_h - 14, 8):
                pyxel.line(col_x, by, col_x + 7, by, COLOR_DARK_BLUE)
                pyxel.pset(col_x + ((by // 4) % 6), by + 3, COLOR_LIGHT_BLUE)

        # Central arched entryway
        pyxel.rect(114, arena_y + 12, 28, arena_h - 26, COLOR_DARK_BLUE)
        pyxel.tri(114, arena_y + 12, 128, arena_y + 2, 141, arena_y + 12, COLOR_DARK_BLUE)
        pyxel.rect(118, arena_y + 16, 20, arena_h - 30, COLOR_BLACK)
        pyxel.tri(118, arena_y + 16, 128, arena_y + 8, 137, arena_y + 16, COLOR_BLACK)

        # Left Torch Sconce & Flame
        ltx, lty = 22, 38
        pyxel.rect(ltx - 1, lty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(ltx, lty + 9, COLOR_DARK_BLUE)
        pyxel.rect(ltx - 1, lty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(ltx, lty + (1 if fc % 4 < 2 else 0), COLOR_YELLOW)
        pyxel.pset(ltx + 1, lty + 2, COLOR_WHITE)
        if fc % 3 == 0:
            pyxel.pset(ltx + (fc % 3) - 1, lty - 2, COLOR_YELLOW)

        # Right Torch Sconce & Flame
        rtx, rty = 230, 38
        pyxel.rect(rtx - 1, rty + 6, 4, 3, COLOR_BROWN)
        pyxel.pset(rtx, rty + 9, COLOR_DARK_BLUE)
        pyxel.rect(rtx - 1, rty + 2, 4, 4, COLOR_ORANGE)
        pyxel.pset(rtx, rty + (0 if fc % 4 < 2 else 1), COLOR_YELLOW)
        pyxel.pset(rtx - 1, rty + 2, COLOR_WHITE)
        if fc % 3 == 1:
            pyxel.pset(rtx - (fc % 3) + 1, rty - 2, COLOR_YELLOW)

        # Cobblestone ground
        ground_y = arena_y + arena_h - 14
        pyxel.rect(arena_x, ground_y, arena_w, 14, COLOR_DARK_BLUE)
        for gx in range(arena_x + 2, arena_x + arena_w - 4, 12):
            pyxel.line(gx, ground_y + 3, gx + 6, ground_y + 3, COLOR_NAVY)
            pyxel.line(gx + 6, ground_y + 8, gx + 11, ground_y + 8, COLOR_NAVY)

        # Status Badges Behind Player (Left of Hero: x=14..48)
        if game_state.player.statuses:
            status_y = 52
            for s in game_state.player.statuses[:3]:
                tag = f"{s.badge} {s.stacks} {s.duration}" if s.max_stacks > 1 else f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = 14
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Status Badges Behind Enemy (Right of Enemy: x=204..238)
        if combat.enemy.statuses:
            status_y = 52
            for s in combat.enemy.statuses[:3]:
                tag = f"{s.badge} {s.stacks} {s.duration}" if s.max_stacks > 1 else f"{s.badge} {s.duration}"
                tw = renderer.get_text_width(tag)
                pill_w = tw + 6
                pill_x = arena_x + arena_w - pill_w - 6
                pyxel.rect(pill_x, status_y - 1, pill_w, 9, COLOR_BLACK)
                pyxel.rectb(pill_x, status_y - 1, pill_w, 9, s.color)
                renderer.draw_text(pill_x + 3, status_y, tag, s.color)
                status_y += 11

        # Combatant Ground Shadows
        pyxel.elli(56, 75, 20, 5, COLOR_NAVY)
        pyxel.elli(176, 75, 22, 5, COLOR_NAVY)

        # Animated Hero Character on Left
        sprite_map = {
            "warrior": (0, 0),
            "rogue": (0, 32),
            "mage": (16, 32),
        }
        pu, pv = sprite_map.get(game_state.player.class_id, (0, 0))
        hero_x, hero_y = 58, 62

        if self.player_flash > 0:
            self.player_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(hero_x, hero_y, 0, pu, pv, 16, 16, 0)

        # Drawn hero blade
        pyxel.line(hero_x + 14, hero_y + 6, hero_x + 21, hero_y - 1, COLOR_CYAN)
        pyxel.line(hero_x + 15, hero_y + 6, hero_x + 22, hero_y - 1, COLOR_WHITE)

        # Animated Enemy Sprite on Right
        eu, ev = self._get_enemy_sprite(combat.enemy)
        enemy_x, enemy_y = 178, 62

        if self.enemy_flash > 0:
            self.enemy_flash -= 1
            for c in range(16):
                pyxel.pal(c, COLOR_WHITE)
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)
            pyxel.pal()
        else:
            pyxel.blt(enemy_x, enemy_y, 0, eu, ev, 16, 16, 0)

        # Ambient floating magic/spore motes around enemy
        spore_coords = [(172, 56), (180, 50), (192, 52), (198, 58), (175, 66), (196, 68)]
        for s_idx, (sx, sy) in enumerate(spore_coords):
            sy_float = sy + int(math.sin((fc + s_idx * 5) * 0.2) * 2)
            if (fc + s_idx * 4) % 20 < 12:
                pyxel.pset(sx, sy_float, COLOR_CYAN if s_idx % 2 == 0 else COLOR_LIME)

        # Floating combat damage popups
        for pop in self.popups:
            renderer.draw_text(pop.x, pop.y, pop.text, pop.color)

        # Speed Button in the bottom-right corner of the dungeon arena
        renderer.draw_button(222, 79, 28, 11, f"[{SPEED_LABELS[self.speed_index]}]", bg_col=COLOR_BLACK,
                             border_col=COLOR_YELLOW, text_col=COLOR_YELLOW)

        # Arena Outer Border
        pyxel.rectb(arena_x, arena_y, arena_w, arena_h, COLOR_DARK_BLUE)

        # =====================================================================
        # 2. STAT & PORTRAIT CARDS (y=94 to y=140)
        # =====================================================================
        card_w, card_h = 122, 46

        # --- PLAYER CARD (Left) ---
        pc_x, pc_y = 4, 94
        renderer.draw_box(pc_x, pc_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=COLOR_LIGHT_BLUE)

        # Portrait Frame & Hero Sprite
        pyxel.rect(pc_x + 3, pc_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(pc_x + 3, pc_y + 3, 20, 20, COLOR_LIGHT_BLUE)
        pyxel.blt(pc_x + 5, pc_y + 5, 0, pu, pv, 16, 16, 0)

        # Player Name & HP Bar
        p_name = game_state.player.name[:14]
        renderer.draw_text(pc_x + 27, pc_y + 4, p_name, COLOR_YELLOW)
        renderer.draw_bar(pc_x + 27, pc_y + 13, 90, 5, game_state.player.current_hp, game_state.player.max_hp,
                          fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        p_stats = game_state.player.effective_stats
        renderer.draw_text(pc_x + 27, pc_y + 20, f"HP:  {game_state.player.current_hp}/{game_state.player.max_hp}",
                           COLOR_WHITE)
        renderer.draw_text(pc_x + 27, pc_y + 28, f"ATK: {p_stats.attack:<3} DEF: {p_stats.defense}", COLOR_WHITE)
        crit_pct = int(p_stats.crit_chance * 100)
        renderer.draw_text(pc_x + 27, pc_y + 36, f"SPD: {p_stats.speed:<3} CRIT: {crit_pct}%", COLOR_WHITE)

        # --- ENEMY CARD (Right) ---
        ec_x, ec_y = 130, 94
        border_col = COLOR_RED if combat.enemy.tier.value >= 3 else COLOR_LIGHT_BLUE
        renderer.draw_box(ec_x, ec_y, card_w, card_h, bg_col=COLOR_DARK_BLUE, border_col=border_col)

        # Portrait Frame & Enemy Sprite
        pyxel.rect(ec_x + 3, ec_y + 3, 20, 20, COLOR_NAVY)
        pyxel.rectb(ec_x + 3, ec_y + 3, 20, 20, border_col)
        pyxel.blt(ec_x + 5, ec_y + 5, 0, eu, ev, 16, 16, 0)

        # Enemy Name & HP Bar
        e_name = combat.enemy.display_name if len(combat.enemy.display_name) <= 14 else combat.enemy.display_name[
                                                                                            :13] + "."
        renderer.draw_text(ec_x + 27, ec_y + 4, e_name, COLOR_YELLOW)
        renderer.draw_bar(ec_x + 27, ec_y + 13, 90, 5, combat.enemy.current_hp, combat.enemy.max_hp,
                          fill_col=COLOR_GREEN, bg_col=COLOR_RED)

        # Numeric Stats
        e_stats = combat.enemy.effective_stats
        renderer.draw_text(ec_x + 27, ec_y + 20, f"HP:  {combat.enemy.current_hp}/{combat.enemy.max_hp}", COLOR_WHITE)
        renderer.draw_text(ec_x + 27, ec_y + 28, f"ATK: {e_stats.attack:<3} DEF: {e_stats.defense}", COLOR_WHITE)
        e_crit = int(e_stats.crit_chance * 100)
        renderer.draw_text(ec_x + 27, ec_y + 36, f"SPD: {e_stats.speed:<3} CRIT: {e_crit}%", COLOR_WHITE)

        # =====================================================================
        # 3. ACTION TICK GAUGES (y=142 to y=156)
        # =====================================================================
        renderer.draw_text(4, 142, t("tick_gauges"), COLOR_YELLOW)

        # Player meter aligned with player card (x=4, w=122); Enemy meter aligned with enemy card (x=130, w=122)
        renderer.draw_bar(4, 150, 122, 5, combat.player_gauge, ACTION_THRESHOLD, fill_col=COLOR_LIGHT_BLUE,
                          bg_col=COLOR_NAVY)
        renderer.draw_bar(130, 150, 122, 5, combat.enemy_gauge, ACTION_THRESHOLD, fill_col=COLOR_ORANGE,
                          bg_col=COLOR_NAVY)

        # =====================================================================
        # 4. SPLIT ACTION COMMAND PANEL (y=158 to y=198)
        # =====================================================================
        cmd_x, cmd_y, cmd_w, cmd_h = 4, 158, SCREEN_WIDTH - 8, 42
        renderer.draw_box(cmd_x, cmd_y, cmd_w, cmd_h, bg_col=COLOR_NAVY, border_col=COLOR_LIGHT_BLUE)

        # Vertical Column Divider
        div_x = cmd_x + 120
        pyxel.line(div_x, cmd_y + 2, div_x, cmd_y + cmd_h - 3, COLOR_LIGHT_BLUE)

        # --- LEFT COLUMN: Belt Quick-Items ---
        inv = game_state.player.inventory
        for b_idx in range(MAX_BELT_SLOTS):
            b_item = inv.belt[b_idx]
            sy = cmd_y + 4 + b_idx * 12

            if b_idx == 0:
                pyxel.tri(cmd_x + 3, sy + 3, cmd_x + 3, sy + 7, cmd_x + 6, sy + 5, COLOR_YELLOW)

            if b_item:
                pyxel.rectb(cmd_x + 8, sy - 1, 108, 10, COLOR_LIGHT_BLUE if b_idx == 0 else COLOR_NAVY)
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx + 1}. {b_item.localized_name[:10]}", COLOR_WHITE)
                renderer.draw_text(cmd_x + 78, sy, f"[+{b_item.heal_amount} HP]", COLOR_LIME)
            else:
                renderer.draw_text(cmd_x + 11, sy, f"{b_idx + 1}. {t('empty_slot_short')}", COLOR_GRAY)

        # --- RIGHT COLUMN: Active Skills ---
        skills = game_state.player.abilities.active
        for a_idx in range(2):
            sy = cmd_y + 7 + a_idx * 16
            if a_idx < len(skills):
                ab = skills[a_idx]
                is_queued = (combat.queued_ability == ab)

                if a_idx == 0:
                    pyxel.line(div_x + 4, sy + 1, div_x + 8, sy + 5, COLOR_WHITE)
                    pyxel.line(div_x + 8, sy + 1, div_x + 4, sy + 5, COLOR_WHITE)
                else:
                    pyxel.rect(div_x + 4, sy + 1, 5, 4, COLOR_WHITE)
                    pyxel.pset(div_x + 5, sy + 2, COLOR_BLACK)
                    pyxel.pset(div_x + 7, sy + 2, COLOR_BLACK)

                ab_name = f"{a_idx + 4}. {ab.localized_name[:12]}"
                renderer.draw_text(div_x + 12, sy, ab_name, COLOR_YELLOW if is_queued else COLOR_WHITE)

                rem_cd = combat.get_cooldown(ab)
                if is_queued:
                    tag = "WAIT"
                    tag_col = COLOR_YELLOW
                elif rem_cd > 0:
                    tag = f"CD:{rem_cd}"
                    tag_col = COLOR_GRAY
                else:
                    tag = "CAST"
                    tag_col = COLOR_LIGHT_BLUE

                renderer.draw_text(cmd_x + cmd_w - 28, sy, tag, tag_col)
            else:
                renderer.draw_text(div_x + 12, sy, f"{a_idx + 4}. (Empty)", COLOR_GRAY)

        # =====================================================================
        # 5. GOTHIC COMBAT ACTIVITY LOG (y=202 to y=254)
        # =====================================================================
        log_x, log_y, log_w, log_h = 4, 202, SCREEN_WIDTH - 8, 52
        renderer.draw_box(log_x, log_y, log_w, log_h, bg_col=COLOR_BLACK, border_col=COLOR_DARK_BLUE)
        pyxel.rectb(log_x + 1, log_y + 1, log_w - 2, log_h - 2, COLOR_NAVY)

        for cx, cy in [
            (log_x + 2, log_y + 2),
            (log_x + log_w - 3, log_y + 2),
            (log_x + 2, log_y + log_h - 3),
            (log_x + log_w - 3, log_y + log_h - 3),
        ]:
            pyxel.pset(cx, cy, COLOR_LIGHT_BLUE)

        renderer.draw_text(log_x + 8, log_y + 3, t("combat_log_header"), COLOR_YELLOW)

        recent_logs = combat.combat_logs if combat.combat_logs else [t("combat_awaiting")]
        wrapped_logs = []
        for line in recent_logs:
            wrapped_logs.extend(renderer.wrap_text(line, max_chars_per_line=39))

        display_entries = wrapped_logs[-4:] if wrapped_logs else []
        line_y = log_y + 13
        for disp in display_entries:
            if "CRIT" in disp or "CRÍTICO" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_YELLOW)
            elif "dmg" in disp or "daño" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_WHITE)
            elif "defeated" in disp or "derrotado" in disp:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_LIME)
            else:
                renderer.draw_text(log_x + 8, line_y, disp, COLOR_GRAY)
            line_y += 9

        if len(wrapped_logs) > 4:
            ind_x, ind_y = log_x + log_w - 8, log_y + log_h - 7
            pyxel.tri(ind_x - 2, ind_y, ind_x + 2, ind_y, ind_x, ind_y + 3, COLOR_YELLOW)

        pyxel.camera(0, 0)
