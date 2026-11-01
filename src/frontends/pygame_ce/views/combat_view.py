"""Pygame-CE Combat Presentation View with Speed Gauges, Abilities, QTEs, and Statuses."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING
import pygame

from src.core.events import DamageDealtEvent, HealthRestoredEvent
from src.core.game_state import GameMode
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
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
    lifetime: float = 1.0
    max_lifetime: float = 1.0


class PygameCombatView(PygameView):
    """Rich combat view rendering speed gauges, active skill decks, status effects, and QTEs."""

    def __init__(self) -> None:
        self.popups: list[FloatingNumber] = []
        self.auto_advance_timer: float = 0.0
        self.step_interval: float = 0.40  # Default speed
        self._hovered_btn: str | None = None

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and combat interaction."""
        if not session.combat:
            return

        combat = session.combat

        # If QTE is active, handle QTE key/mouse interaction
        if combat.is_qte_active() and combat.active_qte:
            qte = combat.active_qte
            if qte.summary_active:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN)) or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    combat.dismiss_qte_summary()
                    if not combat.is_qte_active() and not combat.is_active():
                        session.update_combat()
                return

            if qte.in_intro:
                if (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN)) or \
                   (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    qte.intro_frames = 0
                return

            target = qte.current_target
            if target is not None and not target.resolved:
                if event.type == pygame.KEYDOWN:
                    pressed_num = None
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        pressed_num = 1
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        pressed_num = 2
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        pressed_num = 3
                    elif event.key == pygame.K_SPACE:
                        pressed_num = target.number

                    if pressed_num is not None:
                        if pressed_num == target.number:
                            combat.resolve_qte_target(target.current_accuracy())
                        else:
                            combat.resolve_qte_target(0)
                        return

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    tx = int(target.x * (960 / 256))
                    ty = int(target.y * (540 / 256))
                    tr = int(target.button_radius * 2.8) + 14
                    dist = math.hypot(event.pos[0] - tx, event.pos[1] - ty)
                    if dist <= tr:
                        combat.resolve_qte_target(target.current_accuracy())
                    else:
                        combat.resolve_qte_target(0)
                    return
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._tick_combat(session)
            elif event.key == pygame.K_z:
                # Cycle speed intervals: 0.40s -> 0.18s -> 0.06s
                if self.step_interval > 0.3:
                    self.step_interval = 0.18
                elif self.step_interval > 0.10:
                    self.step_interval = 0.06
                else:
                    self.step_interval = 0.40
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = event.key - pygame.K_1
                if idx < len(session.player.inventory.belt):
                    session.player.inventory.use_belt_item(idx, session.player)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Belt potion clicks
            for b_idx in range(len(session.player.inventory.belt)):
                b_rect = pygame.Rect(40 + b_idx * 140, 310, 130, 36)
                if b_rect.collidepoint(pos):
                    session.player.inventory.use_belt_item(b_idx, session.player)
                    return

            # Speed toggle click
            speed_rect = pygame.Rect(480, 310, 100, 36)
            if speed_rect.collidepoint(pos):
                if self.step_interval > 0.3:
                    self.step_interval = 0.18
                elif self.step_interval > 0.10:
                    self.step_interval = 0.06
                else:
                    self.step_interval = 0.40
                return

            # Advance turn arena click
            arena_rect = pygame.Rect(40, 20, 880, 275)
            if arena_rect.collidepoint(pos):
                self._tick_combat(session)

    def _tick_combat(self, session: GameSession) -> None:
        """Advance combat simulation tick and collect domain events for visuals."""
        if not session.combat:
            return

        session.update_combat()

        for ev in session.drain_events():
            if isinstance(ev, DamageDealtEvent):
                is_hero = (ev.target == session.player.name)
                px = 220 if is_hero else 720
                py = 140
                txt = f"-{ev.amount}!" if ev.is_crit else f"-{ev.amount}"
                col = (255, 236, 39) if ev.is_crit else (255, 80, 80)
                self.popups.append(FloatingNumber(x=px, y=py, text=txt, color=col))

            elif isinstance(ev, HealthRestoredEvent):
                px = 220 if ev.target == session.player.name else 720
                py = 140
                self.popups.append(FloatingNumber(x=px, y=py, text=f"+{ev.amount}", color=(80, 240, 100)))

    def update(self, dt: float, session: GameSession) -> None:
        """Update popup animations, auto-advance ticks, and QTE timer."""
        for p in self.popups:
            p.y -= 35 * dt
            p.lifetime -= dt
        self.popups = [p for p in self.popups if p.lifetime > 0]

        if not session.combat or not session.combat.is_active():
            return

        # Advance QTE if active
        if session.combat.is_qte_active() and session.combat.active_qte:
            qte = session.combat.active_qte
            if qte.summary_active:
                qte.summary_frames -= 1
                if qte.summary_frames <= 0:
                    session.combat.dismiss_qte_summary()
                    if not session.combat.is_qte_active() and not session.combat.is_active():
                        session.update_combat()
                return

            if qte.in_intro:
                qte.intro_frames -= 1
                return

            target = qte.current_target
            if target is None:
                return

            if target.resolved:
                target.feedback_frames -= 1
                if target.feedback_frames <= 0:
                    session.combat.advance_qte_after_feedback()
                return

            if target.step_shrink():
                session.combat.resolve_qte_target(0)
            return

        # Auto-step timer
        self.auto_advance_timer += dt
        if self.auto_advance_timer >= self.step_interval:
            self.auto_advance_timer = 0.0
            self._tick_combat(session)

    def draw(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Draw combat arena over 16-bit SNES background with gauges, fighters, and log."""
        if not session.combat:
            return

        surface_w = surface.get_width()
        combat = session.combat
        player = session.player
        enemy = combat.enemy

        # 1. 16-Bit SNES Background
        biome = getattr(session.state, "current_biome", "cathedral")
        assets.draw_background(surface, biome, vignette_alpha=120)

        # 2. Arena Stage Container
        arena_rect = pygame.Rect(40, 20, surface_w - 80, 275)
        renderer.draw_panel(surface, arena_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.BORDER, border_width=2, border_radius=8)

        # ---------------- HERO SIDE (LEFT) ----------------
        # Hero Portrait
        h_portrait = assets.get_class_portrait(player.class_id, scale=1)
        if h_portrait:
            surface.blit(h_portrait, (60, 40))

        # Hero Name & Level
        renderer.draw_text(surface, player.name.upper(), 125, 40, token=ThemeToken.TEXT_HIGHLIGHT, size=18, bold=True)
        renderer.draw_text(surface, f"Lvl {player.level} {player.class_id.capitalize()}", 125, 62, token=ThemeToken.TEXT_MUTED, size=12)

        # Hero Health Bar
        p_hp_rect = pygame.Rect(125, 85, 240, 20)
        renderer.draw_progress_bar(surface, p_hp_rect, current=player.current_hp, maximum=player.max_hp, fill_token=ThemeToken.HP_FILL, label=f"HP {player.current_hp}/{player.max_hp}")

        # Hero Barrier (Shield) Bar
        if player.shield > 0:
            sh_rect = pygame.Rect(125, 108, 240, 10)
            renderer.draw_progress_bar(surface, sh_rect, current=player.shield, maximum=player.max_hp, fill_token=ThemeToken.SHIELD_FILL, label=f"Shield: {player.shield}")

        # Hero Action Speed Gauge (0..100)
        p_gauge = getattr(combat, "player_gauge", 0)
        p_gauge_rect = pygame.Rect(125, 122, 240, 10)
        renderer.draw_progress_bar(surface, p_gauge_rect, current=min(100, int(p_gauge)), maximum=100, fill_token=ThemeToken.ACCENT_PRIMARY, label="ACTION SPEED")

        # Evade Charges Badge
        if getattr(player, "evade_charges", 0) > 0:
            renderer.draw_text(surface, f"EVADE: {player.evade_charges}", 125, 138, token=ThemeToken.ACCENT_SECONDARY, size=11, bold=True)

        # Hero Status Effects
        if hasattr(player, "statuses") and player.statuses:
            s_text = " ".join([f"[{s.name.capitalize()}:{s.duration}t]" for s in player.statuses])
            renderer.draw_text(surface, s_text, 125, 155, token=ThemeToken.TEXT_ALERT, size=11, bold=True)

        # ---------------- ENEMY SIDE (RIGHT) ----------------
        e_x = surface_w - 380

        # Biome Enemy Sprite (48x48)
        e_sprite = assets.get_enemy_sprite(enemy.name, scale=3)
        if e_sprite:
            surface.blit(e_sprite, (surface_w - 110, 45))

        # Enemy Name & Tier
        tier_label = getattr(enemy, "tier", "MONSTER")
        tier_str = tier_label.name if hasattr(tier_label, "name") else str(tier_label)
        renderer.draw_text(surface, enemy.name.upper(), e_x, 40, token=ThemeToken.TEXT_ALERT, size=18, bold=True)
        renderer.draw_text(surface, f"Tier: {tier_str}", e_x, 62, token=ThemeToken.TEXT_MUTED, size=12)

        # Enemy Health Bar
        e_hp_rect = pygame.Rect(e_x, 85, 240, 20)
        renderer.draw_progress_bar(surface, e_hp_rect, current=enemy.current_hp, maximum=enemy.max_hp, fill_token=ThemeToken.HP_FILL, label=f"HP {enemy.current_hp}/{enemy.max_hp}")

        # Enemy Action Speed Gauge (0..100)
        e_gauge = getattr(combat, "enemy_gauge", 0)
        e_gauge_rect = pygame.Rect(e_x, 108, 240, 10)
        renderer.draw_progress_bar(surface, e_gauge_rect, current=min(100, int(e_gauge)), maximum=100, fill_token=ThemeToken.ACCENT_PRIMARY, label="ACTION SPEED")

        # Enemy Intent / Speech Bubble
        bubble = getattr(combat, "enemy_speech_bubble", None)
        if bubble:
            bubble_rect = pygame.Rect(e_x - 30, 130, 270, 32)
            renderer.draw_panel(surface, bubble_rect, bg_token=ThemeToken.BG, border_token=ThemeToken.ACCENT_PRIMARY)
            renderer.draw_text(surface, f"Intent: {bubble}", bubble_rect.centerx, bubble_rect.centery - 6, token=ThemeToken.TEXT_HIGHLIGHT, size=11, bold=True, align="center")

        # Enemy Statuses
        if hasattr(enemy, "statuses") and enemy.statuses:
            es_text = " ".join([f"[{s.name.capitalize()}:{s.duration}t]" for s in enemy.statuses])
            renderer.draw_text(surface, es_text, e_x, 168, token=ThemeToken.TEXT_ALERT, size=11, bold=True)

        # ---------------- FLOATING POPUP NUMBERS ----------------
        for p in self.popups:
            font = renderer.get_font(size=20, bold=True)
            txt_surf = font.render(p.text, True, p.color)
            alpha = int(255 * (p.lifetime / p.max_lifetime))
            txt_surf.set_alpha(alpha)
            surface.blit(txt_surf, (int(p.x), int(p.y)))

        # 3. Middle Action Bar (Belt items & speed)
        bar_rect = pygame.Rect(40, 305, surface_w - 80, 48)
        renderer.draw_panel(surface, bar_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.BORDER_MUTED)

        # Belt quick slots
        belt = player.inventory.belt
        for b_idx in range(3):
            b_rect = pygame.Rect(55 + b_idx * 135, 311, 125, 36)
            if b_idx < len(belt) and belt[b_idx] is not None:
                renderer.draw_button(surface, b_rect, f"[{b_idx+1}] {belt[b_idx].name}", accent_token=ThemeToken.ACCENT_PRIMARY, font_size=11)
            else:
                renderer.draw_panel(surface, b_rect, border_token=ThemeToken.BORDER_MUTED)
                renderer.draw_text(surface, f"[{b_idx+1}] Empty", b_rect.centerx, b_rect.centery - 6, token=ThemeToken.BORDER_MUTED, size=11, align="center")

        # Speed Toggle
        speed_label = "1x" if self.step_interval > 0.3 else ("2x" if self.step_interval > 0.10 else "4x")
        speed_rect = pygame.Rect(480, 311, 110, 36)
        renderer.draw_button(surface, speed_rect, f"[Z] SPEED: {speed_label}", accent_token=ThemeToken.ACCENT_SECONDARY, font_size=11)

        # Advance instruction
        renderer.draw_text(surface, "[SPACE] Tick Turn", surface_w - 60, 322, token=ThemeToken.TEXT_NORMAL, size=13, bold=True, align="right")

        # 4. Battle Log Panel
        log_rect = pygame.Rect(40, 365, surface_w - 80, 150)
        renderer.draw_panel(surface, log_rect, bg_token=ThemeToken.PANEL_BG, border_token=ThemeToken.BORDER)

        renderer.draw_text(surface, "BATTLE LOG", log_rect.x + 16, log_rect.y + 12, token=ThemeToken.TEXT_HIGHLIGHT, size=14, bold=True)

        recent_logs = combat.combat_logs[-5:] if combat.combat_logs else []
        for idx, line in enumerate(recent_logs):
            renderer.draw_text(surface, f"> {line}", log_rect.x + 20, log_rect.y + 36 + idx * 22, token=ThemeToken.TEXT_MUTED if idx < len(recent_logs) - 1 else ThemeToken.TEXT_NORMAL, size=12)

        # ---------------- QTE MODAL OVERLAY ----------------
        if combat.is_qte_active() and combat.active_qte:
            self._draw_qte(surface, renderer, combat.active_qte)

    def _draw_qte(self, surface: pygame.Surface, renderer: PygameRenderer, qte) -> None:
        """Render darkened battle overlay with intro banner, shrinking rings, or summary."""
        w, h = surface.get_width(), surface.get_height()

        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 160))
        surface.blit(backdrop, (0, 0))

        if qte.in_intro:
            box = pygame.Rect(w // 2 - 250, 150, 500, 160)
            renderer.draw_panel(surface, box, bg_token=ThemeToken.BG, border_token=ThemeToken.TEXT_ALERT, border_width=3, border_radius=8)
            renderer.draw_text(surface, "¡CLASH OF MIGHT!", box.centerx, box.y + 20, token=ThemeToken.TEXT_HIGHLIGHT, size=20, bold=True, align="center")
            renderer.draw_text(surface, "Elite / Boss Critical Technique Incoming!", box.centerx, box.y + 55, token=ThemeToken.TEXT_NORMAL, size=14, bold=True, align="center")
            renderer.draw_text(surface, "Press [1, 2, 3] or [SPACE] as the outer ring meets the button!", box.centerx, box.y + 85, token=ThemeToken.ACCENT_PRIMARY, size=13, align="center")
            renderer.draw_text(surface, "[Press SPACE or CLICK to Begin]", box.centerx, box.y + 120, token=ThemeToken.TEXT_MUTED, size=12, align="center")
            return

        if qte.summary_active:
            box = pygame.Rect(w // 2 - 260, 140, 520, 190)
            tier_token = ThemeToken.TEXT_HIGHLIGHT if qte.final_tier == "perfect" else (ThemeToken.ACCENT_PRIMARY if qte.final_tier == "amazing" else ThemeToken.BORDER_MUTED)
            renderer.draw_panel(surface, box, bg_token=ThemeToken.BG, border_token=tier_token, border_width=3, border_radius=8)
            renderer.draw_text(surface, "TECHNIQUE RESOLUTION", box.centerx, box.y + 16, token=ThemeToken.TEXT_HIGHLIGHT, size=18, bold=True, align="center")
            renderer.draw_text(surface, f"{qte.final_tier.upper()} ({qte.final_score}%)", box.centerx, box.y + 44, token=tier_token, size=16, bold=True, align="center")

            sy = box.y + 75
            for b_line in qte.bonuses_applied[:4]:
                renderer.draw_text(surface, f"* {b_line}", box.centerx, sy, token=ThemeToken.TEXT_NORMAL, size=12, bold=True, align="center")
                sy += 20

            renderer.draw_text(surface, "[Press SPACE or CLICK to Continue]", box.centerx, box.bottom - 26, token=ThemeToken.TEXT_MUTED, size=12, align="center")
            return

        target = qte.current_target
        if target is None:
            return

        # Header step banner
        step_banner = pygame.Rect(w // 2 - 190, 20, 380, 36)
        renderer.draw_panel(surface, step_banner, bg_token=ThemeToken.BG, border_token=ThemeToken.ACCENT_PRIMARY, border_width=2, border_radius=6)
        renderer.draw_text(surface, f"DEFENSE REACTION: {qte.current_index + 1} OF {len(qte.targets)}", step_banner.centerx, step_banner.centery - 7, token=ThemeToken.TEXT_HIGHLIGHT, size=13, bold=True, align="center")

        tx = int(target.x * (w / 256))
        ty = int(target.y * (h / 256))
        br = int(target.button_radius * 2.8)

        if not target.resolved:
            acc = target.current_accuracy()
            ring_col = (255, 236, 39) if acc >= 81 else ((0, 228, 255) if acc >= 61 else ((0, 231, 86) if acc >= 41 else (255, 255, 255)))
            cr = max(br + 2, int(target.current_radius * 2.8))

            pygame.draw.circle(surface, ring_col, (tx, ty), cr, width=3)
            pygame.draw.circle(surface, (20, 24, 40), (tx, ty), br)
            pygame.draw.circle(surface, (255, 236, 39), (tx, ty), br, width=2)
            renderer.draw_text(surface, str(target.number), tx, ty - 10, token=ThemeToken.TEXT_HIGHLIGHT, size=20, bold=True, align="center")
        else:
            tier_col = (255, 236, 39) if target.tier == "perfect" else ((0, 228, 255) if target.tier == "amazing" else ((0, 231, 86) if target.tier in ("nice", "good") else (255, 80, 80)))
            pygame.draw.circle(surface, (15, 15, 20), (tx, ty), br)
            pygame.draw.circle(surface, tier_col, (tx, ty), br, width=3)
            renderer.draw_text(surface, f"{target.tier.upper()} {target.score}%", tx, ty - 8, token=ThemeToken.TEXT_HIGHLIGHT, size=13, bold=True, align="center")
