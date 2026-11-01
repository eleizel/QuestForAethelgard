"""Pygame-CE Class Selection & Route Customization View.

Authentic 16-bit Super Nintendo Golden Age RPG design (Secret of Evermore, Terranigma, Chrono Trigger).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from src.core.game_state import GameMode
from src.core.i18n import t
from src.core.theme import ThemeToken
from src.data.classes import CLASS_REGISTRY
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


CLASS_ROLES: dict[str, str] = {
    "warrior": "[Martial/Tank]",
    "rogue": "[Agile/Crit]",
    "mage": "[Arcane/Burst]",
    "paladin": "[Holy/Defense]",
    "berserker": "[Rage/Brawler]",
    "venomancer": "[DoT/Toxin]",
    "duelist": "[Speed/Parry]",
    "archmage": "[Burst/Arcane]",
    "warlock": "[Dark/LifeDrain]",
}


class PygameClassSelectView(PygameView):
    """Class selection screen pulling dynamically from CLASS_REGISTRY with 16-bit sprites and portraits."""

    STARTER_CLASSES = ["warrior", "rogue", "mage"]

    def __init__(self) -> None:
        self.selected_index: int = 0
        self.route_mode: str = "FATE"  # "FATE" or "PATHFINDER"
        self._hovered_btn: str | None = None
        self._hovered_card: int | None = None

    @property
    def selected_class_id(self) -> str:
        return self.STARTER_CLASSES[self.selected_index]

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard shortcuts and mouse clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                session.switch_mode(GameMode.WELCOME)
            elif event.key == pygame.K_1:
                self.selected_index = 0
            elif event.key == pygame.K_2:
                self.selected_index = 1
            elif event.key == pygame.K_3:
                self.selected_index = 2
            elif event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % len(self.STARTER_CLASSES)
            elif event.key == pygame.K_RIGHT:
                self.selected_index = (self.selected_index + 1) % len(self.STARTER_CLASSES)
            elif event.key in (pygame.K_b, pygame.K_t):
                self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection(session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Class card clicks
            for idx in range(3):
                card_rect = pygame.Rect(30 + idx * 310, 80, 280, 116)
                if card_rect.collidepoint(pos):
                    self.selected_index = idx
                    return

            # Back button
            back_rect = pygame.Rect(30, 476, 160, 44)
            if back_rect.collidepoint(pos):
                session.switch_mode(GameMode.WELCOME)
                return

            # Route toggle button
            route_rect = pygame.Rect(280, 476, 400, 44)
            if route_rect.collidepoint(pos):
                self.route_mode = "PATHFINDER" if self.route_mode == "FATE" else "FATE"
                return

            # Begin Journey button
            start_rect = pygame.Rect(770, 476, 160, 44)
            if start_rect.collidepoint(pos):
                self._confirm_selection(session)
                return

    def _confirm_selection(self, session: GameSession) -> None:
        """Begin new run and advance to Map or Biome Selection."""
        session.start_new_game(class_id=self.selected_class_id, route_mode=self.route_mode)
        if self.route_mode == "PATHFINDER":
            session.switch_mode(GameMode.BIOME_SELECT)
        else:
            session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Track mouse hover over buttons and cards."""
        pos = pygame.mouse.get_pos()

        self._hovered_card = None
        for idx in range(3):
            card_rect = pygame.Rect(30 + idx * 310, 80, 280, 116)
            if card_rect.collidepoint(pos):
                self._hovered_card = idx
                break

        back_rect = pygame.Rect(30, 476, 160, 44)
        route_rect = pygame.Rect(280, 476, 400, 44)
        start_rect = pygame.Rect(770, 476, 160, 44)

        if back_rect.collidepoint(pos):
            self._hovered_btn = "back"
        elif route_rect.collidepoint(pos):
            self._hovered_btn = "route"
        elif start_rect.collidepoint(pos):
            self._hovered_btn = "start"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render class selection with authentic 16-bit SNES aesthetics."""
        # 1. Background image (Clean balcony gothic background)
        assets.draw_background(surface, "class_select")

        w = surface.get_width()

        # 2. Ornate Top Header Plaque
        header_rect = pygame.Rect(w // 2 - 250, 14, 500, 56)
        self._draw_ornate_panel(surface, header_rect, bg_color=(12, 10, 20, 235), border_color=(212, 163, 60), double_border=True)

        renderer.draw_text(
            surface,
            t("class_select_title") if t("class_select_title") != "class_select_title" else "CHOOSE YOUR CHAMPION",
            w // 2,
            24,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=18,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            "Each archetype possesses distinct stat masteries and promotions at Level 10.",
            w // 2,
            46,
            token=ThemeToken.TEXT_MUTED,
            size=11,
            align="center",
        )

        # 3. Top Gallery: 3 Class Cards (Warrior, Rogue, Mage)
        for idx, cid in enumerate(self.STARTER_CLASSES):
            cdef = CLASS_REGISTRY[cid]
            card_rect = pygame.Rect(30 + idx * 310, 80, 280, 116)
            is_selected = (self.selected_index == idx)
            is_hovered = (self._hovered_card == idx)

            border_col = (255, 215, 0) if is_selected else ((200, 160, 80) if is_hovered else (80, 70, 95))
            self._draw_ornate_panel(
                surface,
                card_rect,
                bg_color=(18, 14, 28, 235) if is_selected else (14, 12, 22, 210),
                border_color=border_col,
                double_border=is_selected,
                highlight=is_selected,
            )

            # Sprite on pedestal (left)
            sprite = assets.get_class_sprite(cid)
            if sprite:
                target_w, target_h = 75, 96
                scaled_sprite = pygame.transform.smoothscale(sprite, (target_w, target_h))
                surface.blit(scaled_sprite, (card_rect.x + 12, card_rect.y + 10))

            # Class Crest Icon + Name (right)
            crest = assets.get_class_crest(cid, size=(28, 28))
            if crest:
                surface.blit(crest, (card_rect.x + 98, card_rect.y + 26))

            name_color = ThemeToken.TEXT_HIGHLIGHT if is_selected else ThemeToken.TEXT_NORMAL
            renderer.draw_text(
                surface,
                f"[{idx+1}] {cdef.localized_name}",
                card_rect.x + 132,
                card_rect.y + 30,
                token=name_color,
                size=15,
                bold=True,
                align="left",
            )

            # Role tag
            role_text = CLASS_ROLES.get(cid, "[Hero]")
            renderer.draw_text(
                surface,
                role_text,
                card_rect.x + 102,
                card_rect.y + 64,
                token=ThemeToken.TEXT_MUTED if not is_selected else ThemeToken.ACCENT_SECONDARY,
                size=12,
                bold=is_selected,
                align="left",
            )

        # 4. Bottom Detail Panel
        detail_rect = pygame.Rect(30, 206, 900, 256)
        self._draw_ornate_panel(surface, detail_rect, bg_color=(12, 10, 22, 240), border_color=(200, 160, 60), double_border=True)

        sel_cid = self.selected_class_id
        sel_cdef = CLASS_REGISTRY[sel_cid]

        # 4a. Left column: Bust Portrait Frame
        portrait_frame = pygame.Rect(46, 220, 150, 182)
        self._draw_ornate_panel(surface, portrait_frame, bg_color=(8, 6, 14, 255), border_color=(180, 140, 50), double_border=True)

        portrait = assets.get_class_portrait(sel_cid)
        if portrait:
            # Fit inside portrait_frame nicely
            target_pw, target_ph = 140, 172
            scaled_p = pygame.transform.smoothscale(portrait, (target_pw, target_ph))
            surface.blit(scaled_p, (portrait_frame.centerx - target_pw // 2, portrait_frame.centery - target_ph // 2))

        # Class Name & Role beneath portrait
        tag_rect = pygame.Rect(46, 408, 150, 42)
        self._draw_ornate_panel(surface, tag_rect, bg_color=(20, 16, 32, 240), border_color=(140, 110, 40))
        renderer.draw_text(
            surface,
            sel_cdef.localized_name,
            tag_rect.centerx,
            tag_rect.y + 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=13,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            CLASS_ROLES.get(sel_cid, ""),
            tag_rect.centerx,
            tag_rect.y + 22,
            token=ThemeToken.TEXT_MUTED,
            size=11,
            align="center",
        )

        # 4b. Right Header & Description
        renderer.draw_text(
            surface,
            sel_cdef.localized_name,
            216,
            222,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=22,
            bold=True,
            align="left",
        )
        renderer.draw_text(
            surface,
            sel_cdef.localized_description,
            216,
            248,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            align="left",
        )

        # 4c. Sub-box 1: STARTING STATS
        stats_rect = pygame.Rect(216, 276, 200, 174)
        self._draw_sub_box(surface, renderer, stats_rect, "STARTING STATS")
        b_stats = sel_cdef.base_stats
        stat_items = [
            ("hp", "HP", str(b_stats.max_hp)),
            ("atk", "ATK", str(b_stats.attack)),
            ("def", "DEF", str(b_stats.defense)),
            ("spd", "SPD", str(b_stats.speed)),
            ("crit", "CRIT", f"{int(b_stats.crit_chance * 100)}%"),
        ]
        for s_idx, (icon_key, label, val) in enumerate(stat_items):
            y_pos = stats_rect.y + 36 + s_idx * 26
            icon = assets.get_stat_icon(icon_key, size=(20, 20))
            if icon:
                surface.blit(icon, (stats_rect.x + 16, y_pos))
            renderer.draw_text(
                surface,
                f"{label.ljust(5)}: {val}",
                stats_rect.x + 46,
                y_pos + 2,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
                bold=True,
                align="left",
            )

        # 4d. Sub-box 2: GROWTH / LEVEL
        growth_rect = pygame.Rect(430, 276, 200, 174)
        self._draw_sub_box(surface, renderer, growth_rect, "GROWTH / LEVEL")
        g_stats = sel_cdef.growth_per_level
        growth_items = [
            ("hp", "HP", f"+{g_stats.max_hp}"),
            ("atk", "ATK", f"+{g_stats.attack}"),
            ("def", "DEF", f"+{g_stats.defense}"),
            ("spd", "SPD", f"+{g_stats.speed}"),
            ("crit", "CRIT", f"+{g_stats.crit_chance * 100:.1f}%"),
        ]
        for s_idx, (icon_key, label, val) in enumerate(growth_items):
            y_pos = growth_rect.y + 36 + s_idx * 26
            icon = assets.get_stat_icon(icon_key, size=(20, 20))
            if icon:
                surface.blit(icon, (growth_rect.x + 16, y_pos))
            renderer.draw_text(
                surface,
                f"{label.ljust(5)}: {val}",
                growth_rect.x + 46,
                y_pos + 2,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
                bold=True,
                align="left",
            )

        # 4e. Sub-box 3: PROMOTES TO
        promo_rect = pygame.Rect(644, 276, 270, 174)
        self._draw_sub_box(surface, renderer, promo_rect, "PROMOTES TO")
        for p_idx, promo_cid in enumerate(sel_cdef.promotions[:2]):
            badge_rect = pygame.Rect(promo_rect.x + 12, promo_rect.y + 36 + p_idx * 64, 246, 54)
            self._draw_ornate_panel(surface, badge_rect, bg_color=(20, 16, 32, 220), border_color=(150, 120, 50))

            p_crest = assets.get_class_crest(promo_cid, size=(32, 32))
            if p_crest:
                surface.blit(p_crest, (badge_rect.x + 12, badge_rect.y + 11))

            p_def = CLASS_REGISTRY.get(promo_cid)
            p_name = p_def.localized_name if p_def else promo_cid.capitalize()
            renderer.draw_text(
                surface,
                p_name,
                badge_rect.x + 54,
                badge_rect.y + 10,
                token=ThemeToken.TEXT_HIGHLIGHT,
                size=14,
                bold=True,
                align="left",
            )

            p_role = CLASS_ROLES.get(promo_cid, "[Promoted]")
            renderer.draw_text(
                surface,
                p_role,
                badge_rect.x + 54,
                badge_rect.y + 30,
                token=ThemeToken.TEXT_MUTED,
                size=11,
                align="left",
            )

        # 5. Bottom Action Bar
        back_rect = pygame.Rect(30, 476, 160, 44)
        self._draw_footer_button(
            surface,
            renderer,
            back_rect,
            "[ESC] < BACK",
            is_hovered=(self._hovered_btn == "back"),
        )

        route_rect = pygame.Rect(280, 476, 400, 44)
        route_text = f"[B] ROUTE: {self.route_mode}  ({'Procedural Tree' if self.route_mode == 'FATE' else 'Choice Matrix'})"
        self._draw_footer_button(
            surface,
            renderer,
            route_rect,
            route_text,
            is_hovered=(self._hovered_btn == "route"),
            accent_gold=True,
        )

        start_rect = pygame.Rect(770, 476, 160, 44)
        self._draw_footer_button(
            surface,
            renderer,
            start_rect,
            "BEGIN >",
            is_hovered=(self._hovered_btn == "start"),
            accent_gold=True,
        )

    def _draw_ornate_panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        bg_color: tuple[int, int, int, int],
        border_color: tuple[int, int, int],
        double_border: bool = False,
        highlight: bool = False,
    ) -> None:
        """Draw a gothic ornate filigree panel with beveled corners and glowing border."""
        # Background alpha fill
        panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel_surf.fill(bg_color)
        surface.blit(panel_surf, (rect.x, rect.y))

        # Outer border
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=4)

        if double_border:
            inner_rect = rect.inflate(-6, -6)
            inner_col = (border_color[0] // 2, border_color[1] // 2, border_color[2] // 2)
            pygame.draw.rect(surface, inner_col, inner_rect, width=1, border_radius=2)

        if highlight:
            # Golden corner accents
            corner_len = 8
            gold = (255, 230, 120)
            # Top-left
            pygame.draw.line(surface, gold, (rect.x, rect.y), (rect.x + corner_len, rect.y), 2)
            pygame.draw.line(surface, gold, (rect.x, rect.y), (rect.x, rect.y + corner_len), 2)
            # Top-right
            pygame.draw.line(surface, gold, (rect.right - corner_len, rect.y), (rect.right, rect.y), 2)
            pygame.draw.line(surface, gold, (rect.right, rect.y), (rect.right, rect.y + corner_len), 2)
            # Bottom-left
            pygame.draw.line(surface, gold, (rect.x, rect.bottom), (rect.x + corner_len, rect.bottom), 2)
            pygame.draw.line(surface, gold, (rect.x, rect.bottom - corner_len), (rect.x, rect.bottom), 2)
            # Bottom-right
            pygame.draw.line(surface, gold, (rect.right - corner_len, rect.bottom), (rect.right, rect.bottom), 2)
            pygame.draw.line(surface, gold, (rect.right, rect.bottom - corner_len), (rect.right, rect.bottom), 2)

    def _draw_sub_box(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        rect: pygame.Rect,
        title: str,
    ) -> None:
        """Draw an inner sub-panel with gold title ribbon and filigree divider."""
        self._draw_ornate_panel(surface, rect, bg_color=(16, 12, 24, 220), border_color=(120, 95, 45))

        # Title ribbon divider
        title_y = rect.y + 12
        renderer.draw_text(
            surface,
            title,
            rect.centerx,
            title_y,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=12,
            bold=True,
            align="center",
        )
        line_y = rect.y + 28
        pygame.draw.line(surface, (160, 130, 50), (rect.x + 12, line_y), (rect.right - 12, line_y), 1)

    def _draw_footer_button(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        rect: pygame.Rect,
        label: str,
        is_hovered: bool = False,
        accent_gold: bool = False,
    ) -> None:
        """Draw a retro button matching the golden age gothic theme."""
        if is_hovered:
            border_col = (255, 230, 100) if accent_gold else (220, 220, 220)
            bg_col = (36, 28, 52, 250)
            text_tok = ThemeToken.TEXT_HIGHLIGHT
        else:
            border_col = (180, 140, 50) if accent_gold else (100, 90, 115)
            bg_col = (20, 16, 30, 235)
            text_tok = ThemeToken.TEXT_NORMAL

        self._draw_ornate_panel(
            surface,
            rect,
            bg_color=bg_col,
            border_color=border_col,
            double_border=True,
            highlight=is_hovered,
        )

        renderer.draw_text(
            surface,
            label,
            rect.centerx,
            rect.centery,
            token=text_tok,
            size=13,
            bold=True,
            align="center",
        )
