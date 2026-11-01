"""Pygame-CE Combat Presentation View."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
import pygame

from src.core.events import DamageDealtEvent, HealthRestoredEvent
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.views.base import PygameView

if TYPE_CHECKING:
    from src.core.session import GameSession
    from src.frontends.pygame_ce.renderer import PygameRenderer


@dataclass
class FloatingNumber:
    """Animated damage or healing popup text in the arena."""
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    lifetime: float = 1.0  # seconds
    max_lifetime: float = 1.0


class PygameCombatView(PygameView):
    """Combat view rendering high-DPI health bars, animated popups, and battle log."""

    def __init__(self) -> None:
        self.popups: list[FloatingNumber] = []
        self.auto_advance_timer: float = 0.0
        self.step_interval: float = 0.45  # Default combat speed (seconds per tick)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and combat interaction."""
        if not session.combat:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._tick_combat(session)
            elif event.key == pygame.K_z:
                # Cycle speed intervals: 0.45s -> 0.20s -> 0.08s
                if self.step_interval > 0.3:
                    self.step_interval = 0.20
                elif self.step_interval > 0.15:
                    self.step_interval = 0.08
                else:
                    self.step_interval = 0.45
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                # Belt item usage
                idx = event.key - pygame.K_1
                if idx < len(session.player.inventory.belt):
                    session.player.inventory.use_belt_item(idx, session.player)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._tick_combat(session)

    def _tick_combat(self, session: GameSession) -> None:
        """Advance combat simulation tick and collect domain events for visuals."""
        if not session.combat:
            return

        session.update_combat()

        # Drain events to spawn floating popups
        for ev in session.drain_events():
            if isinstance(ev, DamageDealtEvent):
                # If target is enemy -> spawn on right, if hero -> spawn on left
                is_hero = (ev.target == session.player.name)
                px = 240 if is_hero else 720
                py = 180
                txt = f"-{ev.amount}!" if ev.is_crit else f"-{ev.amount}"
                col = (255, 236, 39) if ev.is_crit else (255, 80, 80)
                self.popups.append(FloatingNumber(x=px, y=py, text=txt, color=col))

            elif isinstance(ev, HealthRestoredEvent):
                px = 240 if ev.target == session.player.name else 720
                py = 180
                self.popups.append(
                    FloatingNumber(x=px, y=py, text=f"+{ev.amount}", color=(80, 240, 100))
                )

    def update(self, dt: float, session: GameSession) -> None:
        """Update popup animations and auto-advance combat ticks."""
        # Update floating combat numbers
        for p in self.popups:
            p.y -= 35 * dt  # Float upwards
            p.lifetime -= dt
        self.popups = [p for p in self.popups if p.lifetime > 0]

        if not session.combat or not session.combat.is_active():
            return

        # Auto-step timer
        self.auto_advance_timer += dt
        if self.auto_advance_timer >= self.step_interval:
            self.auto_advance_timer = 0.0
            self._tick_combat(session)

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Draw combat arena, fighters, health bars, and combat log."""
        if not session.combat:
            return

        surface_w = surface.get_width()
        surface_h = surface.get_height()
        combat = session.combat
        player = session.player
        enemy = combat.enemy

        # Arena Background Panel
        arena_rect = pygame.Rect(40, 30, surface_w - 80, 260)
        renderer.draw_panel(
            surface,
            arena_rect,
            bg_token=ThemeToken.PANEL_BG,
            border_token=ThemeToken.BORDER,
            border_width=2,
            border_radius=8,
        )

        # 1. Player Side (Left)
        renderer.draw_text(
            surface,
            player.name.upper(),
            80,
            50,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=22,
            bold=True,
        )
        renderer.draw_text(
            surface,
            f"Level {player.level} {player.class_id.capitalize()}",
            80,
            80,
            token=ThemeToken.TEXT_MUTED,
            size=14,
        )

        # Player Health Bar
        p_hp_rect = pygame.Rect(80, 110, 260, 24)
        renderer.draw_progress_bar(
            surface,
            p_hp_rect,
            current=player.current_hp,
            maximum=player.max_hp,
            fill_token=ThemeToken.HP_FILL,
            label=f"HP {player.current_hp}/{player.max_hp}",
        )

        # Player Shield Bar (if any)
        if player.shield > 0:
            p_sh_rect = pygame.Rect(80, 138, 260, 14)
            renderer.draw_progress_bar(
                surface,
                p_sh_rect,
                current=player.shield,
                maximum=player.max_hp,
                fill_token=ThemeToken.SHIELD_FILL,
                label=f"BARRIER: {player.shield}",
            )

        # 2. Enemy Side (Right)
        e_x = surface_w - 340
        renderer.draw_text(
            surface,
            enemy.name.upper(),
            e_x,
            50,
            token=ThemeToken.TEXT_ALERT,
            size=22,
            bold=True,
        )
        renderer.draw_text(
            surface,
            f"Tier: {getattr(enemy, 'tier', 'Common')}",
            e_x,
            80,
            token=ThemeToken.TEXT_MUTED,
            size=14,
        )

        # Enemy Health Bar
        e_hp_rect = pygame.Rect(e_x, 110, 260, 24)
        renderer.draw_progress_bar(
            surface,
            e_hp_rect,
            current=enemy.current_hp,
            maximum=enemy.max_hp,
            fill_token=ThemeToken.HP_FILL,
            label=f"HP {enemy.current_hp}/{enemy.max_hp}",
        )

        # 3. Floating Numbers
        for p in self.popups:
            font = renderer.get_font(size=20, bold=True)
            txt_surf = font.render(p.text, True, p.color)
            alpha = int(255 * (p.lifetime / p.max_lifetime))
            txt_surf.set_alpha(alpha)
            surface.blit(txt_surf, (int(p.x), int(p.y)))

        # 4. Action Bar / Instructions
        action_rect = pygame.Rect(40, 305, surface_w - 80, 48)
        renderer.draw_panel(
            surface,
            action_rect,
            bg_token=ThemeToken.PANEL_BG,
            border_token=ThemeToken.BORDER_MUTED,
            border_width=1,
            border_radius=6,
        )

        speed_text = "1x" if self.step_interval > 0.3 else ("2x" if self.step_interval > 0.15 else "4x")
        renderer.draw_text(
            surface,
            f"[SPACE/CLICK] Advance Turn  |  [Z] Speed ({speed_text})  |  [1-3] Belt Potions",
            action_rect.centerx,
            action_rect.centery - 8,
            token=ThemeToken.TEXT_NORMAL,
            size=14,
            bold=True,
            align="center",
        )

        # 5. Combat Log Panel
        log_rect = pygame.Rect(40, 368, surface_w - 80, 140)
        renderer.draw_panel(
            surface,
            log_rect,
            bg_token=ThemeToken.PANEL_BG,
            border_token=ThemeToken.BORDER,
            border_width=1,
            border_radius=6,
        )

        renderer.draw_text(
            surface,
            "BATTLE LOG",
            log_rect.x + 16,
            log_rect.y + 12,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
        )

        recent_logs = combat.combat_logs[-4:] if combat.combat_logs else []
        for idx, line in enumerate(recent_logs):
            renderer.draw_text(
                surface,
                f"> {line}",
                log_rect.x + 20,
                log_rect.y + 36 + idx * 24,
                token=ThemeToken.TEXT_MUTED if idx < len(recent_logs) - 1 else ThemeToken.TEXT_NORMAL,
                size=13,
            )
