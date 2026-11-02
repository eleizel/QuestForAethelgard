"""Pygame-CE Spire Exploration Map View.

Matches 16-bit Super Nintendo JRPG aesthetic with 9-slice ornate gold frames,
dynamic cropped headshot bust portraits, rich biome vistas, interactive node medallions,
and bottom node legend bar.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.data.biomes import get_biome
from src.systems.map_gen import NodeType
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer
    from src.systems.map_gen import MapNode


class PygameMapView(PygameView):
    """Visualizes the Spire node tree over 16-bit SNES biome vistas with interactive navigation and top HUD."""

    # Node icon mapping
    NODE_TYPE_NAMES: dict[NodeType, str] = {
        NodeType.COMBAT: "combat",
        NodeType.EVENT: "event",
        NodeType.REST: "rest",
        NodeType.ELITE: "elite",
        NodeType.TREASURE: "treasure",
        NodeType.SHOP: "shop",
        NodeType.BOSS: "boss",
    }

    # Color accents for fallback or glow rings
    NODE_ACCENTS: dict[NodeType, tuple[int, int, int]] = {
        NodeType.COMBAT: (220, 50, 60),      # Crimson
        NodeType.EVENT: (170, 70, 230),     # Mystic Purple
        NodeType.REST: (30, 180, 160),      # Teal
        NodeType.ELITE: (180, 40, 200),     # Horned Violet
        NodeType.TREASURE: (240, 180, 40),  # Gilded Gold
        NodeType.SHOP: (210, 140, 50),      # Warm Bronze
        NodeType.BOSS: (255, 215, 0),       # Sovereign Gold
    }

    LEGEND_ITEMS = [
        ("combat", "Combat"),
        ("event", "Event"),
        ("rest", "Rest"),
        ("elite", "Epic Enemy"),
        ("treasure", "Treasure"),
        ("shop", "Shop"),
        ("boss", "Boss"),
    ]

    def __init__(self) -> None:
        self.pulse_timer: float = 0.0
        self._hovered_node_id: int | None = None
        self._hovered_btn: str | None = None

        # Interactive Button Rects (inset from frame edges to prevent corner overlap)
        self.char_btn_rect = pygame.Rect(716, 12, 98, 32)
        self.inv_btn_rect = pygame.Rect(824, 12, 98, 32)

    def _get_node_screen_pos(self, node: MapNode, total_floors: int, surface_w: int, surface_h: int) -> tuple[int, int]:
        """Compute pixel position for a node with comfortable layout spacing within center viewport."""
        content_top = 118
        content_bottom = 442
        span_h = content_bottom - content_top

        # Floors progress from bottom (0) to top (total_floors - 1)
        y = content_bottom - int((node.floor / max(1, total_floors - 1)) * span_h)

        if node.floor == total_floors - 1:
            return surface_w // 2, y

        # Center lanes comfortably between x=220 and x=740
        lane_span = 500
        lane_w = lane_span // 3
        base_x = 230 + node.lane * lane_w
        wiggle = int(math.sin(node.floor * 1.6 + node.lane * 2.1) * 14)
        return base_x + wiggle, y

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle mouse clicks and keyboard shortcuts on the Spire map."""
        if not session.state.map_graph:
            return

        available = session.state.map_graph.available_nodes

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                session.reset_to_title()
            elif event.key == pygame.K_i:
                session.toggle_inventory()
            elif event.key == pygame.K_c:
                session.toggle_character()
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                if 0 <= idx < len(available):
                    session.select_map_node(available[idx].id)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Top HUD Buttons
            if self.inv_btn_rect.collidepoint(pos):
                session.toggle_inventory()
                return
            elif self.char_btn_rect.collidepoint(pos):
                session.toggle_character()
                return

            if self._hovered_node_id is not None:
                session.select_map_node(self._hovered_node_id)

    def update(self, dt: float, session: GameSession) -> None:
        """Update pulse timer and check mouse hover over nodes and buttons."""
        self.pulse_timer += dt
        pos = pygame.mouse.get_pos()

        if self.inv_btn_rect.collidepoint(pos):
            self._hovered_btn = "inv"
        elif self.char_btn_rect.collidepoint(pos):
            self._hovered_btn = "char"
        else:
            self._hovered_btn = None

        if not session.state.map_graph:
            self._hovered_node_id = None
            return

        total_floors = len(session.state.map_graph.floors)
        available = session.state.map_graph.available_nodes

        self._hovered_node_id = None
        for node in available:
            nx, ny = self._get_node_screen_pos(node, total_floors, 960, 540)
            radius = 24 if node.node_type == NodeType.BOSS else 18
            dist_sq = (pos[0] - nx) ** 2 + (pos[1] - ny) ** 2
            if dist_sq <= radius * radius:
                self._hovered_node_id = node.id
                break

    def _draw_dotted_line(
        self,
        surface: pygame.Surface,
        p1: tuple[int, int],
        p2: tuple[int, int],
        color: tuple[int, int, int],
        dot_len: int = 5,
        gap_len: int = 4,
        width: int = 2,
    ) -> None:
        """Draw an authentic retro dotted connecting path between two nodes."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        if dist <= 0.001:
            return

        ux = dx / dist
        uy = dy / dist

        # Inset start and end so lines don't pierce inside medallions
        offset_start = 18
        offset_end = 18
        curr_dist = offset_start
        max_dist = dist - offset_end

        while curr_dist < max_dist:
            seg_end = min(curr_dist + dot_len, max_dist)
            start_pos = (int(p1[0] + ux * curr_dist), int(p1[1] + uy * curr_dist))
            end_pos = (int(p1[0] + ux * seg_end), int(p1[1] + uy * seg_end))
            pygame.draw.line(surface, color, start_pos, end_pos, width)
            curr_dist += dot_len + gap_len

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render Spire map graph over 16-bit SNES biome vista with top HUD and bottom legend."""
        surface_w = surface.get_width()
        surface_h = surface.get_height()

        # Dark base canvas
        surface.fill((12, 10, 16))

        player = session.player
        current_biome_id = getattr(session.state, "current_biome", "arboretum") or "arboretum"
        biome_def = get_biome(current_biome_id)

        # =========================================================================
        # 1. CENTER MAP VIEWPORT (y = 54 to y = 482)
        # =========================================================================
        map_viewport = pygame.Rect(8, 54, surface_w - 16, 428)

        # Draw Biome Background filling entire viewport
        bg_surf = assets.background_surfaces.get(current_biome_id.lower())
        if bg_surf:
            scaled_bg = pygame.transform.smoothscale(bg_surf, (map_viewport.width, map_viewport.height))
            surface.blit(scaled_bg, map_viewport.topleft)

        # Outer 9-slice ornate frame around map with draw_center=False and edge_margin=24 so background stays 100% luminous
        map_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            map_viewport.width,
            map_viewport.height,
            margin=54,
            draw_center=False,
            edge_margin=24,
        )
        if map_frame:
            surface.blit(map_frame, map_viewport.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), map_viewport, width=3, border_radius=4)

        # =========================================================================
        # 2. ACT & BIOME NAMEPLATE BADGE (Top-Left inside Map)
        # =========================================================================
        badge_rect = pygame.Rect(26, 72, 330, 48)
        badge_bg = pygame.Surface((badge_rect.width, badge_rect.height), pygame.SRCALPHA)
        badge_bg.fill((16, 14, 24, 215))
        surface.blit(badge_bg, badge_rect.topleft)

        # Gold frame around badge
        badge_frame = assets.get_9slice_frame("frame_button_gold", badge_rect.width, badge_rect.height, margin=14)
        if badge_frame:
            surface.blit(badge_frame, badge_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), badge_rect, width=2, border_radius=4)

        # Biome Icon (inset from left corner filigree)
        biome_icon = assets.get_biome_icon(current_biome_id, size=(34, 34))
        if biome_icon:
            surface.blit(biome_icon, (badge_rect.x + 20, badge_rect.y + 7))

        # Act & Biome Name Text
        act_title = f"Act {session.state.act}: {biome_def.name if biome_def else 'The Unknown'}"
        renderer.draw_text(
            surface,
            act_title,
            badge_rect.x + 62,
            badge_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )
        renderer.draw_text(
            surface,
            "Select a path [1-4]",
            badge_rect.x + 62,
            badge_rect.y + 26,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
            font_variant="alagard",
        )

        # =========================================================================
        # 3. NODE GRAPH (Paths & Interactive Medallions)
        # =========================================================================
        map_graph = session.state.map_graph
        if map_graph:
            total_floors = len(map_graph.floors)
            available = map_graph.available_nodes
            pulse_anim = math.sin(self.pulse_timer * 6.0)

            # 3A. Draw Connecting Lines
            for floor_nodes in map_graph.floors:
                for node in floor_nodes:
                    nx, ny = self._get_node_screen_pos(node, total_floors, surface_w, surface_h)
                    for out_id in node.outgoing_ids:
                        out_node = map_graph.nodes_by_id.get(out_id)
                        if out_node:
                            ox, oy = self._get_node_screen_pos(out_node, total_floors, surface_w, surface_h)
                            is_active = (node.visited and out_node.available)
                            if is_active:
                                # Glowing white-gold active line
                                glow_col = (255, 240, 160) if pulse_anim > 0 else (255, 215, 60)
                                self._draw_dotted_line(surface, (nx, ny), (ox, oy), glow_col, dot_len=6, gap_len=3, width=2)
                            elif node.visited and out_node.visited:
                                # Visited completed line
                                self._draw_dotted_line(surface, (nx, ny), (ox, oy), (200, 180, 120), dot_len=5, gap_len=4, width=2)
                            else:
                                # Future faint path
                                self._draw_dotted_line(surface, (nx, ny), (ox, oy), (105, 115, 140), dot_len=4, gap_len=5, width=1)

            # 3B. Draw Nodes
            for floor_nodes in map_graph.floors:
                for node in floor_nodes:
                    nx, ny = self._get_node_screen_pos(node, total_floors, surface_w, surface_h)
                    is_avail = node.available
                    is_hovered = (self._hovered_node_id == node.id)
                    is_boss = (node.node_type == NodeType.BOSS)
                    ntype_str = self.NODE_TYPE_NAMES.get(node.node_type, "combat")

                    icon_size = (44, 44) if is_boss else (32, 32)
                    radius = icon_size[0] // 2

                    # Pulsing glow ring for available nodes
                    if is_avail:
                        glow_r = radius + 4 + int(pulse_anim * 3)
                        pygame.draw.circle(surface, (255, 236, 39), (nx, ny), glow_r, width=2)
                        if is_hovered:
                            pygame.draw.circle(surface, (255, 255, 255), (nx, ny), glow_r + 2, width=1)

                    # Node icon medallion
                    node_icon = assets.get_node_icon(ntype_str, size=icon_size)
                    if node_icon:
                        # If node is not available and not visited, dim it slightly
                        if not is_avail and not node.visited:
                            dimmed = node_icon.copy()
                            dim_mask = pygame.Surface(icon_size, pygame.SRCALPHA)
                            dim_mask.fill((20, 20, 30, 90))
                            dimmed.blit(dim_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
                            surface.blit(dimmed, (nx - radius, ny - radius))
                        else:
                            surface.blit(node_icon, (nx - radius, ny - radius))
                    else:
                        # Fallback colored circle if asset missing
                        base_col = self.NODE_ACCENTS.get(node.node_type, (200, 200, 200))
                        fill_col = base_col if (is_avail or node.visited) else (60, 65, 80)
                        pygame.draw.circle(surface, fill_col, (nx, ny), radius)
                        pygame.draw.circle(surface, (218, 165, 32), (nx, ny), radius, width=2)

                    # Shortcut Key Badge below available nodes
                    if is_avail:
                        try:
                            idx = available.index(node)
                            if 0 <= idx < 4:
                                key_label = str(idx + 1)
                                k_rect = pygame.Rect(nx - 9, ny + radius + 3, 18, 16)
                                pygame.draw.rect(surface, (18, 16, 26), k_rect, border_radius=3)
                                pygame.draw.rect(surface, (218, 165, 32), k_rect, width=1, border_radius=3)
                                renderer.draw_text(
                                    surface,
                                    key_label,
                                    k_rect.centerx,
                                    k_rect.y + 1,
                                    token=ThemeToken.TEXT_HIGHLIGHT,
                                    size=12,
                                    bold=True,
                                    align="center",
                                    font_variant="alagard",
                                )
                        except ValueError:
                            pass

        # 3C. Tooltip for hovered node
        if self._hovered_node_id is not None and map_graph:
            h_node = map_graph.nodes_by_id.get(self._hovered_node_id)
            if h_node:
                mouse_pos = pygame.mouse.get_pos()
                tip_text = f"{h_node.node_type.value} [CLICK / 1-4]"
                tip_rect = pygame.Rect(mouse_pos[0] + 14, mouse_pos[1] - 28, 170, 26)
                pygame.draw.rect(surface, (20, 18, 28), tip_rect, border_radius=4)
                pygame.draw.rect(surface, (255, 215, 60), tip_rect, width=1, border_radius=4)
                renderer.draw_text(
                    surface,
                    tip_text,
                    tip_rect.centerx,
                    tip_rect.y + 5,
                    token=ThemeToken.TEXT_HIGHLIGHT,
                    size=12,
                    bold=True,
                    align="center",
                    font_variant="alagard",
                )

        # =========================================================================
        # 4. TOP HUD BAR (y = 6 to y = 50)
        # =========================================================================
        hud_rect = pygame.Rect(8, 6, surface_w - 16, 46)
        hud_bg = pygame.Surface((hud_rect.width, hud_rect.height), pygame.SRCALPHA)
        hud_bg.fill((18, 15, 24, 240))
        surface.blit(hud_bg, hud_rect.topleft)

        # 9-slice clean gold frame
        hud_frame = assets.get_9slice_frame("frame_gold_clean", hud_rect.width, hud_rect.height, margin=16)
        if hud_frame:
            surface.blit(hud_frame, hud_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), hud_rect, width=2, border_radius=4)

        # 4A. Character Headshot Bust (Neck up, inset from left corner filigree)
        bust_rect = pygame.Rect(hud_rect.x + 28, hud_rect.y + 5, 36, 36)
        bust_surf = assets.get_bust_portrait(player.class_id, size=(36, 36))
        if bust_surf:
            surface.blit(bust_surf, bust_rect.topleft)
            # Gold filigree border around bust
            pygame.draw.rect(surface, (218, 165, 32), bust_rect, width=1, border_radius=3)

        # 4B. Name, Class, Level
        info_x = bust_rect.right + 12
        name_part = f"{player.name}"
        class_part = f" ({player.class_id.capitalize()})"
        lvl_part = f" Lv.{player.level}"

        # Draw compound colored text
        r_name = renderer.draw_text(
            surface, name_part, info_x, hud_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True, font_variant="alagard"
        )
        r_class = renderer.draw_text(
            surface, class_part, r_name.right, hud_rect.y + 8,
            token=ThemeToken.TEXT_NORMAL, size=14, bold=True, font_variant="alagard"
        )
        renderer.draw_text(
            surface, lvl_part, r_class.right, hud_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True, font_variant="alagard"
        )

        # 4C. EXP Text & Bar
        exp_next = max(1, getattr(player, "exp_to_next_level", 100))
        exp_curr = getattr(player, "experience", 0)
        exp_str = f"EXP: {exp_curr}/{exp_next}"
        r_exp = renderer.draw_text(
            surface, exp_str, info_x, hud_rect.y + 26,
            token=ThemeToken.TEXT_MUTED, size=11, bold=False, font_variant="alagard"
        )

        # EXP Bar
        exp_bar_x = r_exp.right + 8
        exp_bar_rect = pygame.Rect(exp_bar_x, hud_rect.y + 28, 100, 10)
        pygame.draw.rect(surface, (30, 32, 45), exp_bar_rect, border_radius=2)
        exp_ratio = min(1.0, max(0.0, exp_curr / exp_next))
        if exp_ratio > 0:
            fill_w = max(2, int(exp_bar_rect.width * exp_ratio))
            pygame.draw.rect(surface, (41, 173, 255), (exp_bar_rect.x, exp_bar_rect.y, fill_w, exp_bar_rect.height), border_radius=2)
        pygame.draw.rect(surface, (150, 155, 175), exp_bar_rect, width=1, border_radius=2)

        # Vertical Divider
        div1_x = exp_bar_rect.right + 16
        renderer.draw_text(surface, "|", div1_x, hud_rect.y + 16, token=ThemeToken.BORDER_MUTED, size=14, font_variant="alagard")

        # 4D. Gold
        gold_x = div1_x + 14
        renderer.draw_text(
            surface,
            f"Gold: {player.gold}",
            gold_x,
            hud_rect.y + 16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # Vertical Divider
        div2_x = gold_x + 95
        renderer.draw_text(surface, "|", div2_x, hud_rect.y + 16, token=ThemeToken.BORDER_MUTED, size=14, font_variant="alagard")

        # 4E. Floor
        floor_x = div2_x + 14
        renderer.draw_text(
            surface,
            f"Floor {session.state.floor}",
            floor_x,
            hud_rect.y + 16,
            token=ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # 4F. Top Right HUD Action Buttons ([CHAR] and [INV])
        # CHAR button
        c_hover = (self._hovered_btn == "char")
        c_frame = assets.get_9slice_frame("frame_button_gold", self.char_btn_rect.width, self.char_btn_rect.height, margin=14)
        if c_frame:
            surface.blit(c_frame, self.char_btn_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.char_btn_rect, width=2, border_radius=4)
        if c_hover:
            pygame.draw.rect(surface, (255, 255, 255), self.char_btn_rect, width=1, border_radius=4)
        renderer.draw_text(
            surface,
            "[C] CHAR",
            self.char_btn_rect.centerx,
            self.char_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if c_hover else ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # INV button
        i_hover = (self._hovered_btn == "inv")
        i_frame = assets.get_9slice_frame("frame_button_gold", self.inv_btn_rect.width, self.inv_btn_rect.height, margin=14)
        if i_frame:
            surface.blit(i_frame, self.inv_btn_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.inv_btn_rect, width=2, border_radius=4)
        if i_hover:
            pygame.draw.rect(surface, (255, 255, 255), self.inv_btn_rect, width=1, border_radius=4)
        renderer.draw_text(
            surface,
            "[I] INV",
            self.inv_btn_rect.centerx,
            self.inv_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if i_hover else ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # =========================================================================
        # 5. BOTTOM LEGEND BAR (y = 488 to y = 534)
        # =========================================================================
        legend_rect = pygame.Rect(8, 488, surface_w - 16, 46)
        leg_bg = pygame.Surface((legend_rect.width, legend_rect.height), pygame.SRCALPHA)
        leg_bg.fill((18, 15, 24, 240))
        surface.blit(leg_bg, legend_rect.topleft)

        leg_frame = assets.get_9slice_frame("frame_gold_clean", legend_rect.width, legend_rect.height, margin=16)
        if leg_frame:
            surface.blit(leg_frame, legend_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), legend_rect, width=2, border_radius=4)

        # 7 items evenly spaced with horizontal padding to keep frame corners clear
        pad_x = 44
        usable_w = legend_rect.width - 2 * pad_x
        slot_w = usable_w / len(self.LEGEND_ITEMS)
        for i, (n_type, label) in enumerate(self.LEGEND_ITEMS):
            slot_center_x = legend_rect.x + pad_x + int((i + 0.5) * slot_w)
            icon = assets.get_node_icon(n_type, size=(22, 22))

            # Compute width of icon + label to center them together
            font = renderer.get_font(size=12, variant="alagard")
            txt_surf = font.render(label, True, (255, 241, 232))
            pair_w = 24 + 6 + txt_surf.get_width()
            start_x = slot_center_x - pair_w // 2

            if icon:
                surface.blit(icon, (start_x, legend_rect.centery - 11))
            surface.blit(txt_surf, (start_x + 28, legend_rect.centery - txt_surf.get_height() // 2))

            # Divider line between items (except after the last one)
            if i < len(self.LEGEND_ITEMS) - 1:
                div_x = legend_rect.x + pad_x + int((i + 1) * slot_w)
                pygame.draw.line(
                    surface,
                    (90, 85, 110),
                    (div_x, legend_rect.y + 12),
                    (div_x, legend_rect.bottom - 12),
                    1,
                )
