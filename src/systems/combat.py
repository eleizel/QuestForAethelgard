"""Deterministic tick-based auto-battle system."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Final

import pyxel

if TYPE_CHECKING:
    from src.entities.enemy import Enemy
    from src.entities.player import Player

ACTION_THRESHOLD: Final[int] = 100


class CombatResult(Enum):
    """Possible outcomes of an encounter."""

    IN_PROGRESS = auto()
    PLAYER_VICTORY = auto()
    PLAYER_DEFEAT = auto()


class CombatSystem:
    """Simulates tick-based deterministic combat between player and enemy."""

    def __init__(
        self,
        player: Player,
        enemy: Enemy,
        seed: int | None = None,
    ) -> None:
        self.player: Player = player
        self.enemy: Enemy = enemy
        self.rng: random.Random = random.Random(seed)

        # Action gauges (0 to ACTION_THRESHOLD)
        self.player_gauge: int = 0
        self.enemy_gauge: int = 0
        self.queued_ability = None

        self.current_tick: int = 0
        self.result: CombatResult = CombatResult.IN_PROGRESS
        self.combat_logs: list[str] = [
            f"Battle commenced: {player.name} vs {enemy.name}!"
        ]

    def is_active(self) -> bool:
        """Return True if combat is still ongoing."""
        return self.result == CombatResult.IN_PROGRESS

    def step(self) -> CombatResult:
        """Advance the battle simulation by one tick."""
        if not self.is_active():
            return self.result

        self.current_tick += 1

        # Accumulate action gauges based on speed attributes
        player_speed = self.player.effective_stats.speed
        enemy_speed = self.enemy.base_stats.speed

        self.player_gauge += player_speed
        self.enemy_gauge += enemy_speed

        # Check for ready actions (resolve faster actor first if both are ready)
        if self.player_gauge >= ACTION_THRESHOLD and self.player_gauge >= self.enemy_gauge:
            self._execute_player_attack()
            if self.enemy.is_alive and self.enemy_gauge >= ACTION_THRESHOLD:
                self._execute_enemy_attack()
        elif self.enemy_gauge >= ACTION_THRESHOLD:
            self._execute_enemy_attack()
            if self.player.is_alive and self.player_gauge >= ACTION_THRESHOLD:
                self._execute_player_attack()

        # Check win/loss state
        if not self.enemy.is_alive:
            self.result = CombatResult.PLAYER_VICTORY
            self.combat_logs.append(f"{self.enemy.name} was defeated!")
            self._distribute_rewards()
            pyxel.play(0, 4)  # Sound 4: Victory fanfare
        elif not self.player.is_alive:
            self.result = CombatResult.PLAYER_DEFEAT
            self.combat_logs.append(f"{self.player.name} succumbed to injuries...")
            pyxel.play(0, 5)  # Sound 5: Defeat sting

        return self.result

    def _execute_player_attack(self) -> None:
        """Execute a player strike against the enemy, or an ability if queued."""
        self.player_gauge -= ACTION_THRESHOLD

        if self.queued_ability:
            # Execute queued active ability
            log_str, dmg_dealt, is_crit = self.queued_ability.execute(self)
            crit_str = " (CRITICAL HIT!)" if is_crit else ""
            self.combat_logs.append(f"[Tick {self.current_tick}] {log_str}")
            pyxel.play(0, 1 if is_crit else 0) # Base sound
            self.queued_ability = None
        else:
            raw_dmg, is_crit = self.player.calculate_attack(self.rng)
            crit_str = " (CRITICAL HIT!)" if is_crit else ""
            dmg_dealt = self.enemy.take_damage(raw_dmg)
            self.combat_logs.append(
                f"[Tick {self.current_tick}] {self.player.name} attacks {self.enemy.name} "
                f"for {dmg_dealt} dmg{crit_str}. ({self.enemy.current_hp}/{self.enemy.max_hp} HP)"
            )
            pyxel.play(0, 1 if is_crit else 0)

        # Triggers passive hooks for attack dealt
        for passive in self.player.abilities.passive:
            passive.on_attack_dealt(self.player, self.enemy, dmg_dealt, is_crit)

        has_veteran = any(a.id == "veterans_instincts" for a in self.player.abilities.passive)
        if has_veteran and is_crit:
            self.player_gauge += 20
            self.combat_logs.append(f"{self.player.name}'s Veteran's Instincts restored 20 gauge!")

    def _execute_enemy_attack(self) -> None:
        """Execute an enemy strike against the player."""
        self.enemy_gauge -= ACTION_THRESHOLD
        raw_dmg, is_crit = self.enemy.calculate_attack(self.rng)
        crit_str = " (CRITICAL HIT!)" if is_crit else ""
        dmg_dealt = self.player.take_damage(raw_dmg)

        # Audio feedback: Sound 1 (Crit) or Sound 0 (Hit)
        pyxel.play(0, 1 if is_crit else 0)

        self.combat_logs.append(
            f"[Tick {self.current_tick}] {self.enemy.name} strikes {self.player.name} "
            f"for {dmg_dealt} dmg{crit_str}. ({self.player.current_hp}/{self.player.max_hp} HP)"
        )

    def _distribute_rewards(self) -> None:
        """Grant spoils of victory to the player."""
        exp = self.enemy.exp_reward
        gold = self.enemy.gold_reward
        self.player.gold += gold
        leveled = self.player.gain_experience(exp, foe_type=self.enemy.name)

        # Cleanup combat state
        self.player.combat_def_buff = 0
        if hasattr(self.player, "undying_will_used"):
            self.player.undying_will_used = False
        self.combat_logs.append(f"Gained {exp} EXP and {gold} Gold.")
        if leveled:
            self.combat_logs.append(f"LEVEL UP! {self.player.name} reached Level {self.player.level}!")

    def resolve_all(self, max_ticks: int = 1000) -> CombatResult:
        """Run the simulation to completion or until maximum ticks reached."""
        while self.is_active() and self.current_tick < max_ticks:
            self.step()
        return self.result