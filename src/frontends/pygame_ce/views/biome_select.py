"""Pygame-CE 16-bit SNES Biome Selection View for Pathfinder expedition routes.

Authentic Super Nintendo Golden Age RPG design:
- Crimson moon kingdom balcony background with ambient vignette
- TopHUDComponent displaying champion stats, EXP, gold, and floor
- Ornate Act Expedition Route header plaque
- Dual side-by-side Biome Vista Cards with aspect-ratio preserved scenery windows
- Archetype hazard badges and wrapped lore descriptions
- Enemy threat lists and boss previews pulling dynamically from ENEMY_CATALOG
- Keyboard & mouse selection with audio cues (AudioCue.CLICK & AudioCue.VICTORY)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.core.theme import ThemeToken
from src.data.biomes import ACT_BIOMES, BIOME_REGISTRY
from src.data.enemies import ENEMY_CATALOG
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


def get_fitted_surface(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    """Scale uniformly (preserving aspect ratio, zero distortion) and crop center to fit target dimensions."""
    sw, sh = src_surf.get_size()
    scale = max(target_w / sw, target_h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    ox = (nw - target_w) // 2
    oy = (nh - target_h) // 2
    return scaled.subsurface((ox, oy, target_w, target_h))


class PygameBiomeSelectView(PygameView):
    """Panoramic biome selection screen displaying Act expedition branches in SNES pixel art."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.selected_index: int = 0
        self._hovered_index: int | None = None
        self._hovered_btn: int | None = None
        self.anim_timer: float = 0.0

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(44, 52, 872, 476)
        self.header_rect = pygame.Rect(self.outer_rect.centerx - 290, 62, 580, 56)

        # Dual Expedition Cards
        self.card_a_rect = pygame.Rect(self.outer_rect.x + 18, 126, 408, 350)
        self.card_b_rect = pygame.Rect(self.outer_rect.x + 446, 126, 408, 350)

        # Bottom Action / Embark Buttons
        self.btn_a_rect = pygame.Rect(self.card_a_rect.centerx - 100, self.card_a_rect.bottom - 46, 200, 36)
        self.btn_b_rect = pygame.Rect(self.card_b_rect.centerx - 100, self.card_b_rect.bottom - 46, 200, 36)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle keyboard navigation and mouse clicks."""
        if self.top_hud.handle_event(event, session):
            return

        act = getattr(session.state, "act", 1)
        if act not in ACT_BIOMES:
            session.switch_mode(GameMode.MAP)
            return

        biome_a_id, biome_b_id = ACT_BIOMES[act]

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_index != 0:
                    self.selected_index = 0
                    event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.selected_index != 1:
                    self.selected_index = 1
                    event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                if self.selected_index == 0:
                    self._confirm_selection(session, biome_a_id)
                else:
                    self.selected_index = 0
                    event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                if self.selected_index == 1:
                    self._confirm_selection(session, biome_b_id)
                else:
                    self.selected_index = 1
                    event_bus.emit_audio(AudioCue.CLICK)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                chosen_id = biome_a_id if self.selected_index == 0 else biome_b_id
                self._confirm_selection(session, chosen_id)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Click Card A or Button A
            if self.card_a_rect.collidepoint(pos):
                if self.selected_index == 0 or self.btn_a_rect.collidepoint(pos):
                    self._confirm_selection(session, biome_a_id)
                else:
                    self.selected_index = 0
                    event_bus.emit_audio(AudioCue.CLICK)
                return

            # Click Card B or Button B
            if self.card_b_rect.collidepoint(pos):
                if self.selected_index == 1 or self.btn_b_rect.collidepoint(pos):
                    self._confirm_selection(session, biome_b_id)
                else:
                    self.selected_index = 1
                    event_bus.emit_audio(AudioCue.CLICK)
                return

    def _confirm_selection(self, session: GameSession, target_biome_id: str) -> None:
        """Play victory fanfare, advance act, and enter exploration map."""
        event_bus.emit_audio(AudioCue.VICTORY)
        session.state.advance_act(target_biome_id=target_biome_id)
        session.switch_mode(GameMode.MAP)

    def update(self, dt: float, session: GameSession) -> None:
        """Track mouse hover states and advance animation timer."""
        self.anim_timer += dt
        pos = pygame.mouse.get_pos()

        if self.card_a_rect.collidepoint(pos):
            self._hovered_index = 0
        elif self.card_b_rect.collidepoint(pos):
            self._hovered_index = 1
        else:
            self._hovered_index = None

        if self.btn_a_rect.collidepoint(pos):
            self._hovered_btn = 0
        elif self.btn_b_rect.collidepoint(pos):
            self._hovered_btn = 1
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render side-by-side 16-bit SNES biome vista cards with full threat and boss previews."""
        act = getattr(session.state, "act", 1)
        if act not in ACT_BIOMES:
            return

        biome_a_id, biome_b_id = ACT_BIOMES[act]
        b_a = BIOME_REGISTRY.get(biome_a_id)
        b_b = BIOME_REGISTRY.get(biome_b_id)
        if not b_a or not b_b:
            return

        # 1. Background (Crimson moon mountain kingdom balcony)
        assets.draw_background(surface, "class_select", vignette_alpha=145)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Frame
        bg_surf = pygame.Surface((self.outer_rect.width - 12, self.outer_rect.height - 12), pygame.SRCALPHA)
        bg_surf.fill((12, 14, 24, 235))
        surface.blit(bg_surf, (self.outer_rect.x + 6, self.outer_rect.y + 6))

        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Header Plaque
        self._draw_header(surface, renderer, act)

        # 5. Dual Biome Expedition Cards
        self._draw_card(surface, renderer, b_a, self.card_a_rect, self.btn_a_rect, idx=0)
        self._draw_card(surface, renderer, b_b, self.card_b_rect, self.btn_b_rect, idx=1)

        # 6. Bottom Navigation Controls Footnote
        footnote = (
            "[ 1 / 2 ] SELECT BIOME  |  [ ENTER / SPACE ] EMBARK EXPEDITION"
            if i18n.locale == "en"
            else "[ 1 / 2 ] ELEGIR BIOMA  |  [ ENTER / ESPACIO ] EMPRENDER EXPEDICIÓN"
        )
        renderer.draw_text(
            surface,
            footnote,
            self.outer_rect.centerx,
            self.outer_rect.bottom - 26,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
            align="center",
        )

    def _draw_header(self, surface: pygame.Surface, renderer: PygameRenderer, act: int) -> None:
        """Render ornate top expedition header plaque."""
        assets.draw_frame(surface, "frame_button_gold", self.header_rect, margin=18)

        act_title = (
            f"- ACT {act} EXPEDITION ROUTE -"
            if i18n.locale == "en"
            else f"- RUTA DE EXPEDICIÓN: ACTO {act} -"
        )
        # Drop shadow title
        renderer.draw_text(
            surface,
            act_title,
            self.header_rect.centerx + 1,
            self.header_rect.y + 9,
            color=(0, 0, 0),
            size=18,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            act_title,
            self.header_rect.centerx,
            self.header_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=18,
            bold=True,
            align="center",
        )

        sub = (
            "Pathfinder choice: select which perilous territory your champion shall traverse"
            if i18n.locale == "en"
            else "Elección de ruta: selecciona qué territorio hostil atravesará tu campeón"
        )
        renderer.draw_text(
            surface,
            sub,
            self.header_rect.centerx,
            self.header_rect.y + 32,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
            align="center",
        )

    def _draw_card(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        bdef,
        card_rect: pygame.Rect,
        btn_rect: pygame.Rect,
        idx: int,
    ) -> None:
        """Render individual 16-bit SNES expedition card with vista, threat list, and boss preview."""
        is_sel = (self.selected_index == idx)
        is_hover = (self._hovered_index == idx)

        # Card Backdrop
        bg_surf = pygame.Surface((card_rect.width - 8, card_rect.height - 8), pygame.SRCALPHA)
        bg_surf.fill((20, 26, 42, 235) if is_sel else (14, 18, 28, 225))
        surface.blit(bg_surf, (card_rect.x + 4, card_rect.y + 4))

        if is_sel:
            glow = pygame.Surface((card_rect.width - 8, card_rect.height - 8), pygame.SRCALPHA)
            glow.fill((255, 215, 0, 30))
            surface.blit(glow, (card_rect.x + 4, card_rect.y + 4))

        frame_name = "frame_button_gold" if is_sel else "frame_gold_clean"
        assets.draw_frame(surface, frame_name, card_rect, margin=18, draw_center=False)

        # 1. Scenic Landscape Vista Window (w=384, h=114)
        vista_rect = pygame.Rect(card_rect.x + 12, card_rect.y + 12, card_rect.width - 24, 114)
        vista_bg = assets.get_background(bdef.id)
        if vista_bg:
            fitted_vista = get_fitted_surface(vista_bg, vista_rect.width, vista_rect.height)
            surface.blit(fitted_vista, vista_rect.topleft)
        else:
            pygame.draw.rect(surface, (10, 14, 22), vista_rect)

        # Frame around vista window
        assets.draw_frame(surface, "frame_gold_clean", vista_rect, margin=14, draw_center=False)

        # 2. Biome Full Name
        name_y = vista_rect.bottom + 8
        renderer.draw_text(
            surface,
            f"[{idx + 1}]  {bdef.localized_name.upper()}",
            card_rect.x + 16,
            name_y,
            token=ThemeToken.TEXT_HIGHLIGHT if is_sel else ThemeToken.TEXT_NORMAL,
            size=15,
            bold=True,
        )

        # Archetype / Hazard Tag on dedicated line
        tag_y = name_y + 19
        clean_tags = bdef.localized_tags.strip("[] ")
        badge_col = (80, 215, 235) if idx == 0 else (245, 120, 140)
        renderer.draw_text(
            surface,
            f"Archetype: {clean_tags}",
            card_rect.x + 16,
            tag_y,
            color=badge_col,
            size=11,
            bold=True,
        )

        # 3. Biome Lore Description (2 lines)
        desc_y = tag_y + 18
        raw_desc = bdef.localized_description or ""
        words = raw_desc.split(" ")
        lines = []
        curr = ""
        for w in words:
            if len(curr) + len(w) < 52:
                curr += w + " "
            else:
                lines.append(curr.strip())
                curr = w + " "
        if curr:
            lines.append(curr.strip())

        for li, line in enumerate(lines[:2]):
            renderer.draw_text(
                surface,
                line,
                card_rect.x + 16,
                desc_y + li * 14,
                token=ThemeToken.TEXT_MUTED,
                size=12,
            )

        # Divider line
        div_y = desc_y + 32
        pygame.draw.line(surface, (55, 65, 88), (card_rect.x + 16, div_y), (card_rect.right - 16, div_y), width=1)

        # 4. Known Threats & Lurking Boss Section
        threats_x = card_rect.x + 16
        section_y = div_y + 6

        # Left Column: Threats
        renderer.draw_text(
            surface,
            "KNOWN THREATS",
            threats_x,
            section_y,
            color=(240, 160, 50),
            size=11,
            bold=True,
        )

        threat_names = []
        for e_id in getattr(bdef, "basic_enemies", [])[:3]:
            if e_id in ENEMY_CATALOG:
                threat_names.append(ENEMY_CATALOG[e_id].localized_name)
            else:
                threat_names.append(e_id.replace("_", " ").title())

        for ti, tname in enumerate(threat_names[:3]):
            ty = section_y + 16 + ti * 16
            pygame.draw.circle(surface, (240, 70, 80), (threats_x + 4, ty + 5), 2)
            renderer.draw_text(
                surface,
                tname,
                threats_x + 12,
                ty,
                token=ThemeToken.TEXT_NORMAL,
                size=12,
            )

        # Right Column: Lurking Boss
        boss_x = card_rect.centerx + 14
        renderer.draw_text(
            surface,
            "ACT BOSS ENCOUNTER",
            boss_x,
            section_y,
            color=(255, 90, 100),
            size=11,
            bold=True,
        )

        boss_names = []
        for b_id in getattr(bdef, "bosses", [])[:2]:
            if b_id in ENEMY_CATALOG:
                boss_names.append(ENEMY_CATALOG[b_id].localized_name)
            else:
                boss_names.append(b_id.replace("_", " ").title())

        for bi, bname in enumerate(boss_names[:2]):
            by_pos = section_y + 16 + bi * 16
            pygame.draw.circle(surface, (255, 215, 0), (boss_x + 4, by_pos + 5), 3)
            renderer.draw_text(
                surface,
                bname,
                boss_x + 12,
                by_pos,
                color=(255, 215, 0),
                size=12,
                bold=True,
            )

        # 5. Embark Route Button
        is_btn_hover = (self._hovered_btn == idx)
        btn_bg = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
        btn_bg.fill((32, 44, 70, 245) if (is_sel or is_btn_hover) else (18, 22, 34, 220))
        surface.blit(btn_bg, btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=14)

        if is_sel:
            # Pulsing cursor arrow
            pulse = int(math.sin(self.anim_timer * 6) * 3)
            arrow_color = (255, 215, 0)
            ax = btn_rect.x + 14 + pulse
            ay = btn_rect.centery
            pygame.draw.polygon(surface, arrow_color, [(ax, ay - 5), (ax, ay + 5), (ax + 6, ay)])

            btn_label = "[ EMBARK ROUTE ]" if i18n.locale == "en" else "[ EMPRENDER RUTA ]"
            btn_token = ThemeToken.TEXT_HIGHLIGHT
        else:
            btn_label = "[ SELECT ROUTE ]" if i18n.locale == "en" else "[ ELEGIR RUTA ]"
            btn_token = ThemeToken.TEXT_NORMAL if is_hover else ThemeToken.TEXT_MUTED

        renderer.draw_text(
            surface,
            btn_label,
            btn_rect.centerx,
            btn_rect.centery - 6,
            token=btn_token,
            size=13,
            bold=True,
            align="center",
        )
