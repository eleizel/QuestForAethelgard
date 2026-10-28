"""Deterministic tick-based auto-battle system."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Final

import pyxel

from src.systems.abilities import Ability

if TYPE_CHECKING:
    from src.entities.enemy import Enemy
    from src.entities.player import Player
    from src.entities.actor import Actor

ACTION_THRESHOLD: Final[int] = 100


def _t(key: str, **kwargs) -> str:
    from src.core.i18n import t
    return t(key, **kwargs)


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
        self.player._active_stances.clear()
        # Passive hooks may update combat-owned resources such as action gauge.
        self.player.combat_ref = self
        self.rng: random.Random = random.Random(seed)

        # Action gauges (0 to ACTION_THRESHOLD)
        self.player_gauge: int = 0
        self.enemy_gauge: int = 0
        self.queued_ability = None
        self.cooldowns: dict[str, int] = {}
        self.arcane_reservoir_charges = 0
        self._current_player_action_is_basic = False
        self._passives_handled_per_hit = False
        self._last_player_hit_raw_damage = 0
        self._defer_attack_proc_logs = False
        self._deferred_attack_proc_logs: list[str] = []
        self._current_action_affinities: tuple[str, ...] = ()
        self._pact_of_pain_active = False

        self.current_tick: int = 0
        self.result: CombatResult = CombatResult.IN_PROGRESS
        self.combat_logs: list[str] = [
            _t("combat_start", player=player.name, enemy=enemy.name)
        ]

    def is_active(self) -> bool:
        """Return True if combat is still ongoing."""
        return self.result == CombatResult.IN_PROGRESS

    def _process_status_ticks(self, actor: 'Actor') -> None:
        from src.systems.status import StatusTrigger
        active_statuses = list(actor.statuses)
        for s in active_statuses:
            if s.trigger == StatusTrigger.ON_TICK:
                if s.on_tick_hook:
                    log_str, dmg = s.on_tick_hook(self, actor, s)
                    self.combat_logs.append(log_str)

            # Prevent decrementing duration for PRE_ACTION statuses (e.g. Stun) which are measured in turns, not ticks.
            if s.trigger != StatusTrigger.PRE_ACTION:
                s.duration -= 1
                if s.duration <= 0:
                    actor.statuses.remove(s)

    def _can_actor_act(self, actor: 'Actor') -> bool:
        for s in actor.statuses:
            if s.id == "stun":
                self.combat_logs.append(_t("combat_stunned", actor=actor.name))
                s.duration -= 1
                if s.duration <= 0:
                    actor.statuses.remove(s)
                return False
        return True

    def _evaluate_battle_outcome(self) -> bool:
        if not self.enemy.is_alive:
            self.arcane_reservoir_charges = 0
            self.result = CombatResult.PLAYER_VICTORY
            self.combat_logs.append(_t("combat_enemy_defeat", enemy=self.enemy.name))
            self._distribute_rewards()
            pyxel.play(0, 4)  # Sound 4: Victory fanfare
            return True
        elif not self.player.is_alive:
            self.arcane_reservoir_charges = 0
            self.result = CombatResult.PLAYER_DEFEAT
            self.combat_logs.append(_t("combat_player_defeat", player=self.player.name))
            pyxel.play(0, 5)  # Sound 5: Defeat sting
            return True
        return False

    def step(self) -> CombatResult:
        """Advance the battle simulation by one tick."""
        if not self.is_active():
            return self.result

        self.current_tick += 1

        self._process_status_ticks(self.player)
        self._process_status_ticks(self.enemy)
        if self._evaluate_battle_outcome():
            return self.result

        # Accumulate action gauges based on speed attributes
        player_speed = self.player.effective_stats.speed
        enemy_speed = self.enemy.effective_stats.speed

        self.player_gauge += player_speed
        self.enemy_gauge += enemy_speed

        # Check for ready actions (resolve faster actor first if both are ready)
        if self.player_gauge >= ACTION_THRESHOLD and self.player_gauge >= self.enemy_gauge:
            self._execute_player_attack()
            if self.enemy.is_alive and self.enemy_gauge >= ACTION_THRESHOLD:
                self._execute_enemy_attack()
        elif self.enemy_gauge >= ACTION_THRESHOLD:
            self._execute_enemy_attack()
            if self.enemy.is_alive and self.player.is_alive and self.player_gauge >= ACTION_THRESHOLD:
                self._execute_player_attack()

        self._evaluate_battle_outcome()

        return self.result

    def damage_enemy(self, raw_damage: int, defense_penetration: float = 0.0) -> int:
        """Resolve player damage, including vulnerabilities and passives."""
        if self._pact_of_pain_active:
            raw_damage = int(raw_damage * 1.10)
        self._last_player_hit_raw_damage = raw_damage
        vulnerable = next((status for status in self.enemy.statuses if status.id == "vulnerable"), None)
        if vulnerable:
            # Vulnerable statuses created before potency was configurable have potency 0.
            vulnerability = vulnerable.potency if vulnerable.potency > 0 else 30
            raw_damage = int(raw_damage * (1 + vulnerability / 100))

        has_cull_the_weak = any(
            ability.id == "cull_the_weak" for ability in self.player.abilities.passive
        )
        if has_cull_the_weak and self.enemy.current_hp > 0 and self.enemy.current_hp <= self.enemy.max_hp * 0.30:
            raw_damage = int(raw_damage * 1.30)

        # Defensive Superiority converts the player's relative DEF advantage into
        # penetration. It does nothing when the enemy has equal or higher DEF.
        has_defensive_superiority = any(
            ability.id == "defensive_superiority" for ability in self.player.abilities.passive
        )
        if has_defensive_superiority:
            enemy_defense = max(0, self.enemy.effective_stats.defense)
            player_defense = max(0, self.player.effective_stats.defense)
            if enemy_defense <= 0:
                passive_penetration = 0.75 if player_defense > 0 else 0.0
            else:
                passive_penetration = min(0.75, max(0.0, player_defense / enemy_defense - 1.0))
            # Combine penetrations multiplicatively to avoid adding percentages past 100%.
            defense_penetration = 1.0 - (1.0 - defense_penetration) * (1.0 - passive_penetration)

        # Exposed Weakness empowers exactly the next damaging strike after a critical hit.
        if getattr(self.player, "_next_strike_bonus", False):
            raw_damage = int(raw_damage * 1.25)
            self.player._next_strike_bonus = False

        return self.enemy.take_damage(raw_damage, defense_penetration=defense_penetration)

    def log_attack_proc(self, message: str) -> None:
        """Append proc logs after the parent ability log when its hits are resolved first."""
        if self._defer_attack_proc_logs:
            self._deferred_attack_proc_logs.append(message)
        else:
            self.combat_logs.append(message)

    def trigger_player_attack_passives(
        self,
        damage: int,
        is_crit: bool,
        *,
        is_basic_attack: bool,
        skip_ids: set[str] | None = None,
        only_ids: set[str] | None = None,
    ) -> None:
        """Run passive attack hooks for one damaging hit or a cast-level event."""
        if damage <= 0:
            return
        skip_ids = skip_ids or set()
        for passive in self.player.abilities.passive:
            if passive.id in skip_ids or (only_ids is not None and passive.id not in only_ids):
                continue
            if passive.id == "soulfire" and not is_basic_attack:
                continue
            passive.on_attack_dealt(self.player, self.enemy, damage, is_crit)

    def _execute_player_attack(self) -> None:
        """Execute a player strike against the enemy, or an ability if queued."""
        self.player_gauge -= ACTION_THRESHOLD
        if not self._can_actor_act(self.player):
            return

        self._passives_handled_per_hit = False
        is_basic_attack = self.queued_ability is None
        self._current_player_action_is_basic = is_basic_attack
        whirlwind_ready = is_basic_attack and self.player.consume_stance("whirlwind_defense")

        # Reckless Assault's vulnerability lasts until this next player action.
        self.player._reckless_assault_vulnerable = False

        # Decrement all independent cooldowns by 1 on player action
        for ab_id in list(self.cooldowns.keys()):
            if self.cooldowns[ab_id] > 0:
                self.cooldowns[ab_id] -= 1
                if self.cooldowns[ab_id] <= 0:
                    del self.cooldowns[ab_id]

        if self.queued_ability:
            # Set this specific ability's cooldown
            if self.queued_ability.cooldown > 0:
                self.cooldowns[self.queued_ability.id] = self.queued_ability.cooldown

            # Track the affinity of the last active skill used. Basic attacks do not clear it.
            self.player._last_ability_affinities = tuple(getattr(self.queued_ability, "affinities", ()))
            self._current_action_affinities = self.player._last_ability_affinities
            self._pact_of_pain_active = (
                "warlock" in self._current_action_affinities
                and any(ability.id == "pact_of_pain" for ability in self.player.abilities.passive)
            )
            if self._pact_of_pain_active:
                cost = max(1, int(self.player.max_hp * 0.05))
                paid = min(cost, max(0, self.player.current_hp - 1))
                self.player.current_hp -= paid
                if paid:
                    self.combat_logs.append(
                        _t("combat_pact_of_pain", actor=self.player.name, cost=paid)
                    )

            # Arcane Missiles resolves its per-hit passives before returning its summary log.
            self._deferred_attack_proc_logs.clear()
            self._defer_attack_proc_logs = self.queued_ability.id == "arcane_missiles"
            log_str, dmg_dealt, is_crit = self.queued_ability.execute(self)
            self._defer_attack_proc_logs = False
            self.combat_logs.append(f"[Tick {self.current_tick}] {log_str}")
            self.combat_logs.extend(self._deferred_attack_proc_logs)
            self._deferred_attack_proc_logs.clear()
            pyxel.play(0, 1 if is_crit else 0)
            self.queued_ability = None
        else:
            if self.player.has_status("blind") and self.rng.random() < 0.50:
                self.combat_logs.append(_t("combat_blind_miss", actor=self.player.name))
                dmg_dealt = 0
                is_crit = False
            else:
                raw_dmg, is_crit = self.player.calculate_attack(self.rng)
                dmg_dealt = self.damage_enemy(raw_dmg)
                if is_crit:
                    self.combat_logs.append(
                        _t("combat_crit", actor=self.player.name, target=self.enemy.name, damage=dmg_dealt))
                else:
                    self.combat_logs.append(
                        _t("combat_hit", actor=self.player.name, target=self.enemy.name, damage=dmg_dealt))
                pyxel.play(0, 1 if is_crit else 0)

                # Check on_hit_status for player weapons
                weapon = self.player.inventory.get_equipment_in_slot("Main Hand")
                if weapon and getattr(weapon, "on_hit_status", None) and self.rng.random() < getattr(weapon,
                                                                                                     "on_hit_chance",
                                                                                                     0.0):
                    from src.systems.status import get_status_by_id
                    effect = get_status_by_id(weapon.on_hit_status)
                    if effect:
                        self.enemy.apply_status(effect)
                        self.combat_logs.append(
                            _t("combat_status_applied", target=self.enemy.name, effect=effect.localized_name))

                # Summon Imp adds an independent strike to each successful basic attack.
                if dmg_dealt > 0 and self.enemy.is_alive and any(
                    ability.id == "summon_imp" for ability in self.player.abilities.passive
                ):
                    imp_crit = self.rng.random() < self.player.effective_stats.crit_chance
                    imp_raw = int(self.player.effective_stats.attack * 0.50)
                    if imp_crit:
                        imp_raw = int(imp_raw * 1.5)
                    imp_damage = self.damage_enemy(imp_raw)
                    dmg_dealt += imp_damage
                    is_crit = is_crit or imp_crit

                    burned = False
                    if self.enemy.is_alive and self.rng.random() < 0.50:
                        from src.systems.status import get_status_by_id
                        burn = get_status_by_id("burn", duration=8, potency=1)
                        if burn:
                            self.enemy.apply_status(burn)
                            burned = True

                    log_key = "combat_summon_imp_crit" if imp_crit else "combat_summon_imp_hit"
                    self.combat_logs.append(
                        _t(log_key, actor=self.player.name, target=self.enemy.name, damage=imp_damage)
                    )
                    if burned:
                        self.combat_logs.append(
                            _t("combat_summon_imp_burn", target=self.enemy.name)
                        )

        if whirlwind_ready and dmg_dealt > 0 and self.enemy.is_alive:
            extra_crit = self.rng.random() < self.player.effective_stats.crit_chance
            extra_raw = int(self.player.effective_stats.attack * 0.25)
            if extra_crit:
                extra_raw = int(extra_raw * 1.5)
            extra_damage = self.damage_enemy(extra_raw)
            dmg_dealt += extra_damage
            is_crit = is_crit or extra_crit
            log_key = "combat_whirlwind_crit" if extra_crit else "combat_whirlwind_hit"
            self.combat_logs.append(_t(log_key, actor=self.player.name, target=self.enemy.name, damage=extra_damage))

        # Trigger passive hooks for attack dealt. Soulfire is deliberately
        # restricted to basic attacks; other passives may still react to abilities.
        if dmg_dealt > 0 and not self._passives_handled_per_hit:
            self.trigger_player_attack_passives(
                dmg_dealt, is_crit, is_basic_attack=is_basic_attack
            )
        self._passives_handled_per_hit = False
        self._current_player_action_is_basic = False
        self._current_action_affinities = ()
        self._pact_of_pain_active = False

        if self.player.abilities.has_veterans_instincts and is_crit:
            self.player_gauge = min(100, self.player_gauge + 20)
            self.combat_logs.append(_t("combat_veteran", player=self.player.name))

    def _execute_enemy_attack(self) -> None:
        """Execute an enemy strike against the player."""
        self.enemy_gauge -= ACTION_THRESHOLD
        if not self._can_actor_act(self.enemy):
            return

        if self.enemy.has_status("blind") and self.rng.random() < 0.50:
            self.combat_logs.append(_t("combat_blind_miss", actor=self.enemy.name))
            return

        if any(ability.id == "riposte" for ability in self.player.abilities.passive):
            if self.rng.random() < 0.25:
                self.player.activate_stance("riposte")
                self.combat_logs.append(_t("combat_riposte_block", actor=self.player.name))
                return

        raw_dmg, is_crit = self.enemy.calculate_attack(self.rng)
        vulnerable = next((status for status in self.player.statuses if status.id == "vulnerable"), None)
        if vulnerable:
            # Preserve the legacy 30% Vulnerable effect when no potency is supplied.
            vulnerability = vulnerable.potency if vulnerable.potency > 0 else 30
            raw_dmg = int(raw_dmg * (1 + vulnerability / 100))
        dmg_dealt = self.player.take_damage(raw_dmg)

        # Audio feedback: Sound 1 (Crit) or Sound 0 (Hit)
        pyxel.play(0, 1 if is_crit else 0)

        if is_crit:
            self.combat_logs.append(_t("combat_crit", actor=self.enemy.name, target=self.player.name, damage=dmg_dealt))
        else:
            self.combat_logs.append(_t("combat_hit", actor=self.enemy.name, target=self.player.name, damage=dmg_dealt))

        if dmg_dealt > 0 and self.enemy.is_alive and any(
                ability.id == "ice_shards" for ability in self.player.abilities.passive):
            reflected_raw = int(dmg_dealt * 0.10)
            if reflected_raw > 0:
                reflected = self.enemy.take_damage(reflected_raw)
                if reflected > 0:
                    self.combat_logs.append(
                        _t("combat_ice_shards_reflect", actor=self.player.name,
                           target=self.enemy.name, damage=reflected))

        if getattr(self.enemy, "on_hit_status", None) and self.rng.random() < getattr(self.enemy, "status_chance", 0.0):
            from src.systems.status import get_status_by_id
            effect = get_status_by_id(self.enemy.on_hit_status)
            if effect:
                self.player.apply_status(effect)
                self.combat_logs.append(
                    _t("combat_status_applied", target=self.player.name, effect=effect.localized_name))

        if dmg_dealt > 0:
            chest = self.player.inventory.get_equipment_in_slot("Chest")
            if chest and chest.id == "spiked_carapace":
                from src.systems.status import get_status_by_id
                effect = get_status_by_id("bleed")
                if effect:
                    self.enemy.apply_status(effect)
                    self.combat_logs.append(
                        _t("combat_status_applied", target=self.enemy.name, effect=effect.localized_name))

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
        self.combat_logs.append(_t("combat_rewards", exp=exp, gold=gold))
        if leveled:
            self.combat_logs.append(_t("combat_level_up", player=self.player.name, level=self.player.level))

    def resolve_all(self, max_ticks: int = 1000) -> CombatResult:
        """Run the simulation to completion or until maximum ticks reached."""
        while self.is_active() and self.current_tick < max_ticks:
            self.step()
        return self.result

    def get_cooldown(self, ability: Ability) -> int:
        """Return remaining cooldown turns for a given ability."""
        return self.cooldowns.get(ability.id, 0)

    def is_ability_ready(self, ability: Ability) -> bool:
        """Check if an ability can be queued."""
        return self.get_cooldown(ability) <= 0
