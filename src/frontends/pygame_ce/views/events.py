"""Pygame-CE 16-bit SNES Narrative Events & Shrine Encounter View."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.game_state import GameMode
from src.core.i18n import t, i18n
from src.core.theme import ThemeToken
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


class PygameEventsView(PygameView):
    """Narrative dungeon event view presenting choices, animated 16-bit scene art, and outcomes."""

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.anim_timer: float = 0.0
        self._hovered_choice: int | None = None
        self._hovered_btn: str | None = None

        # Display Rectangles (960x540 display)
        self.outer_rect = pygame.Rect(36, 56, 888, 472)
        self.header_rect = pygame.Rect(self.outer_rect.centerx - 240, self.outer_rect.y + 12, 480, 36)
        self.scene_rect = pygame.Rect(self.outer_rect.centerx - 280, self.outer_rect.y + 56, 560, 142)
        self.text_rect = pygame.Rect(self.outer_rect.centerx - 340, self.outer_rect.y + 208, 680, 70)

        # Choice button rects (up to 3 choices)
        self.choice_rects = [
            pygame.Rect(self.outer_rect.centerx - 300, self.outer_rect.y + 288, 600, 44),
            pygame.Rect(self.outer_rect.centerx - 300, self.outer_rect.y + 340, 600, 44),
            pygame.Rect(self.outer_rect.centerx - 300, self.outer_rect.y + 392, 600, 44),
        ]
        self.cont_rect = pygame.Rect(self.outer_rect.centerx - 120, self.outer_rect.y + 340, 240, 46)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Handle choice selection and progression inputs."""
        if self.top_hud.handle_event(event, session):
            return

        current_event = getattr(session.state, "current_event", None)
        is_resolved = current_event is None or bool(getattr(current_event, "resolved_text", ""))
        event_raw_text = (
            current_event.description
            if (current_event and current_event.description)
            else getattr(session.state, "current_event_text", "")
        )

        if is_resolved:
            # Resolved or simple notification: any progression key continues
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_c, pygame.K_ESCAPE):
                    self._exit_events(session)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.cont_rect.collidepoint(event.pos) or not self.outer_rect.collidepoint(event.pos):
                    self._exit_events(session)
            return

        # Decision State
        if current_event and current_event.choices:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1) and len(current_event.choices) > 0:
                    self._execute_choice(session, current_event, 0)
                elif event.key in (pygame.K_2, pygame.K_KP2) and len(current_event.choices) > 1:
                    self._execute_choice(session, current_event, 1)
                elif event.key in (pygame.K_3, pygame.K_KP3) and len(current_event.choices) > 2:
                    self._execute_choice(session, current_event, 2)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for idx, r in enumerate(self.choice_rects):
                    if idx < len(current_event.choices) and r.collidepoint(pos):
                        self._execute_choice(session, current_event, idx)
                        return

    def _execute_choice(self, session: GameSession, event, choice_idx: int) -> None:
        """Execute selected choice action hook and record resolved outcome."""
        if choice_idx >= len(event.choices):
            return
        choice = event.choices[choice_idx]
        if not choice.is_available(session.state):
            return

        # Play audio cue
        cue = AudioCue.CHEST if getattr(event, "scene_type", "") == "CHEST" else AudioCue.CLICK
        event_bus.emit_audio(cue)

        # Execute effect and transition to resolved text
        outcome = choice.action_hook(session.state)
        event.resolved_text = outcome

    def _exit_events(self, session: GameSession) -> None:
        """Clear active event and route to promotion, ability choice, or map."""
        session.state.current_event = None
        session.state.current_event_text = ""

        from src.systems.loot_service import LootService
        next_mode = LootService.resolve_exit_mode(session.player)
        if next_mode == GameMode.PROMOTION:
            if session.state.begin_promotion(GameMode.EVENTS):
                return
        elif next_mode == GameMode.ABILITY_CHOICE:
            session.state.switch_mode(GameMode.ABILITY_CHOICE)
            return

        session.state.continue_after_rewards()

    def update(self, dt: float, session: GameSession) -> None:
        """Update animation timer and hover coordinates."""
        self.anim_timer += dt
        pos = pygame.mouse.get_pos()

        current_event = getattr(session.state, "current_event", None)
        is_resolved = current_event is None or bool(getattr(current_event, "resolved_text", ""))
        event_raw_text = (
            current_event.description
            if (current_event and current_event.description)
            else getattr(session.state, "current_event_text", "")
        )

        if is_resolved:
            self._hovered_btn = "continue" if self.cont_rect.collidepoint(pos) else None
            self._hovered_choice = None
        else:
            self._hovered_btn = None
            self._hovered_choice = None
            if current_event:
                for idx, r in enumerate(self.choice_rects):
                    if idx < len(current_event.choices) and r.collidepoint(pos):
                        self._hovered_choice = idx
                        break

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render 16-bit SNES event modal with scene art, dialogue, and choices."""
        # 1. Dimmed Background
        biome = getattr(session.state, "current_biome", "cathedral")
        event_raw_text = getattr(session.state, "current_event_text", "")
        bg_name = "rest" if "rest" in event_raw_text.lower() else biome
        assets.draw_background(surface, bg_name, vignette_alpha=145)

        # 2. Top HUD Bar
        self.top_hud.draw(surface, renderer, session)

        # 3. Outer Ornate Golden Frame
        bg_surf = pygame.Surface((self.outer_rect.width - 12, self.outer_rect.height - 12), pygame.SRCALPHA)
        bg_surf.fill((14, 16, 26, 248))
        surface.blit(bg_surf, (self.outer_rect.x + 6, self.outer_rect.y + 6))

        assets.draw_frame(surface, "frame_gold_ornate_hollow", self.outer_rect, margin=54)

        current_event = getattr(session.state, "current_event", None)
        is_resolved = current_event is None or bool(getattr(current_event, "resolved_text", ""))
        event_raw_text = (
            current_event.description
            if (current_event and current_event.description)
            else getattr(session.state, "current_event_text", "")
        )

        # 4. Header Plaque
        assets.draw_frame(surface, "frame_button_gold", self.header_rect, margin=18)
        if current_event:
            header_title = current_event.title.upper()
        elif "rest" in event_raw_text.lower():
            header_title = "SANCTUARY REST"
        elif "treasure" in event_raw_text.lower() or "cache" in event_raw_text.lower():
            header_title = "HIDDEN CACHE"
        else:
            header_title = "ENCOUNTER IN THE DARK"

        renderer.draw_text(
            surface,
            header_title,
            self.header_rect.centerx,
            self.header_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=15,
            bold=True,
            align="center",
        )

        # 5. Scene Art Illustration Viewport
        self._draw_scene_art(surface, renderer, session, current_event)

        # 6. Centered Narrative Dialogue
        self._draw_narrative_text(surface, renderer, current_event, event_raw_text, is_resolved)

        # 7. Action Choices or Continue Button
        if current_event and not is_resolved:
            self._draw_choices(surface, renderer, session, current_event)
        else:
            self._draw_continue_button(surface, renderer)

    def _draw_scene_art(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        session: GameSession,
        event,
    ) -> None:
        """Render bespoke 16-bit animated scene art inside the central viewport."""
        r = self.scene_rect

        # Fitted combat arena backdrop (dimmed for focal atmospheric contrast)
        biome = getattr(session.state, "current_biome", "cathedral")
        arena_src = assets.get_combat_arena_bg(biome) or assets.get_background(biome)
        if arena_src:
            fitted_arena = get_fitted_surface(arena_src, r.width, r.height)
            surface.blit(fitted_arena, r.topleft)
            dim_overlay = pygame.Surface(r.size, pygame.SRCALPHA)
            dim_overlay.fill((8, 12, 20, 100))
            surface.blit(dim_overlay, r.topleft)
        else:
            pygame.draw.rect(surface, (10, 12, 18), r)

        scene_type = getattr(event, "scene_type", "DEFAULT") if event else "DEFAULT"
        cx = r.centerx
        cy = r.centery
        t_ticks = int(self.anim_timer * 10)

        # Ground platform
        ground_y = r.bottom - 22
        ground_surf = pygame.Surface((r.width - 16, 16), pygame.SRCALPHA)
        ground_surf.fill((20, 24, 36, 220))
        surface.blit(ground_surf, (r.x + 8, ground_y))
        for gx in range(r.x + 14, r.right - 14, 18):
            pygame.draw.line(surface, (50, 60, 80), (gx, ground_y + 4), (gx + 12, ground_y + 4), width=1)
            pygame.draw.line(surface, (50, 60, 80), (gx + 6, ground_y + 10), (gx + 16, ground_y + 10), width=1)

        # Pillars on flanks
        for col_x in [r.x + 24, r.x + 48, r.right - 64, r.right - 40]:
            col_surf = pygame.Surface((16, ground_y - r.y - 12), pygame.SRCALPHA)
            col_surf.fill((24, 28, 42, 190))
            surface.blit(col_surf, (col_x, r.y + 12))
            for py in range(r.y + 18, ground_y - 6, 12):
                pygame.draw.line(surface, (50, 58, 85), (col_x, py), (col_x + 15, py), width=1)

        if scene_type == "CHEST":
            # --- Bespoke Chest Scene ---
            chest_surf = assets.get_ui_component("chest_spoils")
            if chest_surf:
                scaled_chest = pygame.transform.smoothscale(chest_surf, (150, 68))
                surface.blit(scaled_chest, (cx - 75, ground_y - 56))

            # Sparkle motes
            for i in range(5):
                angle = (t_ticks * 4 + i * 72) % 360
                rad = math.radians(angle)
                sx = cx + int(math.cos(rad) * (60 + (i * 8)))
                sy = ground_y - 32 + int(math.sin(rad) * 18)
                if (t_ticks + i * 3) % 6 < 4:
                    pygame.draw.circle(surface, (255, 215, 0), (sx, sy), 2)
                    pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 1)

        elif scene_type in ("SHRINE", "ALTAR"):
            # --- Holy Shrine / Altar Scene ---
            # Stone Altar Base
            pygame.draw.rect(surface, (32, 38, 56), (cx - 46, ground_y - 32, 92, 32))
            pygame.draw.rect(surface, (70, 85, 120), (cx - 46, ground_y - 32, 92, 32), width=1)

            # Glowing Runestone Monolith
            pygame.draw.rect(surface, (22, 28, 44), (cx - 24, ground_y - 70, 48, 42))
            pygame.draw.rect(surface, (80, 200, 230), (cx - 24, ground_y - 70, 48, 42), width=1)

            # Radiant Holy Rune Cross
            pygame.draw.line(surface, (240, 245, 255), (cx, ground_y - 64), (cx, ground_y - 38), width=3)
            pygame.draw.line(surface, (240, 245, 255), (cx - 12, ground_y - 52), (cx + 12, ground_y - 52), width=3)

            # Pulsing Aura Ring
            aura_r = 28 + int(math.sin(self.anim_timer * 3) * 4)
            aura_surf = pygame.Surface((aura_r * 2 + 4, aura_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (80, 220, 255, 60), (aura_r + 2, aura_r + 2), aura_r, width=2)
            surface.blit(aura_surf, (cx - aura_r - 2, ground_y - 51 - aura_r))

            # Altar Candles
            for c_x in [cx - 36, cx + 36]:
                pygame.draw.rect(surface, (220, 225, 230), (c_x - 3, ground_y - 38, 6, 10))
                flame_h = 4 + (t_ticks % 3)
                pygame.draw.circle(surface, (255, 200, 40), (c_x, ground_y - 38 - flame_h), 3)
                pygame.draw.circle(surface, (255, 120, 20), (c_x, ground_y - 38 - flame_h - 1), 2)

        elif scene_type == "FORGE":
            # --- Blacksmith Forge Scene ---
            # Anvil Base & Horn
            pygame.draw.rect(surface, (30, 34, 46), (cx - 30, ground_y - 28, 60, 28))
            pygame.draw.rect(surface, (50, 56, 74), (cx - 36, ground_y - 36, 72, 10))
            pygame.draw.polygon(surface, (50, 56, 74), [(cx + 36, ground_y - 36), (cx + 52, ground_y - 33), (cx + 36, ground_y - 28)])

            # Glowing Molten Slag
            pygame.draw.rect(surface, (255, 120, 30), (cx - 16, ground_y - 40, 32, 6))
            pygame.draw.rect(surface, (255, 220, 60), (cx - 10, ground_y - 41, 20, 3))

            # Rising Embers
            for i in range(7):
                ex = cx - 20 + ((t_ticks * 3 + i * 14) % 40)
                ey = ground_y - 44 - ((t_ticks * 2 + i * 11) % 45)
                col = (255, 220, 80) if i % 2 == 0 else (255, 100, 30)
                pygame.draw.circle(surface, col, (ex, ey), 1)

        elif scene_type == "PORTAL":
            # --- Celestial Portal Scene ---
            p_rot = (self.anim_timer * 1.5)
            # Outer swirling rings
            for i in range(16):
                ang = p_rot + (i * math.pi / 8)
                px = cx + int(math.cos(ang) * 44)
                py = ground_y - 42 + int(math.sin(ang) * 28)
                pygame.draw.circle(surface, (160, 60, 220), (px, py), 3)

            for i in range(12):
                ang = -p_rot * 1.4 + (i * math.pi / 6)
                px = cx + int(math.cos(ang) * 28)
                py = ground_y - 42 + int(math.sin(ang) * 18)
                pygame.draw.circle(surface, (60, 210, 255), (px, py), 2)

            # Bright core
            pygame.draw.circle(surface, (230, 240, 255), (cx, ground_y - 42), 12)
            pygame.draw.circle(surface, (255, 255, 255), (cx, ground_y - 42), 6)

        elif scene_type == "CORPSE":
            # --- Tangled Briar & Fallen Knight ---
            pygame.draw.circle(surface, (24, 30, 40), (cx, ground_y - 12), 34)
            # Briar tendrils
            for i in range(8):
                rad = math.radians(i * 45)
                bx = cx + int(math.cos(rad) * 26)
                by = ground_y - 12 + int(math.sin(rad) * 18)
                pygame.draw.line(surface, (50, 90, 60), (cx, ground_y - 12), (bx, by), width=2)
                if i % 2 == 0:
                    pygame.draw.circle(surface, (220, 40, 50), (bx, by), 3)  # Blood / roses

            # Dark silhouette
            pygame.draw.rect(surface, (16, 18, 26), (cx - 14, ground_y - 24, 28, 16))
            pygame.draw.circle(surface, (16, 18, 26), (cx, ground_y - 28), 8)

        else:
            # --- Default / Sanctuary Rest Campfire ---
            # Fire Pit Cobblestones
            pygame.draw.ellipse(surface, (36, 40, 56), (cx - 28, ground_y - 14, 56, 14))
            pygame.draw.line(surface, (80, 50, 30), (cx - 18, ground_y - 10), (cx + 18, ground_y - 6), width=4)
            pygame.draw.line(surface, (80, 50, 30), (cx + 16, ground_y - 10), (cx - 16, ground_y - 6), width=4)

            # Animated Fire Flames
            flame_offset = int(math.sin(self.anim_timer * 8) * 3)
            pygame.draw.polygon(surface, (255, 120, 20), [
                (cx - 12, ground_y - 8), (cx + 12, ground_y - 8), (cx + flame_offset, ground_y - 34)
            ])
            pygame.draw.polygon(surface, (255, 210, 40), [
                (cx - 7, ground_y - 8), (cx + 7, ground_y - 8), (cx - flame_offset, ground_y - 26)
            ])
            pygame.draw.circle(surface, (255, 240, 160), (cx, ground_y - 12), 4)

            # Floating fire embers
            for i in range(5):
                ex = cx - 12 + ((t_ticks * 2 + i * 9) % 24)
                ey = ground_y - 20 - ((t_ticks * 3 + i * 13) % 36)
                pygame.draw.circle(surface, (255, 200, 60), (ex, ey), 1)

        # Golden Clean Viewport Frame (Hollow center so scene art shines through)
        assets.draw_frame(surface, "frame_gold_clean", r, margin=20, draw_center=False)

    def _draw_narrative_text(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        event,
        raw_text: str,
        is_resolved: bool,
    ) -> None:
        """Render multi-line narrative description or resolved reward outcome."""
        r = self.text_rect
        display_text = event.resolved_text if (event and is_resolved) else (raw_text or "Silence settles across the ancient hall.")

        words = display_text.split(" ")
        lines = []
        curr = ""
        for word in words:
            if len(curr) + len(word) < 70:
                curr += word + " "
            else:
                lines.append(curr.strip())
                curr = word + " "
        if curr:
            lines.append(curr.strip())

        text_color = (255, 215, 0) if is_resolved else None
        token = ThemeToken.TEXT_NORMAL if not is_resolved else ThemeToken.TEXT_HIGHLIGHT

        display_lines = lines[:4]
        line_spacing = 18 if len(display_lines) >= 4 else 20
        font_size = 13 if len(display_lines) >= 4 else 14
        start_y = r.centery - (len(display_lines) * line_spacing // 2) - 2

        for idx, line in enumerate(display_lines):
            renderer.draw_text(
                surface,
                line,
                r.centerx,
                start_y + idx * line_spacing,
                token=token,
                color=text_color,
                size=font_size,
                bold=is_resolved,
                align="center",
            )

    def _draw_choices(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        session: GameSession,
        event,
    ) -> None:
        """Render available interactive choice buttons."""
        for idx, choice in enumerate(event.choices[:3]):
            btn_rect = self.choice_rects[idx]
            is_avail = choice.is_available(session.state)
            is_hovered = (self._hovered_choice == idx and is_avail)

            # Button Background
            bg_surf = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
            bg_surf.fill((16, 20, 32, 235) if is_avail else (12, 12, 16, 210))
            surface.blit(bg_surf, btn_rect.topleft)

            # Golden Frame
            assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=16)

            if is_hovered:
                glow = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
                glow.fill((255, 215, 0, 45))
                surface.blit(glow, btn_rect.topleft)

            # Choice Label
            avail_tag = "" if is_avail else " [UNAVAILABLE]"
            full_label = f"[{idx + 1}]  {choice.label}{avail_tag}"

            text_col = ThemeToken.TEXT_HIGHLIGHT if is_hovered else (ThemeToken.TEXT_NORMAL if is_avail else ThemeToken.TEXT_MUTED)

            renderer.draw_text(
                surface,
                full_label,
                btn_rect.centerx,
                btn_rect.centery - 6,
                token=text_col,
                size=14,
                bold=is_hovered or is_avail,
                align="center",
            )

    def _draw_continue_button(self, surface: pygame.Surface, renderer: PygameRenderer) -> None:
        """Render centered continue button when event is resolved or no choices exist."""
        btn_rect = self.cont_rect
        is_hovered = (self._hovered_btn == "continue")

        bg_surf = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
        bg_surf.fill((16, 20, 32, 240))
        surface.blit(bg_surf, btn_rect.topleft)

        assets.draw_frame(surface, "frame_button_gold", btn_rect, margin=18)

        if is_hovered:
            glow = pygame.Surface(btn_rect.size, pygame.SRCALPHA)
            glow.fill((255, 215, 0, 50))
            surface.blit(glow, btn_rect.topleft)

        btn_txt = "[ SPACE ] CONTINUE" if i18n.locale == "en" else "[ ESPACIO ] CONTINUAR"
        renderer.draw_text(
            surface,
            btn_txt,
            btn_rect.centerx,
            btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if is_hovered else ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )
