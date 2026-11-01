"""Pygame-CE Spire Exploration Map View."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.systems.map_gen import NodeType
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer
    from src.systems.map_gen import MapNode


class PygameMapView(PygameView):
    """Visualizes the Spire node tree over 16-bit SNES biome vistas with interactive navigation and top HUD."""

    NODE_COLORS: dict[NodeType, tuple[int, int, int]] = {
        NodeType.COMBAT: (220, 50, 60),      # Crimson
        NodeType.ELITE: (160, 40, 180),     # Dark Purple
        NodeType.REST: (230, 140, 30),      # Warm Ember
        NodeType.SHOP: (235, 180, 50),      # Merchant Gold
        NodeType.TREASURE: (245, 210, 60),  # Chest Gold
        NodeType.EVENT: (40, 175, 220),     # Arcane Cyan
        NodeType.BOSS: (240, 40, 40),       # Sovereign Blood Red
    }

    def __init__(self) -> None:
        self.pulse_timer: float = 0.0
        self._hovered_node_id: int | None = None
        self._hovered_btn: str | None = None

    def _get_node_screen_pos(self, node: MapNode, total_floors: int, surface_w: int, surface_h: int) -> tuple[int, int]:
        """Compute pixel position for a node with comfortable layout spacing."""
        content_top = 80
        content_bottom = surface_h - 60
        span_h = content_bottom - content_top

        # Floors progress from bottom (0) to top (total_floors - 1)
        y = content_bottom - int((node.floor / max(1, total_floors - 1)) * span_h)

        if node.floor == total_floors - 1:
            return surface_w // 2, y

        lane_span = surface_w - 240
        lane_w = lane_span // 3
        base_x = 120 + node.lane * lane_w
        wiggle = int(math.sin(node.floor * 1.5 + node.lane * 2.0) * 12)
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
            inv_btn = pygame.Rect(630, 10, 95, 32)
            char_btn = pygame.Rect(735, 10, 105, 32)
            esc_btn = pygame.Rect(850, 10, 95, 32)

            if inv_btn.collidepoint(pos):
                session.toggle_inventory()
                return
            elif char_btn.collidepoint(pos):
                session.toggle_character()
                return
            elif esc_btn.collidepoint(pos):
                session.reset_to_title()
                return

            if self._hovered_node_id is not None:
                session.select_map_node(self._hovered_node_id)

    def update(self, dt: float, session: GameSession) -> None:
        """Update pulse timer and check mouse hover over nodes and buttons."""
        self.pulse_timer += dt
        pos = pygame.mouse.get_pos()

        inv_btn = pygame.Rect(630, 10, 95, 32)
        char_btn = pygame.Rect(735, 10, 105, 32)
        esc_btn = pygame.Rect(850, 10, 95, 32)

        if inv_btn.collidepoint(pos):
            self._hovered_btn = "inv"
        elif char_btn.collidepoint(pos):
            self._hovered_btn = "char"
        elif esc_btn.collidepoint(pos):
            self._hovered_btn = "esc"
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
            dist_sq = (pos[0] - nx) ** 2 + (pos[1] - ny) ** 2
            if dist_sq <= 18 * 18:
                self._hovered_node_id = node.id
                break

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render Spire map graph over 16-bit SNES biome vista with top status HUD."""
        surface_w = surface.get_width()
        surface_h = surface.get_height()

        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=145)

        # Top HUD Bar
        hud_rect = pygame.Rect(0, 0, surface_w, 52)
        renderer.draw_panel(
            surface,
            hud_rect,
            bg_token=ThemeToken.PANEL_BG,
            border_token=ThemeToken.BORDER,
            border_width=1,
            border_radius=0,
        )

        player = session.player
        # Player name & class
        renderer.draw_text(
            surface,
            f"{player.name.upper()} (LVL {player.level} {player.class_id.capitalize()})",
            20,
            16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
        )

        # Health bar
        hp_bar_rect = pygame.Rect(260, 15, 130, 22)
        renderer.draw_progress_bar(
            surface,
            hp_bar_rect,
            current=player.current_hp,
            maximum=player.max_hp,
            fill_token=ThemeToken.HP_FILL,
            label=f"HP: {player.current_hp}/{player.max_hp}",
        )

        # Gold & Floor
        renderer.draw_text(
            surface,
            f"{player.gold}G",
            405,
            17,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
        )

        act_text = f"ACT {session.state.act} - F{session.state.floor}"
        renderer.draw_text(
            surface,
            act_text,
            475,
            17,
            token=ThemeToken.TEXT_MUTED,
            size=13,
            bold=True,
        )

        # Interactive HUD Action Buttons
        inv_btn = pygame.Rect(630, 10, 95, 32)
        renderer.draw_button(surface, inv_btn, "[I] POUCH", is_hovered=(self._hovered_btn == "inv"), accent_token=ThemeToken.ACCENT_PRIMARY, font_size=11)

        char_btn = pygame.Rect(735, 10, 105, 32)
        renderer.draw_button(surface, char_btn, "[C] STATS", is_hovered=(self._hovered_btn == "char"), accent_token=ThemeToken.ACCENT_SECONDARY, font_size=11)

        esc_btn = pygame.Rect(850, 10, 95, 32)
        renderer.draw_button(surface, esc_btn, "[ESC] QUIT", is_hovered=(self._hovered_btn == "esc"), accent_token=ThemeToken.BORDER_MUTED, font_size=11)

        # Draw Node Tree
        map_graph = session.state.map_graph
        if not map_graph:
            return

        total_floors = len(map_graph.floors)

        # 1. Connecting Paths
        for floor_nodes in map_graph.floors:
            for node in floor_nodes:
                nx, ny = self._get_node_screen_pos(node, total_floors, surface_w, surface_h)
                for out_id in node.outgoing_ids:
                    out_node = map_graph.nodes_by_id.get(out_id)
                    if out_node:
                        ox, oy = self._get_node_screen_pos(out_node, total_floors, surface_w, surface_h)
                        is_active_path = (node.visited and out_node.available)
                        line_color = (
                            renderer.color(ThemeToken.ACCENT_PRIMARY)
                            if is_active_path else
                            renderer.color(ThemeToken.BORDER_MUTED)
                        )
                        pygame.draw.line(surface, line_color, (nx, ny), (ox, oy), 2 if is_active_path else 1)

        # 2. Nodes
        pulse_scale = 1.0 + 0.15 * math.sin(self.pulse_timer * 6.0)

        for floor_nodes in map_graph.floors:
            for node in floor_nodes:
                nx, ny = self._get_node_screen_pos(node, total_floors, surface_w, surface_h)
                base_color = self.NODE_COLORS.get(node.node_type, (200, 200, 200))

                radius = 14
                if node.available:
                    radius = int(14 * pulse_scale)
                elif node.visited:
                    radius = 11

                if node.available:
                    pygame.draw.circle(surface, (255, 236, 39), (nx, ny), radius + 4, width=2)

                fill_color = base_color if (node.available or node.visited) else (50, 55, 65)
                pygame.draw.circle(surface, fill_color, (nx, ny), radius)
                pygame.draw.circle(surface, (20, 20, 25), (nx, ny), radius, width=1)

                icon_letter = node.node_type.name[0]
                text_col = ThemeToken.TEXT_NORMAL if (node.available or node.visited) else ThemeToken.TEXT_MUTED
                renderer.draw_text(surface, icon_letter, nx, ny - 7, token=text_col, size=12, bold=True, align="center")

        # 3. Tooltip
        if self._hovered_node_id is not None:
            h_node = map_graph.nodes_by_id.get(self._hovered_node_id)
            if h_node:
                mouse_pos = pygame.mouse.get_pos()
                tip_text = f"{h_node.node_type.value} [CLICK / 1-4]"
                tip_rect = pygame.Rect(mouse_pos[0] + 12, mouse_pos[1] - 28, 160, 26)
                renderer.draw_panel(surface, tip_rect, border_token=ThemeToken.ACCENT_PRIMARY)
                renderer.draw_text(surface, tip_text, tip_rect.centerx, tip_rect.centery - 7, token=ThemeToken.TEXT_HIGHLIGHT, size=12, bold=True, align="center")
