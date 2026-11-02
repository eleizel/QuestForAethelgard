"""Pygame-CE Combat Presentation View with Speed Gauges, Abilities, QTEs, and Statuses.

Faithfully implements the 16-bit Super Nintendo JRPG combat design:
- Reusable Top Status Bar (TopHUDComponent)
- Biome-specific Combat Arena with 9-slice gold ornate frame
- Hero (left) and Enemy (right, facing left) combat sprites
- 16-bit status badges with safe margins
- Symmetrical Player & Enemy status windows with HP bars, numeric stats, and avatars
- Dual ATB Tick Gauges (Cyan for Player, Orange for Enemy)
- 3 Belt Item slots (navigable via [1, 2, 3] or mouse clicks)
- Active Abilities box with states: CAST, WAIT, and CD X
- 16-bit Battle Log panel
- Interactive QTE clash sequence overlay
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import TYPE_CHECKING
import pygame

from src.core.events import DamageDealtEvent, HealthRestoredEvent
from src.core.i18n import t
from src.core.theme import ThemeToken
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.components.top_hud import TopHUDComponent
from src.frontends.pygame_ce.views.base import PygameView
from src.systems.combat import ACTION_THRESHOLD, CombatResult
from src.systems.inventory import MAX_BELT_SLOTS

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
    """Authentic 16-bit SNES JRPG combat view."""

    SPEED_STEPS = [0.40, 0.18, 0.06]
    SPEED_LABELS = ["1x", "2x", "4x"]

    def __init__(self) -> None:
        self.top_hud = TopHUDComponent()
        self.popups: list[FloatingNumber] = []
        self.auto_advance_timer: float = 0.0
        self.speed_idx: int = 0
        self.player_flash: int = 0
        self.enemy_flash: int = 0
        self.shake_frames: int = 0
        self._hovered_btn: str | None = None
        self.selected_belt_idx: int = 0

        # Clickable rects for mouse interaction
        self.victory_active: bool = False
        self.victory_timer: float = 0.0
        self.victory_duration: float = 2.5

        self.arena_rect = pygame.Rect(8, 56, 944, 176)
        self.speed_btn_rect = pygame.Rect(860, 64, 84, 26)
        self.belt_rects = [
            pygame.Rect(56, 396, 68, 48),
            pygame.Rect(174, 396, 68, 48),
            pygame.Rect(292, 396, 68, 48),
        ]
        self.ability_rects = [
            pygame.Rect(440, 392, 490, 24),
            pygame.Rect(440, 420, 490, 24),
        ]

    @property
    def step_interval(self) -> float:
        return self.SPEED_STEPS[self.speed_idx]

    def _cycle_speed(self) -> None:
        self.speed_idx = (self.speed_idx + 1) % len(self.SPEED_STEPS)

    def handle_event(self, event: pygame.event.Event, session: GameSession) -> None:
        """Process keyboard shortcuts and combat interaction."""
        # Top HUD buttons take priority for navigation
        if self.top_hud.handle_event(event, session):
            return

        if not session.combat:
            return

        combat = session.combat

        # Invalidate all player actions if battle is finished or victory modal is active
        if self.victory_active or not combat.is_active() or combat.result != CombatResult.IN_PROGRESS:
            return

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
                self._cycle_speed()
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = event.key - pygame.K_1
                self.selected_belt_idx = idx
                self._use_belt_item(idx, session)
            elif event.key in (pygame.K_4, pygame.K_5):
                ab_idx = event.key - pygame.K_4
                self._queue_ability(ab_idx, session)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Speed toggle click
            if self.speed_btn_rect.collidepoint(pos):
                self._cycle_speed()
                return

            # Belt item clicks
            for idx, rect in enumerate(self.belt_rects):
                if rect.collidepoint(pos):
                    self.selected_belt_idx = idx
                    self._use_belt_item(idx, session)
                    return

            # Ability clicks
            for idx, rect in enumerate(self.ability_rects):
                if rect.collidepoint(pos):
                    self._queue_ability(idx, session)
                    return

            # Arena click advances combat turn
            if self.arena_rect.collidepoint(pos):
                self._tick_combat(session)

    def _use_belt_item(self, idx: int, session: GameSession) -> None:
        """Use an item from the player belt and record log."""
        if not session.combat:
            return
        inv = session.player.inventory
        if idx < len(inv.belt) and inv.belt[idx] is not None:
            item_name = inv.belt[idx].name
            if inv.use_belt_item(idx, session.player):
                session.combat.combat_logs.append(f"{session.player.name} uses {item_name}!")
                self._detect_deltas(session)

    def _queue_ability(self, ab_idx: int, session: GameSession) -> None:
        """Queue or report cooldown for an active ability."""
        if not session.combat:
            return
        combat = session.combat
        active_skills = session.player.abilities.active
        if ab_idx < len(active_skills):
            ab = active_skills[ab_idx]
            rem_cd = combat.get_cooldown(ab)
            if rem_cd <= 0:
                combat.queued_ability = ab
                combat.combat_logs.append(t("combat_queued", ability=ab.name))
            else:
                combat.combat_logs.append(t("combat_cooldown", cooldown=rem_cd))

    def _detect_deltas(self, session: GameSession) -> None:
        """Process domain events and trigger screen shake/flash."""
        for ev in session.drain_events():
            if isinstance(ev, DamageDealtEvent):
                is_hero = (ev.target == session.player.name)
                px = 240 if is_hero else 690
                py = 130
                txt = f"-{ev.amount}!" if ev.is_crit else f"-{ev.amount}"
                col = (255, 236, 39) if ev.is_crit else (255, 80, 80)
                self.popups.append(FloatingNumber(x=px, y=py, text=txt, color=col))
                if is_hero:
                    self.player_flash = 3
                    if ev.is_crit:
                        self.shake_frames = 5
                else:
                    self.enemy_flash = 3
                    if ev.is_crit:
                        self.shake_frames = 6

            elif isinstance(ev, HealthRestoredEvent):
                px = 240 if ev.target == session.player.name else 690
                py = 130
                self.popups.append(FloatingNumber(x=px, y=py, text=f"+{ev.amount}", color=(80, 240, 100)))

    def _tick_combat(self, session: GameSession) -> None:
        """Advance combat simulation tick and collect domain events."""
        if not session.combat:
            return
        session.update_combat()
        self._detect_deltas(session)

    def update(self, dt: float, session: GameSession) -> None:
        """Update popup animations, auto-advance ticks, and QTE timer."""
        pos = pygame.mouse.get_pos()
        self.top_hud.update(pos)

        # Check button hovers
        if self.speed_btn_rect.collidepoint(pos):
            self._hovered_btn = "speed"
        else:
            self._hovered_btn = None

        # Update popup animations
        for p in self.popups:
            p.y -= 35 * dt
            p.lifetime -= dt
        self.popups = [p for p in self.popups if p.lifetime > 0]

        if not session.combat:
            return

        combat = session.combat

        # 1. Player Defeat: immediately progress to defeat view (no victory modal)
        if combat.result == CombatResult.PLAYER_DEFEAT or session.player.current_hp <= 0:
            combat.completion_delay_ticks = 0
            session.update_combat()
            return

        # 2. Player Victory: trigger golden victory modal and 2.5s countdown
        if combat.result == CombatResult.PLAYER_VICTORY or (combat.enemy and combat.enemy.current_hp <= 0):
            if not self.victory_active:
                self.victory_active = True
                self.victory_timer = self.victory_duration
                try:
                    from src.systems.audio_manager import audio_manager, AudioCue
                    audio_manager.play_cue(AudioCue.VICTORY)
                except Exception:
                    pass

            self.victory_timer -= dt
            if self.victory_timer <= 0.0:
                self.victory_active = False
                combat.completion_delay_ticks = 0
                session.update_combat()
            return

        if not combat.is_active():
            combat.completion_delay_ticks = 0
            session.update_combat()
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
        """Render complete 16-bit SNES combat view matching design specification."""
        if not session.combat:
            return

        surface_w = surface.get_width()
        combat = session.combat
        player = session.player
        enemy = combat.enemy
        biome = getattr(session.state, "current_biome", "arboretum")

        # Handle screen shake
        orig_surface = surface
        if self.shake_frames > 0:
            self.shake_frames -= 1
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)
            shaked = pygame.Surface(surface.get_size())
            surface = shaked

        # Fill background with deep gothic dark tone
        surface.fill((12, 10, 16))

        # =========================================================================
        # 1. TOP HUD STATUS BAR (y = 6 to y = 52) - Reusable TopHUDComponent
        # =========================================================================
        self.top_hud.draw(surface, renderer, session)

        # =========================================================================
        # 2. COMBAT ARENA VIEWPORT (y = 56 to y = 232, h = 176)
        # =========================================================================
        arena_rect = self.arena_rect
        arena_rect.width = surface_w - 16

        # Draw Arena Vista Background
        arena_bg = assets.get_combat_arena_bg(biome, size=(arena_rect.width, arena_rect.height))
        if arena_bg:
            surface.blit(arena_bg, arena_rect.topleft)
        else:
            pygame.draw.rect(surface, (18, 15, 25), arena_rect)

        # Dim arena background slightly so combatant sprites pop and do not blend into scenery
        arena_dim = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        arena_dim.fill((0, 0, 0, 75))
        surface.blit(arena_dim, arena_rect.topleft)

        # Vignette / subtle dark gradient along the top and bottom of arena
        vignette = pygame.Surface((arena_rect.width, 30), pygame.SRCALPHA)
        vignette.fill((0, 0, 0, 80))
        surface.blit(vignette, arena_rect.topleft)

        # ---------------- COMBATANT SHADOWS ----------------
        hero_center_x = 280
        ground_y = arena_rect.bottom - 22
        enemy_center_x = 690

        hero_shadow = pygame.Surface((60, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(hero_shadow, (0, 0, 0, 110), (0, 0, 60, 14))
        surface.blit(hero_shadow, (hero_center_x - 30, ground_y - 6))

        enemy_shadow = pygame.Surface((80, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(enemy_shadow, (0, 0, 0, 110), (0, 0, 80, 16))
        surface.blit(enemy_shadow, (enemy_center_x - 40, ground_y - 6))

        # ---------------- HERO SPRITE (FACING RIGHT) ----------------
        hero_sprite = assets.get_class_sprite(player.class_id)
        if hero_sprite:
            # Scale proportionally so height is ~88px
            hw, hh = hero_sprite.get_size()
            target_h = 88
            target_w = max(1, int(hw * (target_h / hh)))
            hero_scaled = pygame.transform.smoothscale(hero_sprite, (target_w, target_h))

            # Hit flash effect
            if self.player_flash > 0:
                self.player_flash -= 1
                flash_surf = hero_scaled.copy()
                flash_surf.fill((255, 255, 255, 200), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(flash_surf, (hero_center_x - target_w // 2, ground_y - target_h + 4))
            else:
                surface.blit(hero_scaled, (hero_center_x - target_w // 2, ground_y - target_h + 4))

        # ---------------- ENEMY SPRITE (FACING LEFT) ----------------
        arch_id = getattr(enemy, "archetype_id", None) or enemy.name
        enemy_sprite = assets.get_enemy_sprite(arch_id, max_height=95)
        if enemy_sprite:
            ew, eh = enemy_sprite.get_size()
            ex = enemy_center_x - ew // 2
            ey = ground_y - eh + 4

            if self.enemy_flash > 0:
                self.enemy_flash -= 1
                flash_surf = enemy_sprite.copy()
                flash_surf.fill((255, 255, 255, 200), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(flash_surf, (ex, ey))
            else:
                surface.blit(enemy_sprite, (ex, ey))

        # ---------------- STATUS BADGES (LEFT FOR PLAYER, RIGHT FOR ENEMY) ----------------
        # Player statuses on left (x = 55..120)
        p_statuses = getattr(player, "statuses", [])
        badge_y = arena_rect.y + 34
        for s in p_statuses[:4]:
            b_bg_rect = pygame.Rect(55, badge_y - 2, 62, 26)
            s_bg = pygame.Surface((b_bg_rect.width, b_bg_rect.height), pygame.SRCALPHA)
            s_bg.fill((16, 12, 22, 210))
            surface.blit(s_bg, b_bg_rect.topleft)
            pygame.draw.rect(surface, (160, 130, 40), b_bg_rect, width=1, border_radius=3)

            b_icon = assets.get_status_icon(s.id, size=(22, 22))
            if b_icon:
                surface.blit(b_icon, (b_bg_rect.x + 2, b_bg_rect.y + 2))
            tag = f"{s.duration}t"
            if getattr(s, "stacks", 1) > 1:
                tag = f"x{s.stacks} {tag}"
            renderer.draw_text(surface, tag, b_bg_rect.x + 28, b_bg_rect.y + 5, token=ThemeToken.TEXT_HIGHLIGHT, size=11, bold=True, font_variant="alagard")
            badge_y += 30

        # Enemy statuses on right (x = arena_rect.right - 105..arena_rect.right - 45)
        e_statuses = getattr(enemy, "statuses", [])
        e_badge_y = arena_rect.y + 56
        for s in e_statuses[:4]:
            eb_bg_rect = pygame.Rect(arena_rect.right - 105, e_badge_y - 2, 62, 26)
            s_bg = pygame.Surface((eb_bg_rect.width, eb_bg_rect.height), pygame.SRCALPHA)
            s_bg.fill((16, 12, 22, 210))
            surface.blit(s_bg, eb_bg_rect.topleft)
            pygame.draw.rect(surface, (160, 130, 40), eb_bg_rect, width=1, border_radius=3)

            b_icon = assets.get_status_icon(s.id, size=(22, 22))
            if b_icon:
                surface.blit(b_icon, (eb_bg_rect.x + 2, eb_bg_rect.y + 2))
            tag = f"{s.duration}t"
            if getattr(s, "stacks", 1) > 1:
                tag = f"x{s.stacks} {tag}"
            renderer.draw_text(surface, tag, eb_bg_rect.x + 28, eb_bg_rect.y + 5, token=ThemeToken.TEXT_ALERT, size=11, bold=True, font_variant="alagard")
            e_badge_y += 30

        # ---------------- ENEMY INTENT / SPEECH BUBBLE ----------------
        bubble = getattr(combat, "enemy_speech_bubble", None)
        if bubble:
            bubble_font = renderer.get_font(size=12, variant="alagard")
            txt_w = bubble_font.size(f"Intent: {bubble}")[0]
            bw = max(110, txt_w + 20)
            bh = 26
            bx = min(arena_rect.right - bw - 20, max(arena_rect.x + 400, enemy_center_x - bw // 2))
            by = arena_rect.y + 16

            bubble_rect = pygame.Rect(bx, by, bw, bh)
            bubble_bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bubble_bg.fill((20, 16, 28, 230))
            surface.blit(bubble_bg, (bx, by))
            pygame.draw.rect(surface, (255, 215, 0), bubble_rect, width=1, border_radius=4)
            renderer.draw_text(surface, f"Intent: {bubble}", bx + bw // 2, by + 5, token=ThemeToken.TEXT_HIGHLIGHT, size=12, bold=True, align="center", font_variant="alagard")

        # ---------------- FLOATING POPUP NUMBERS ----------------
        for p in self.popups:
            font = renderer.get_font(size=18, bold=True, variant="alagard")
            txt_surf = font.render(p.text, True, p.color)
            alpha = min(255, max(0, int(255 * (p.lifetime / p.max_lifetime))))
            txt_surf.set_alpha(alpha)
            surface.blit(txt_surf, (int(p.x - txt_surf.get_width() // 2), int(p.y)))

        # ---------------- SPEED TOGGLE BUTTON (ARENA TOP RIGHT) ----------------
        self.speed_btn_rect = pygame.Rect(arena_rect.right - 105, arena_rect.y + 26, 76, 22)
        s_hover = (self._hovered_btn == "speed")
        s_frame = assets.get_9slice_frame("frame_button_gold", self.speed_btn_rect.width, self.speed_btn_rect.height, margin=14)
        if s_frame:
            surface.blit(s_frame, self.speed_btn_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), self.speed_btn_rect, width=2, border_radius=4)
        if s_hover:
            pygame.draw.rect(surface, (255, 255, 255), self.speed_btn_rect, width=1, border_radius=4)
        renderer.draw_text(
            surface,
            f"[Z] {self.SPEED_LABELS[self.speed_idx]}",
            self.speed_btn_rect.centerx,
            self.speed_btn_rect.centery - 6,
            token=ThemeToken.TEXT_HIGHLIGHT if s_hover else ThemeToken.TEXT_NORMAL,
            size=11,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # 9-Slice Gold Ornate Frame Overlay for Arena
        arena_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            arena_rect.width,
            arena_rect.height,
            margin=54,
            edge_margin=24,
            draw_center=False,
        )
        if arena_frame:
            surface.blit(arena_frame, arena_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), arena_rect, width=2, border_radius=6)

        # =========================================================================
        # 3. PLAYER & ENEMY STATUS WINDOWS (y = 238 to y = 312, h = 74)
        # =========================================================================
        gap = 10
        card_w = (surface_w - 16 - gap) // 2
        card_h = 74

        # --- PLAYER STATUS WINDOW (LEFT) ---
        p_card_rect = pygame.Rect(8, 238, card_w, card_h)
        self._draw_status_window(
            surface,
            renderer,
            p_card_rect,
            avatar_surf=assets.get_bust_portrait(player.class_id, size=(38, 38)),
            name=player.name,
            current_hp=player.current_hp,
            max_hp=player.max_hp,
            shield=getattr(player, "shield", 0),
            atk=player.effective_stats.attack,
            def_val=player.effective_stats.defense,
            spd=player.effective_stats.speed,
            crit=int(player.effective_stats.crit_chance * 100),
            is_enemy=False,
        )

        # --- ENEMY STATUS WINDOW (RIGHT) ---
        e_card_rect = pygame.Rect(8 + card_w + gap, 238, card_w, card_h)
        e_bust = assets.get_enemy_bust(arch_id, size=(38, 38))
        self._draw_status_window(
            surface,
            renderer,
            e_card_rect,
            avatar_surf=e_bust,
            name=enemy.display_name,
            current_hp=enemy.current_hp,
            max_hp=enemy.max_hp,
            shield=0,
            atk=enemy.effective_stats.attack,
            def_val=enemy.effective_stats.defense,
            spd=enemy.effective_stats.speed,
            crit=int(enemy.effective_stats.crit_chance * 100),
            is_enemy=True,
        )

        # =========================================================================
        # 4. ACTION TICK GAUGES BAR (y = 318 to y = 354, h = 36)
        # =========================================================================
        tick_rect = pygame.Rect(8, 318, surface_w - 16, 36)
        t_bg = pygame.Surface((tick_rect.width, tick_rect.height), pygame.SRCALPHA)
        t_bg.fill((18, 15, 24, 240))
        surface.blit(t_bg, tick_rect.topleft)

        t_frame = assets.get_9slice_frame("frame_gold_clean", tick_rect.width, tick_rect.height, margin=23)
        if t_frame:
            surface.blit(t_frame, tick_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), tick_rect, width=2, border_radius=4)

        # Label aligned with inner horizontal line at x = 28
        renderer.draw_text(
            surface,
            "Tick Gauges:",
            tick_rect.x + 28,
            tick_rect.y + 10,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # Dual ATB speed bars
        gauge_start_x = tick_rect.x + 160
        gauge_total_w = tick_rect.right - 28 - gauge_start_x
        half_gauge_w = (gauge_total_w - 20) // 2
        bar_h = 14
        bar_y = tick_rect.y + 11

        # Player ATB Gauge (Cyan)
        p_gauge_rect = pygame.Rect(gauge_start_x, bar_y, half_gauge_w, bar_h)
        pygame.draw.rect(surface, (25, 28, 42), p_gauge_rect, border_radius=2)
        p_ratio = min(1.0, max(0.0, combat.player_gauge / ACTION_THRESHOLD))
        if p_ratio > 0:
            pw = max(2, int(half_gauge_w * p_ratio))
            pygame.draw.rect(surface, (41, 173, 255), (p_gauge_rect.x, bar_y, pw, bar_h), border_radius=2)
        pygame.draw.rect(surface, (140, 145, 170), p_gauge_rect, width=1, border_radius=2)

        # Enemy ATB Gauge (Orange)
        e_gauge_rect = pygame.Rect(p_gauge_rect.right + 20, bar_y, half_gauge_w, bar_h)
        pygame.draw.rect(surface, (25, 28, 42), e_gauge_rect, border_radius=2)
        e_ratio = min(1.0, max(0.0, combat.enemy_gauge / ACTION_THRESHOLD))
        if e_ratio > 0:
            ew = max(2, int(half_gauge_w * e_ratio))
            pygame.draw.rect(surface, (255, 120, 20), (e_gauge_rect.x, bar_y, ew, bar_h), border_radius=2)
        pygame.draw.rect(surface, (140, 145, 170), e_gauge_rect, width=1, border_radius=2)

        # =========================================================================
        # 5. SPLIT COMMANDS: BELT ITEMS & ABILITIES (y = 360 to y = 450, h = 90)
        # =========================================================================
        belt_panel_w = 380
        abilities_panel_w = surface_w - 16 - 12 - belt_panel_w
        cmd_h = 90

        # --- LEFT: BELT ITEMS PANEL ---
        b_panel_rect = pygame.Rect(8, 360, belt_panel_w, cmd_h)
        bp_bg = pygame.Surface((b_panel_rect.width, b_panel_rect.height), pygame.SRCALPHA)
        bp_bg.fill((18, 15, 24, 240))
        surface.blit(bp_bg, b_panel_rect.topleft)

        bp_frame = assets.get_9slice_frame("frame_gold_clean", b_panel_rect.width, b_panel_rect.height, margin=23)
        if bp_frame:
            surface.blit(bp_frame, b_panel_rect.topleft)

        renderer.draw_text(
            surface,
            "Belt Items",
            b_panel_rect.x + 24,
            b_panel_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # 3 Single Unstackable Item Slots
        belt = player.inventory.belt
        slot_w, slot_h = 68, 48
        slot_start_x = b_panel_rect.x + 44
        slot_spacing = 96
        slot_y = b_panel_rect.y + 30

        for b_idx in range(MAX_BELT_SLOTS):
            slot_x = slot_start_x + b_idx * slot_spacing
            slot_rect = pygame.Rect(slot_x, slot_y, slot_w, slot_h)
            self.belt_rects[b_idx] = slot_rect

            # Selection cursor '>'
            if b_idx == self.selected_belt_idx:
                renderer.draw_text(
                    surface,
                    ">",
                    slot_rect.x - 14,
                    slot_rect.centery - 8,
                    token=ThemeToken.TEXT_HIGHLIGHT,
                    size=16,
                    bold=True,
                    font_variant="alagard",
                )

            # Slot Frame
            s_box_frame = assets.get_9slice_frame("frame_button_gold", slot_w, slot_h, margin=14)
            if s_box_frame:
                surface.blit(s_box_frame, slot_rect.topleft)
            else:
                pygame.draw.rect(surface, (180, 150, 40), slot_rect, width=1, border_radius=4)

            # Inside Item
            if b_idx < len(belt) and belt[b_idx] is not None:
                item = belt[b_idx]
                item_icon = assets.get_item_icon(item.id, size=(32, 32))
                if not item_icon:
                    item_icon = assets.get_stat_icon("hp", size=(28, 28))

                if item_icon:
                    surface.blit(item_icon, (slot_rect.centerx - item_icon.get_width() // 2, slot_rect.centery - item_icon.get_height() // 2 - 4))

                # Hotkey number [1, 2, 3]
                renderer.draw_text(
                    surface,
                    f"[{b_idx + 1}]",
                    slot_rect.centerx,
                    slot_rect.bottom - 13,
                    token=ThemeToken.TEXT_MUTED,
                    size=10,
                    bold=True,
                    align="center",
                    font_variant="alagard",
                )
            else:
                renderer.draw_text(
                    surface,
                    f"[{b_idx + 1}] Empty",
                    slot_rect.centerx,
                    slot_rect.centery - 6,
                    token=ThemeToken.BORDER_MUTED,
                    size=10,
                    align="center",
                    font_variant="alagard",
                )

        # --- RIGHT: ABILITIES PANEL ---
        ab_panel_rect = pygame.Rect(b_panel_rect.right + 12, 360, abilities_panel_w, cmd_h)
        ab_bg = pygame.Surface((ab_panel_rect.width, ab_panel_rect.height), pygame.SRCALPHA)
        ab_bg.fill((18, 15, 24, 240))
        surface.blit(ab_bg, ab_panel_rect.topleft)

        ab_frame = assets.get_9slice_frame("frame_gold_clean", ab_panel_rect.width, ab_panel_rect.height, margin=23)
        if ab_frame:
            surface.blit(ab_frame, ab_panel_rect.topleft)

        renderer.draw_text(
            surface,
            "Abilities",
            ab_panel_rect.x + 24,
            ab_panel_rect.y + 8,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # 2 Active Abilities with 3 states (CAST, WAIT, CD X)
        active_skills = player.abilities.active
        for a_idx in range(2):
            row_y = ab_panel_rect.y + 32 + a_idx * 26
            row_rect = pygame.Rect(ab_panel_rect.x + 24, row_y, ab_panel_rect.width - 48, 22)
            self.ability_rects[a_idx] = row_rect

            if a_idx < len(active_skills):
                ab = active_skills[a_idx]
                is_queued = (combat.queued_ability == ab)
                rem_cd = combat.get_cooldown(ab)

                # State Tag
                if is_queued:
                    state_tag = "WAIT"
                    state_color = (255, 236, 39)
                elif rem_cd > 0:
                    state_tag = f"CD {rem_cd}"
                    state_color = (160, 165, 180)
                else:
                    state_tag = "CAST"
                    state_color = (41, 173, 255)

                # Row background if queued
                if is_queued:
                    q_bg = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
                    q_bg.fill((45, 55, 110, 160))
                    surface.blit(q_bg, row_rect.topleft)
                    pygame.draw.rect(surface, (120, 160, 255), row_rect, width=1, border_radius=3)

                # Ability Icon / Sword symbol
                icon_surf = assets.get_stat_icon("atk", size=(16, 16)) if a_idx == 0 else assets.get_stat_icon("spd", size=(16, 16))
                if icon_surf:
                    surface.blit(icon_surf, (row_rect.x + 4, row_rect.y + 3))

                # Ability Name e.g. "1. Power Strike" (hotkey [4] or [5])
                hotkey_str = f"{a_idx + 1}. {ab.name}"
                renderer.draw_text(
                    surface,
                    hotkey_str,
                    row_rect.x + 24,
                    row_rect.y + 4,
                    token=ThemeToken.TEXT_HIGHLIGHT if is_queued else ThemeToken.TEXT_NORMAL,
                    size=13,
                    bold=True,
                    font_variant="alagard",
                )

                # Damage / Effect tag
                dmg_val = getattr(ab, "damage_multiplier", 1.0) * player.effective_stats.attack
                cost_tag = f"[ {int(dmg_val)} ATK ]"
                renderer.draw_text(
                    surface,
                    cost_tag,
                    row_rect.right - 90,
                    row_rect.y + 4,
                    token=ThemeToken.TEXT_MUTED,
                    size=12,
                    font_variant="alagard",
                )

                # State Badge on Right
                state_font = renderer.get_font(size=12, bold=True, variant="alagard")
                s_surf = state_font.render(state_tag, True, state_color)
                surface.blit(s_surf, (row_rect.right - s_surf.get_width() - 4, row_rect.y + 4))

            else:
                renderer.draw_text(
                    surface,
                    f"[{a_idx + 4}] (Empty Slot)",
                    row_rect.x + 26,
                    row_rect.y + 4,
                    token=ThemeToken.BORDER_MUTED,
                    size=12,
                    font_variant="alagard",
                )

        # =========================================================================
        # 6. BOTTOM BATTLE LOG PANEL (y = 456 to y = 534, h = 78)
        # =========================================================================
        log_rect = pygame.Rect(8, 456, surface_w - 16, 78)
        l_bg = pygame.Surface((log_rect.width, log_rect.height), pygame.SRCALPHA)
        l_bg.fill((18, 15, 24, 240))
        surface.blit(l_bg, log_rect.topleft)

        l_frame = assets.get_9slice_frame("frame_gold_clean", log_rect.width, log_rect.height, margin=23)
        if l_frame:
            surface.blit(l_frame, log_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), log_rect, width=2, border_radius=4)

        # Header Title
        renderer.draw_text(
            surface,
            "-- Combat Log --",
            log_rect.centerx,
            log_rect.y + 6,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=12,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # Recent 3 log messages with '>' bullets
        recent_logs = combat.combat_logs[-3:] if combat.combat_logs else []
        log_y = log_rect.y + 24
        for idx, line in enumerate(recent_logs):
            is_latest = (idx == len(recent_logs) - 1)
            token = ThemeToken.TEXT_NORMAL if is_latest else ThemeToken.TEXT_MUTED
            renderer.draw_text(
                surface,
                f">  {line}",
                log_rect.x + 28,
                log_y,
                token=token,
                size=12,
                font_variant="alagard",
            )
            log_y += 16

        # Down arrow indicator on bottom-right corner
        arrow_x = log_rect.right - 28
        arrow_y = log_rect.bottom - 16
        pygame.draw.polygon(surface, (255, 215, 0), [(arrow_x, arrow_y), (arrow_x + 8, arrow_y), (arrow_x + 4, arrow_y + 5)])

        # =========================================================================
        # 7. QTE INTERACTIVE MODAL OVERLAY (when active)
        # =========================================================================
        if combat.is_qte_active() and combat.active_qte:
            self._draw_qte(surface, renderer, combat.active_qte)

        # =========================================================================
        # 8. VICTORY NOTIFICATION MODAL
        # =========================================================================
        if self.victory_active:
            self._draw_victory_modal(surface, renderer, session)

        # Restore un-shaked surface if shake was applied
        if orig_surface != surface:
            orig_surface.blit(surface, (ox, oy))

    def _draw_status_window(
        self,
        surface: pygame.Surface,
        renderer: PygameRenderer,
        rect: pygame.Rect,
        avatar_surf: pygame.Surface | None,
        name: str,
        current_hp: int,
        max_hp: int,
        shield: int,
        atk: int,
        def_val: int,
        spd: int,
        crit: int,
        is_enemy: bool,
    ) -> None:
        """Render a symmetrical status card for Player or Enemy."""
        # Dark fill
        card_bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        card_bg.fill((18, 15, 24, 240))
        surface.blit(card_bg, rect.topleft)

        # 9-slice gold frame (clean, margin=23)
        frame = assets.get_9slice_frame("frame_gold_clean", rect.width, rect.height, margin=23)
        if frame:
            surface.blit(frame, rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), rect, width=2, border_radius=4)

        # 1. Avatar Headshot (aligned at rect.x + 24)
        av_rect = pygame.Rect(rect.x + 24, rect.y + 12, 42, 42)
        pygame.draw.rect(surface, (28, 22, 38), av_rect, border_radius=4)
        if avatar_surf:
            surface.blit(avatar_surf, (av_rect.centerx - avatar_surf.get_width() // 2, av_rect.centery - avatar_surf.get_height() // 2))
        pygame.draw.rect(surface, (180, 150, 40), av_rect, width=1, border_radius=4)

        # 2. Name & SPD
        name_x = av_rect.right + 12
        renderer.draw_text(
            surface,
            name,
            name_x,
            rect.y + 10,
            token=ThemeToken.TEXT_ALERT if is_enemy else ThemeToken.TEXT_HIGHLIGHT,
            size=14,
            bold=True,
            font_variant="alagard",
        )

        # SPD on top right
        spd_str = f"SPD {spd}"
        renderer.draw_text(
            surface,
            spd_str,
            rect.right - 28,
            rect.y + 10,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            align="right",
            font_variant="alagard",
        )

        # 3. HP Text & Bar
        hp_y = rect.y + 30
        hp_str = f"HP  {current_hp}/{max_hp}"
        if shield > 0:
            hp_str += f" (+{shield})"
        renderer.draw_text(
            surface,
            hp_str,
            name_x,
            hp_y,
            token=ThemeToken.TEXT_NORMAL,
            size=12,
            bold=True,
            font_variant="alagard",
        )

        # Fixed-aligned HP Bar
        bar_x = name_x + 90
        bar_w = rect.right - 24 - bar_x
        bar_rect = pygame.Rect(bar_x, hp_y + 2, max(40, bar_w), 10)
        pygame.draw.rect(surface, (48, 16, 24), bar_rect, border_radius=2)
        hp_ratio = min(1.0, max(0.0, current_hp / max(1, max_hp)))
        if hp_ratio > 0:
            fill_w = max(2, int(bar_rect.width * hp_ratio))
            bar_color = (255, 60, 90) if is_enemy else (50, 215, 120)
            pygame.draw.rect(surface, bar_color, (bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=2)
        pygame.draw.rect(surface, (150, 155, 175), bar_rect, width=1, border_radius=2)

        # 4. Bottom Numeric Stats: ATK, DEF, CRIT
        stat_y = rect.y + 50
        stat_text = f"ATK {atk}     DEF {def_val}     CRIT {crit}%"
        renderer.draw_text(
            surface,
            stat_text,
            name_x,
            stat_y,
            token=ThemeToken.TEXT_MUTED,
            size=11,
            bold=False,
            font_variant="alagard",
        )

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

    def _draw_victory_modal(self, surface: pygame.Surface, renderer: PygameRenderer, session: GameSession) -> None:
        """Render centered victory notification modal with 9-slice frame, gold typography, and countdown."""
        w, h = surface.get_width(), surface.get_height()
        combat = session.combat
        if not combat:
            return
        enemy = combat.enemy

        # 1. Dark semi-transparent dim backdrop across entire screen
        backdrop = pygame.Surface((w, h), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 140))
        surface.blit(backdrop, (0, 0))

        # 2. Modal dimensions and placement
        modal_w, modal_h = 440, 160
        modal_rect = pygame.Rect((w - modal_w) // 2, (h - modal_h) // 2, modal_w, modal_h)

        # Modal solid dark gothic interior
        modal_bg = pygame.Surface((modal_rect.width, modal_rect.height), pygame.SRCALPHA)
        modal_bg.fill((16, 12, 24, 250))
        surface.blit(modal_bg, modal_rect.topleft)

        # Modal gold ornate frame
        modal_frame = assets.get_9slice_frame(
            "frame_gold_ornate_hollow",
            modal_rect.width,
            modal_rect.height,
            margin=48,
            draw_center=False,
            edge_margin=22,
        )
        if modal_frame:
            surface.blit(modal_frame, modal_rect.topleft)
        else:
            pygame.draw.rect(surface, (218, 165, 32), modal_rect, width=2, border_radius=6)

        # 3. Text & Info
        # Golden Victory Header
        renderer.draw_text(
            surface,
            "VICTORY!",
            modal_rect.centerx,
            modal_rect.y + 22,
            token=ThemeToken.TEXT_HIGHLIGHT,
            size=22,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # Enemy vanquished subtitle
        enemy_name = enemy.name if enemy else "Enemy"
        renderer.draw_text(
            surface,
            f"{enemy_name} vanquished!",
            modal_rect.centerx,
            modal_rect.y + 58,
            token=ThemeToken.TEXT_NORMAL,
            size=15,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # Spoils preview (Exp and Gold)
        exp = getattr(enemy, "exp_reward", 0)
        gold = getattr(enemy, "gold_reward", 0)
        spoils_txt = f"+{exp} EXP      +{gold} GOLD"
        renderer.draw_text(
            surface,
            spoils_txt,
            modal_rect.centerx,
            modal_rect.y + 86,
            token=ThemeToken.ACCENT_PRIMARY,
            size=13,
            bold=True,
            align="center",
            font_variant="alagard",
        )

        # Countdown to map progression
        sec = max(1, int(math.ceil(self.victory_timer)))
        renderer.draw_text(
            surface,
            f"Continuing to map in {sec}s...",
            modal_rect.centerx,
            modal_rect.y + 118,
            token=ThemeToken.TEXT_MUTED,
            size=12,
            align="center",
            font_variant="alagard",
        )
