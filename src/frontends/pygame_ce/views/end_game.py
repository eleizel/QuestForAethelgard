"""Pygame-CE 16-bit SNES End Game & Ascension Victory View.

Authentic Super Nintendo Golden Age RPG design:
- Balcony overlooking the crimson moon with gargoyles, pillars, and banners
- Dual diorama modes: Catacomb Memorial Altar (Defeat) vs Celestial Ascension Shrine (Victory)
- Animated torches, braziers, rising flame embers, and divine star motes
- Ornate Run Epitaph & Hall of Legends ledger with champion crest, portrait, and final glory score
- Audio cues (AudioCue.DEFEAT and AudioCue.VICTORY) and seamless title/credits routing
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import i18n, t
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


def draw_hanging_banner(surface: pygame.Surface, x: int, y: int, w: int = 22, h: int = 54, is_gold: bool = False) -> None:
    """Draw classic Super Nintendo gothic hanging banner with golden star/cross."""
    banner_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base_color = (190, 150, 30) if is_gold else (155, 22, 44)
    pygame.draw.rect(banner_surf, base_color, (0, 0, w, h - 8))
    pygame.draw.polygon(banner_surf, base_color, [(0, h - 9), (w // 2, h - 1), (w - 1, h - 9)])

    border_color = (255, 220, 90) if is_gold else (220, 180, 50)
    pygame.draw.rect(banner_surf, border_color, (0, 0, w, h - 8), width=1)
    pygame.draw.lines(banner_surf, border_color, False, [(0, h - 9), (w // 2, h - 1), (w - 1, h - 9)], width=1)

    # Center cross
    cx = w // 2
    cy = (h - 8) // 2
    cross_col = (255, 255, 255) if is_gold else (255, 215, 0)
    pygame.draw.line(banner_surf, cross_col, (cx, cy - 8), (cx, cy + 8), width=2)
    pygame.draw.line(banner_surf, cross_col, (cx - 5, cy - 2), (cx + 5, cy - 2), width=2)

    surface.blit(banner_surf, (x, y))


class PygameEndGameView(PygameView):
    """Atmospheric end-game memorial tombstone or victory ascension summary screen."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.anim_timer: float = 0.0
        self._audio_played: bool = False
        self._hovered_btn: str | None = None

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(44, 52, 872, 476)
        self.header_rect = pygame.Rect(self.outer_rect.centerx - 310, 62, 620, 58)

        # Diorama (Left) and Ledger (Right)
        self.diorama_rect = pygame.Rect(self.outer_rect.x + 18, 128, 350, 326)
        self.ledger_rect = pygame.Rect(self.outer_rect.x + 382, 128, 472, 326)

        # Bottom Action Buttons
        self.return_btn_rect = pygame.Rect(self.outer_rect.centerx - 170, 468, 210, 42)
        self.credits_btn_rect = pygame.Rect(self.outer_rect.centerx + 58, 468, 160, 42)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle restart, credits navigation, and mouse clicks."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._restart_game(session)
                return
            elif event.key == pygame.K_c:
                self._view_credits(session)
                return
            elif event.key == pygame.K_ESCAPE:
                self._restart_game(session)
                return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.return_btn_rect.collidepoint(pos):
                self._restart_game(session)
                return
            elif self.credits_btn_rect.collidepoint(pos):
                self._view_credits(session)
                return

        if self.top_hud.handle_event(event, session):
            return

    def _restart_game(self, session: GameSession) -> None:
        """Play click and reset state back to the title screen."""
        event_bus.emit_audio(AudioCue.CLICK)
        self._audio_played = False
        session.reset_to_title()

    def _view_credits(self, session: GameSession) -> None:
        """Navigate to the game credits view."""
        event_bus.emit_audio(AudioCue.CLICK)
        self._audio_played = False
        session.switch_mode(GameMode.CREDITS)

    def update(self, dt: float, session: GameSession) -> None:
        """Update animation timer and mouse hover state."""
        self.anim_timer += dt
        pos = pygame.mouse.get_pos()

        if self.return_btn_rect.collidepoint(pos):
            self._hovered_btn = "return"
        elif self.credits_btn_rect.collidepoint(pos):
            self._hovered_btn = "credits"
        else:
            self._hovered_btn = None

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES End Game memorial or ascension victory screen."""
        is_victory = (session.current_mode == GameMode.VICTORY)

        # Play audio cue once on entry
        if not self._audio_played:
            cue = AudioCue.VICTORY if is_victory else AudioCue.DEFEAT
            event_bus.emit_audio(cue)
            self._audio_played = True

        # 1. Background (Crimson moon balcony / class promotion background)
        assets.draw_background(surface, "class_select", vignette_alpha=135)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Frame
        bg_surf = pygame.Surface((self.outer_rect.width - 12, self.outer_rect.height - 12), pygame.SRCALPHA)
        bg_surf.fill((12, 14, 22, 238) if not is_victory else (14, 16, 28, 238))
        surface.blit(bg_surf, (self.outer_rect.x + 6, self.outer_rect.y + 6))

        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        # 4. Top Header Plaque
        self._draw_header(surface, renderer, is_victory)

        # 5. Diorama Viewport (Left)
        self._draw_diorama(surface, renderer, session, is_victory)

        # 6. Run Epitaph / Hall of Legends Ledger (Right)
        self._draw_ledger(surface, renderer, session, is_victory)

        # 7. Bottom Action Control Bar
        self._draw_bottom_bar(surface, renderer, is_victory)

    def _draw_header(self, surface: pygame.Surface, renderer: PygameRenderer, is_victory: bool) -> None:
        """Render ornate top headline plaque with title and thematic subtitle."""
        assets.draw_frame(surface, "frame_button_gold", self.header_rect, margin=18)

        if is_victory:
            title_text = "ASCENSION ACHIEVED!" if i18n.locale == "en" else "¡VICTORIA OBTENIDA!"
            title_color = (255, 215, 0)
            sub_text = (
                "Thou hast banished the ancient shadow and liberated the Realm of Aethelgard!"
                if i18n.locale == "en"
                else "¡Has desterrado la sombra ancestral y liberado el Reino de Aethelgard!"
            )
        else:
            title_text = "HERO DEFEATED" if i18n.locale == "en" else "¡HAS SIDO DERROTADO!"
            title_color = (245, 60, 70)
            sub_text = (
                "Thy courage was valiant, yet thy bones now join the catacombs beneath Aethelgard..."
                if i18n.locale == "en"
                else "Tu valor fue indomable, pero tus restos descansan ya en las catacumbas..."
            )

        # Drop shadow title
        renderer.draw_text(
            surface,
            title_text,
            self.header_rect.centerx + 1,
            self.header_rect.y + 11,
            color=(0, 0, 0),
            size=22,
            bold=True,
            align="center",
        )
        renderer.draw_text(
            surface,
            title_text,
            self.header_rect.centerx,
            self.header_rect.y + 10,
            color=title_color,
            size=22,
            bold=True,
            align="center",
        )

        renderer.draw_text(
            surface,
            sub_text,
            self.header_rect.centerx,
            self.header_rect.y + 36,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            bold=False,
            align="center",
        )

    def _draw_diorama(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        session: GameSession,
        is_victory: bool,
    ) -> None:
        """Render bespoke 16-bit animated diorama (Catacomb Altar or Ascension Shrine)."""
        r = self.diorama_rect

        # Inner dark chamber
        chamber_surf = pygame.Surface((r.width - 8, r.height - 8), pygame.SRCALPHA)
        chamber_surf.fill((10, 12, 18, 220))
        surface.blit(chamber_surf, (r.x + 4, r.y + 4))

        assets.draw_frame(surface, "frame_gold_clean", r, margin=18, draw_center=False)

        cx = r.centerx
        ground_y = r.bottom - 32
        t_ticks = int(self.anim_timer * 10)

        # Flagstone Floor Platform
        ground_surf = pygame.Surface((r.width - 16, 22), pygame.SRCALPHA)
        ground_surf.fill((22, 26, 38, 230))
        surface.blit(ground_surf, (r.x + 8, ground_y))
        for gx in range(r.x + 14, r.right - 24, 20):
            pygame.draw.line(surface, (52, 60, 82), (gx, ground_y + 4), (gx + 14, ground_y + 4), width=1)
            pygame.draw.line(surface, (52, 60, 82), (gx + 6, ground_y + 12), (gx + 18, ground_y + 12), width=1)

        if not is_victory:
            # =================================================================
            # DEFEAT DIORAMA: Catacomb Memorial Altar & Fallen Hero
            # =================================================================
            # Flanking Crimson Hanging Banners
            draw_hanging_banner(surface, r.x + 20, r.y + 16, w=22, h=56, is_gold=False)
            draw_hanging_banner(surface, r.right - 42, r.y + 16, w=22, h=56, is_gold=False)

            # Twin Flanking Stone Braziers with Rising Fire Embers
            for bx in [r.x + 46, r.right - 68]:
                # Stone pillar pedestal
                pygame.draw.rect(surface, (34, 38, 52), (bx, ground_y - 48, 22, 48))
                pygame.draw.rect(surface, (60, 68, 92), (bx, ground_y - 48, 22, 48), width=1)
                pygame.draw.rect(surface, (70, 78, 105), (bx - 3, ground_y - 54, 28, 8))

                # Fire flames
                flame_off = int(math.sin(self.anim_timer * 7 + (bx % 5)) * 3)
                fx = bx + 11
                fy = ground_y - 54
                pygame.draw.polygon(surface, (240, 60, 30), [(fx - 9, fy), (fx + 9, fy), (fx + flame_off, fy - 22)])
                pygame.draw.polygon(surface, (255, 170, 40), [(fx - 5, fy), (fx + 5, fy), (fx - flame_off, fy - 16)])
                pygame.draw.circle(surface, (255, 230, 150), (fx, fy - 4), 3)

                # Floating fire sparks
                for i in range(4):
                    sx = fx - 8 + ((t_ticks * 2 + i * 7) % 18)
                    sy = fy - 8 - ((t_ticks * 3 + i * 11) % 28)
                    pygame.draw.circle(surface, (255, 180, 50), (sx, sy), 1)

            # Central Stone Tomb Altar
            tomb_rect = pygame.Rect(cx - 56, ground_y - 52, 112, 52)
            pygame.draw.rect(surface, (30, 34, 48), tomb_rect)
            pygame.draw.rect(surface, (64, 74, 100), tomb_rect, width=2)
            # Tombstone carved cross
            pygame.draw.line(surface, (120, 135, 170), (cx, ground_y - 44), (cx, ground_y - 14), width=3)
            pygame.draw.line(surface, (120, 135, 170), (cx - 14, ground_y - 34), (cx + 14, ground_y - 34), width=3)

            # Resting Blade embedded into the altar stone
            blade_top = ground_y - 94
            # Blade
            pygame.draw.line(surface, (200, 215, 235), (cx, blade_top + 16), (cx, ground_y - 50), width=3)
            pygame.draw.line(surface, (255, 255, 255), (cx - 1, blade_top + 16), (cx - 1, ground_y - 50), width=1)
            # Crossguard
            pygame.draw.line(surface, (218, 165, 32), (cx - 14, blade_top + 16), (cx + 14, blade_top + 16), width=4)
            # Hilt & Pommel
            pygame.draw.line(surface, (140, 90, 40), (cx, blade_top + 2), (cx, blade_top + 16), width=3)
            pygame.draw.circle(surface, (218, 165, 32), (cx, blade_top + 2), 4)

            # Hero Portrait Alcove in background (Vignetted)
            port_surf = assets.get_class_portrait(session.player.class_id, size=(72, 72))
            if port_surf:
                px = cx - 36
                py = r.y + 36
                # Dark vignette border around hero bust
                pygame.draw.rect(surface, (14, 16, 24), (px - 4, py - 4, 80, 80))
                pygame.draw.rect(surface, (90, 40, 50), (px - 4, py - 4, 80, 80), width=2)
                surface.blit(port_surf, (px, py))
                # Somber tint overlay
                tint = pygame.Surface((72, 72), pygame.SRCALPHA)
                tint.fill((10, 12, 24, 110))
                surface.blit(tint, (px, py))

        else:
            # =================================================================
            # VICTORY DIORAMA: Celestial Ascension Shrine & Sovereign Laurel
            # =================================================================
            # Flanking Golden Royal Banners
            draw_hanging_banner(surface, r.x + 20, r.y + 16, w=22, h=56, is_gold=True)
            draw_hanging_banner(surface, r.right - 42, r.y + 16, w=22, h=56, is_gold=True)

            # Divine Light Beams from Above
            for i in range(5):
                beam_x = cx - 70 + i * 35
                beam_surf = pygame.Surface((32, ground_y - r.y - 10), pygame.SRCALPHA)
                alpha = int(35 + math.sin(self.anim_timer * 3 + i) * 15)
                pygame.draw.polygon(beam_surf, (255, 235, 140, alpha), [(10, 0), (22, 0), (32, ground_y - r.y - 10), (0, ground_y - r.y - 10)])
                surface.blit(beam_surf, (beam_x, r.y + 10))

            # Golden Marble Ascension Pedestal
            ped_rect = pygame.Rect(cx - 60, ground_y - 54, 120, 54)
            pygame.draw.rect(surface, (44, 48, 68), ped_rect)
            assets.draw_frame(surface, "frame_button_gold", ped_rect, margin=14)

            # Floating Golden Sovereign Crown / Laurel
            crown_y = ground_y - 82 + int(math.sin(self.anim_timer * 4) * 4)
            # Golden base
            pygame.draw.rect(surface, (255, 215, 0), (cx - 24, crown_y, 48, 12), border_radius=2)
            pygame.draw.polygon(surface, (255, 215, 0), [(cx - 24, crown_y), (cx - 16, crown_y - 14), (cx - 8, crown_y)])
            pygame.draw.polygon(surface, (255, 215, 0), [(cx - 8, crown_y), (cx, crown_y - 18), (cx + 8, crown_y)])
            pygame.draw.polygon(surface, (255, 215, 0), [(cx + 8, crown_y), (cx + 16, crown_y - 14), (cx + 24, crown_y)])
            # Crown Jewels
            pygame.draw.circle(surface, (240, 50, 70), (cx, crown_y + 6), 3)       # Ruby
            pygame.draw.circle(surface, (60, 180, 255), (cx - 14, crown_y + 6), 2) # Sapphire
            pygame.draw.circle(surface, (60, 220, 100), (cx + 14, crown_y + 6), 2) # Emerald

            # Pulsing Golden Aura Ring
            aura_r = 38 + int(math.sin(self.anim_timer * 4) * 5)
            aura_surf = pygame.Surface((aura_r * 2 + 4, aura_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (255, 215, 0, 55), (aura_r + 2, aura_r + 2), aura_r, width=2)
            surface.blit(aura_surf, (cx - aura_r - 2, crown_y - 4 - aura_r))

            # Hero Portrait in Golden Laurel Wreath
            port_surf = assets.get_class_portrait(session.player.class_id, size=(72, 72))
            if port_surf:
                px = cx - 36
                py = r.y + 36
                pygame.draw.rect(surface, (14, 18, 30), (px - 4, py - 4, 80, 80))
                assets.draw_frame(surface, "frame_button_gold", pygame.Rect(px - 6, py - 6, 84, 84), margin=14)
                surface.blit(port_surf, (px, py))

            # Orbiting Celestial Sparkles
            for i in range(6):
                angle = (t_ticks * 3 + i * 60) % 360
                rad = math.radians(angle)
                sx = cx + int(math.cos(rad) * (52 + (i * 4)))
                sy = crown_y + int(math.sin(rad) * 22)
                pygame.draw.circle(surface, (255, 235, 120), (sx, sy), 2)
                pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 1)

    def _draw_ledger(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        session: GameSession,
        is_victory: bool,
    ) -> None:
        """Render detailed run epitaph or triumphant hall of legends ledger."""
        r = self.ledger_rect

        # Ledger backdrop
        bg_surf = pygame.Surface((r.width - 8, r.height - 8), pygame.SRCALPHA)
        bg_surf.fill((16, 20, 32, 230))
        surface.blit(bg_surf, (r.x + 4, r.y + 4))

        assets.draw_frame(surface, "frame_gold_clean", r, margin=18, draw_center=False)

        player = session.player
        cid = player.class_id.lower()

        # 1. Champion Header with Class Crest
        crest_box = pygame.Rect(r.x + 16, r.y + 14, 46, 46)
        pygame.draw.rect(surface, (10, 12, 18), crest_box)
        assets.draw_frame(surface, "frame_button_gold", crest_box, margin=12)

        crest_icon = assets.get_class_crest(cid, size=(32, 32))
        if crest_icon:
            surface.blit(crest_icon, (crest_box.centerx - 16, crest_box.centery - 16))

        title_name = f"{player.name} the {cid.capitalize()}"
        renderer.draw_text(
            surface,
            title_name,
            r.x + 72,
            r.y + 16,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=16,
            bold=True,
        )

        role_subtitle = (
            f"Ascended Sovereign - Level {player.level}" if is_victory else f"Fallen Champion - Level {player.level}"
        )
        renderer.draw_text(
            surface,
            role_subtitle,
            r.x + 72,
            r.y + 38,
            color=(80, 220, 140) if is_victory else (240, 80, 90),
            size=12,
            bold=True,
        )

        # Divider line
        div_y = r.y + 68
        pygame.draw.line(surface, (60, 70, 95), (r.x + 16, div_y), (r.right - 16, div_y), width=1)

        # 2. Run Statistics Breakdown
        biome_name = getattr(session.state, "current_biome", "cathedral").capitalize()
        act_val = getattr(session.state, "act", 1)
        floor_val = getattr(session.state, "floor", 1)
        gold_val = player.gold
        equip_cnt = len([v for v in player.inventory.equipment.values() if v is not None])
        if hasattr(player.abilities, "active"):
            ab_cnt = len(player.abilities.active) + len(player.abilities.passive)
        elif isinstance(player.abilities, (list, tuple)):
            ab_cnt = len(player.abilities)
        else:
            ab_cnt = 0

        # Calculate run glory score
        run_score = player.level * 120 + gold_val * 2 + floor_val * 60 + equip_cnt * 75 + (2000 if is_victory else 0)

        stats = [
            ("Furthest Reach", f"Act {act_val} - Floor {floor_val} ({biome_name})"),
            ("Treasure Amassed", f"{gold_val} Gold Coins"),
            ("Relics & Armor", f"{equip_cnt} Equipment Pieces"),
            ("Techniques Mastered", f"{ab_cnt} Abilities"),
            ("Final Run Score", f"{run_score} Glory Points"),
        ]

        stat_start_y = div_y + 12
        for idx, (label, val) in enumerate(stats):
            sy = stat_start_y + idx * 28

            # Alternating subtle row striping
            if idx % 2 == 1:
                pygame.draw.rect(surface, (22, 28, 44, 120), (r.x + 16, sy - 4, r.width - 32, 24), border_radius=3)

            renderer.draw_text(
                surface,
                label,
                r.x + 22,
                sy,
                token=ThemeToken.TEXT_MUTED,
                size=13,
                bold=False,
            )

            is_score = (idx == len(stats) - 1)
            val_col = (255, 215, 0) if is_score else (230, 235, 245)
            renderer.draw_text(
                surface,
                val,
                r.right - 22,
                sy,
                color=val_col,
                size=13,
                bold=is_score,
                align="right",
            )

        # Divider line
        div_y2 = stat_start_y + len(stats) * 28 + 4
        pygame.draw.line(surface, (60, 70, 95), (r.x + 16, div_y2), (r.right - 16, div_y2), width=1)

        # 3. Thematic Proclamation / Epitaph Quote
        quote_y = div_y2 + 10
        if is_victory:
            quote = '"Songs of thy triumph shall echo across the mountain realm for eternity."'
            q_color = (255, 215, 0)
        else:
            quote = '"Though thy flame fades into shadow, thy valiant memory shall never perish."'
            q_color = (180, 190, 210)

        renderer.draw_text(
            surface,
            quote,
            r.centerx,
            quote_y,
            color=q_color,
            size=12,
            bold=False,
            align="center",
        )

    def _draw_bottom_bar(self, surface: pygame.Surface, renderer: PygameRenderer, is_victory: bool) -> None:
        """Render return to title and view credits action buttons."""
        # Return / Play Again button
        is_hover_ret = (self._hovered_btn == "return")
        bg_ret = pygame.Surface(self.return_btn_rect.size, pygame.SRCALPHA)
        bg_ret.fill((28, 38, 62, 240) if is_hover_ret else (16, 22, 36, 220))
        surface.blit(bg_ret, self.return_btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", self.return_btn_rect, margin=16)

        ret_label = "[ SPACE ] RETURN TO TITLE" if i18n.locale == "en" else "[ ESPACIO ] MENÚ PRINCIPAL"
        renderer.draw_text(
            surface,
            ret_label,
            self.return_btn_rect.centerx,
            self.return_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hover_ret else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )

        # Credits button
        is_hover_cred = (self._hovered_btn == "credits")
        bg_cred = pygame.Surface(self.credits_btn_rect.size, pygame.SRCALPHA)
        bg_cred.fill((28, 38, 62, 240) if is_hover_cred else (16, 22, 36, 220))
        surface.blit(bg_cred, self.credits_btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", self.credits_btn_rect, margin=16)

        cred_label = "[ C ] CREDITS" if i18n.locale == "en" else "[ C ] CRÉDITOS"
        renderer.draw_text(
            surface,
            cred_label,
            self.credits_btn_rect.centerx,
            self.credits_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hover_cred else ThemeToken.TEXT_NORMAL,
            size=13,
            bold=True,
            align="center",
        )
