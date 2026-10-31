"""Deterministic tick-based auto-battle system."""

from __future__ import annotations

import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Final

import pyxel

from src.core.audio import audio
from src.config import SND_HIT, SND_CRIT, SND_VICTORY, SND_DEFEAT, SND_HEAL
from src.systems.abilities import Ability
from src.data.enemies import ENEMY_SKILLS, EnemySkill

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
        # Keep cosmetic bark selection from shifting the combat RNG stream.
        self.dialogue_rng: random.Random = random.Random(seed + 1 if seed is not None else None)

        # Action gauges (0 to ACTION_THRESHOLD)
        self.player_gauge: int = 0
        self.enemy_gauge: int = 0
        self.queued_ability = None
        self.cooldowns: dict[str, int] = {}
        self.arcane_reservoir_charges = 0
        self.arcane_momentum_stacks = 0
        self.signature_proc_counts: dict[str, int] = {}
        self.venom_poison_ticks = 0
        self._warlock_last_enemy_action = -1
        self.berserker_threshold_triggered = False
        self.berserker_bonus_ready = False
        self._berserker_bonus_damage_active = False

        self.duelist_flourish_armed = False
        self._current_player_action_is_basic = False
        self._passives_handled_per_hit = False
        self._last_player_hit_raw_damage = 0
        self._defer_attack_proc_logs = False
        self._deferred_attack_proc_logs: list[str] = []
        self._current_action_affinities: tuple[str, ...] = ()
        self._pact_of_pain_active = False

        # Enemy actions use their own cooldown clock (one decrement per enemy action).
        self.enemy_skill_cooldowns: dict[str, int] = {}
        self.enemy_actions_taken = 0
        self.enemy_speech_bubble: str | None = None
        self.enemy_speech_actions_remaining = 0
        self.pending_enemy_signature: EnemySkill | None = None
        self._enemy_half_phase_triggered = False
        self._enemy_quarter_hook_triggered = False
        self._enemy_death_hook_triggered = False
        self.completion_delay_ticks = 0

        self.current_tick: int = 0
        self.result: CombatResult = CombatResult.IN_PROGRESS
        self.combat_logs: list[str] = [
            _t("combat_start", player=player.name, enemy=enemy.name)
        ]
        if (
            self._has_signature("berserker_rage")
            and self.player.current_hp <= self.player.max_hp * 0.50
        ):
            self.berserker_threshold_triggered = True
            self.berserker_bonus_ready = True
            self.player_gauge = max(self.player_gauge, ACTION_THRESHOLD)
            self._record_signature_proc("berserker_rage")
            self.combat_logs.append(_t("combat_deathless_onslaught_ready", actor=self.player.name))

        if self._has_signature("archmage_focus"):
            self.player.shield = int(self.player.max_hp * 0.20)
            self._record_signature_proc("archmage_focus")
            self.combat_logs.append(
                _t("combat_archmage_barrier_active", actor=self.player.name, shield=self.player.shield)
            )
        else:
            self.player.shield = 0

    def is_active(self) -> bool:
        """Return True if combat is still ongoing."""
        return self.result == CombatResult.IN_PROGRESS

    def _has_signature(self, signature_id: str) -> bool:
        return any(ability.id == signature_id for ability in self.player.all_passives)

    def _record_signature_proc(self, signature_id: str, count: int = 1) -> None:
        self.signature_proc_counts[signature_id] = self.signature_proc_counts.get(signature_id, 0) + count

    def on_player_stance_consumed(self, stance_id: str) -> None:
        if self._has_signature("duelist_precision"):
            self.duelist_flourish_armed = True
            self._record_signature_proc("duelist_precision")

    def on_player_damaged(self, previous_hp: int, actual_damage: int) -> None:
        if actual_damage <= 0:
            return
        if (
            self._has_signature("berserker_rage")
            and not self.berserker_threshold_triggered
            and self.player.is_alive
            and self.player.current_hp <= self.player.max_hp * 0.50
        ):
            self.berserker_threshold_triggered = True
            self.berserker_bonus_ready = True
            self.player_gauge = max(self.player_gauge, ACTION_THRESHOLD)
            self._record_signature_proc("berserker_rage")
            self.combat_logs.append(_t("combat_deathless_onslaught_ready", actor=self.player.name))

        if (
            self._has_signature("warlock_pact")
            and self.enemy.is_alive
            and self._warlock_last_enemy_action != self.enemy_actions_taken
        ):
            from src.systems.status import get_status_by_id

            burn = get_status_by_id("burn", duration=8, potency=1)
            if burn:
                self.enemy.apply_status(burn)
                self._warlock_last_enemy_action = self.enemy_actions_taken
                self._record_signature_proc("warlock_pact")
                self.combat_logs.append(
                    _t("combat_daemonic_pact_burn", target=self.enemy.name)
                )

    def _process_status_ticks(self, actor: 'Actor') -> None:
        from src.systems.status import StatusTrigger
        active_statuses = list(actor.statuses)
        for s in active_statuses:
            if s.trigger == StatusTrigger.ON_TICK:
                if s.on_tick_hook:
                    previous_hp = actor.current_hp
                    burn_early_stacks = 0
                    burn_early_damage = 0
                    if s.id == "burn" and actor is self.enemy and self._has_signature("warlock_pact"):
                        if len(s.stack_tick_counts) < s.stacks:
                            s.stack_tick_counts.extend([0] * (s.stacks - len(s.stack_tick_counts)))
                        burn_damage_per_stack = max(1, actor.max_hp * s.potency // 100)
                        burn_early_damage = sum(
                            min(
                                burn_damage_per_stack,
                                max(0, actor.current_hp - index * burn_damage_per_stack),
                            )
                            for index, ticks in enumerate(s.stack_tick_counts[:s.stacks])
                            if ticks < 2
                        )
                    log_str, dmg = s.on_tick_hook(self, actor, s)
                    self.combat_logs.append(log_str)
                    if s.id == "burn":
                        if len(s.stack_tick_counts) < s.stacks:
                            s.stack_tick_counts.extend([0] * (s.stacks - len(s.stack_tick_counts)))
                        for index in range(s.stacks):
                            s.stack_tick_counts[index] += 1
                        if burn_early_stacks and dmg > 0:
                            healed = self.player.heal(min(dmg, burn_early_damage) // 2)
                            if healed:
                                self.combat_logs.append(
                                    _t("combat_daemonic_pact_heal", actor=self.player.name, heal=healed)
                                )
                                self._record_signature_proc("warlock_pact")
                    if s.id == "poison" and actor is self.enemy and self._has_signature("venomancer_mastery"):
                        self.venom_poison_ticks += 1
                        if self.venom_poison_ticks % 4 == 0 and dmg > 0 and actor.is_alive:
                            detonation = min(actor.current_hp, max(0, dmg * 2))
                            actor.current_hp -= detonation
                            dmg += detonation
                            self.combat_logs.append(
                                _t("combat_perfect_toxin", target=actor.name, damage=detonation)
                            )
                            self._record_signature_proc("venomancer_mastery")
                    if actor is self.enemy and actor.current_hp < previous_hp:
                        self._check_enemy_threshold_hooks(previous_hp, actor.current_hp)

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
            self._trigger_enemy_death_hook()
            self.arcane_reservoir_charges = 0
            self.player.shield = 0
            if not self.player.is_alive:
                self.result = CombatResult.PLAYER_DEFEAT
                self.combat_logs.append(_t("combat_player_defeat", player=self.player.name))
                audio.play_sfx(SND_DEFEAT)
            else:
                self.result = CombatResult.PLAYER_VICTORY
                self.combat_logs.append(_t("combat_enemy_defeat", enemy=self.enemy.name))
                self._distribute_rewards()
                audio.play_sfx(SND_VICTORY)  # Sound 4: Victory fanfare
            return True
        elif not self.player.is_alive:
            self.arcane_reservoir_charges = 0
            self.player.shield = 0
            self.result = CombatResult.PLAYER_DEFEAT
            self.combat_logs.append(_t("combat_player_defeat", player=self.player.name))
            audio.play_sfx(SND_DEFEAT)  # Sound 5: Defeat sting
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
        if self._has_signature("archmage_focus"):
            raw_damage = int(raw_damage * (1 + 0.10 * self.arcane_momentum_stacks))
        if self._berserker_bonus_damage_active:
            raw_damage *= 2
        self._last_player_hit_raw_damage = raw_damage
        vulnerable = next((status for status in self.enemy.statuses if status.id == "vulnerable"), None)
        if vulnerable:
            # Vulnerable statuses created before potency was configurable have potency 0.
            vulnerability = vulnerable.potency if vulnerable.potency > 0 else 30
            raw_damage = int(raw_damage * (1 + vulnerability / 100))

        has_cull_the_weak = any(
            ability.id == "cull_the_weak" for ability in self.player.all_passives
        )
        if has_cull_the_weak and self.enemy.current_hp > 0 and self.enemy.current_hp <= self.enemy.max_hp * 0.30:
            raw_damage = int(raw_damage * 1.30)

        # Defensive Superiority converts the player's relative DEF advantage into
        # penetration. It does nothing when the enemy has equal or higher DEF.
        has_defensive_superiority = any(
            ability.id == "defensive_superiority" for ability in self.player.all_passives
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

        if self._has_signature("archmage_focus"):
            # The signature adds 25% armor penetration to every direct hit.
            defense_penetration = 1 - (1 - defense_penetration) * 0.75

        previous_hp = self.enemy.current_hp
        actual_damage = self.enemy.take_damage(raw_damage, defense_penetration=defense_penetration)
        if actual_damage > 0:
            self._check_enemy_threshold_hooks(previous_hp, self.enemy.current_hp)
        return actual_damage

    def _show_enemy_speech(self, dialogue_key: str | None, actions: int) -> None:
        if dialogue_key:
            from src.core.i18n import t_choice

            self.enemy_speech_bubble = t_choice(dialogue_key, self.dialogue_rng)
        else:
            self.enemy_speech_bubble = None
        self.enemy_speech_actions_remaining = max(0, actions)

    def _check_enemy_threshold_hooks(self, previous_hp: int, current_hp: int) -> None:
        """Fire threshold hooks once, in descending HP order when a hit skips a phase."""
        from src.entities.enemy import EnemyTier

        if self.enemy.tier not in (EnemyTier.ELITE, EnemyTier.BOSS):
            return
        hooks = (
            (self.enemy.half_hp_hook, 0.50, "half"),
            (self.enemy.quarter_hp_hook, 0.25, "quarter"),
        )
        for hook, fallback_threshold, hook_name in hooks:
            if hook_name == "half" and self._enemy_half_phase_triggered:
                continue
            if hook_name == "quarter" and (self.enemy.tier != EnemyTier.BOSS or self._enemy_quarter_hook_triggered):
                continue
            threshold = hook.threshold if hook.threshold is not None else fallback_threshold
            if previous_hp > self.enemy.max_hp * threshold >= current_hp:
                if hook_name == "half":
                    self._enemy_half_phase_triggered = True
                    self._apply_enemy_half_phase()
                else:
                    self._enemy_quarter_hook_triggered = True
                    self.pending_enemy_signature = ENEMY_SKILLS.get(hook.skill_id or "signature_attack")
                self._show_enemy_speech(hook.dialogue_key, hook.dialogue_actions)

    def _apply_enemy_half_phase(self) -> None:
        """Apply the archetype's configured phase tradeoff at half health."""
        if self.enemy.phase_style == "haste_bleed":
            from src.systems.status import get_status_by_id

            haste = get_status_by_id("haste", duration=10, potency=4)
            bleed = get_status_by_id("bleed", duration=10, potency=2)
            if haste:
                self.enemy.apply_status(haste)
            if bleed:
                self.enemy.apply_status(bleed)
        else:
            self.enemy.base_stats.attack = max(1, int(self.enemy.base_stats.attack * 1.20))
            self.enemy.base_stats.defense = max(0, self.enemy.base_stats.defense - 2)

    def _trigger_enemy_death_hook(self) -> None:
        """Resolve a common/uncommon concept death effect exactly once."""
        from src.entities.enemy import EnemyTier
        from src.systems.status import get_status_by_id

        if self._enemy_death_hook_triggered:
            return
        self._enemy_death_hook_triggered = True
        self.enemy_speech_bubble = None
        self.enemy_speech_actions_remaining = 0
        self.pending_enemy_signature = None
        if self.enemy.tier not in (EnemyTier.COMMON, EnemyTier.UNCOMMON):
            return

        hook = self.enemy.on_death_hook
        status_id = hook.status_id or (self.enemy.on_hit_status if hook.effect == "concept_death" else None)
        if hook.effect in ("concept_death", "status") and status_id:
            effect = get_status_by_id(status_id)
            if effect:
                self.player.apply_status(effect)
                self._show_enemy_speech(hook.dialogue_key, 0)
                self.completion_delay_ticks = 3
                return

        if hook.effect in ("concept_death", "damage"):
            damage = max(1, int(self.player.max_hp * hook.damage_fraction))
            actual = min(self.player.current_hp, damage)
            self.player.current_hp -= actual  # Death bursts bypass defense.
            self._show_enemy_speech(hook.dialogue_key, 0)
            self.completion_delay_ticks = 3

    def _choose_enemy_skill(self) -> EnemySkill | None:
        available = [
            skill for skill in self.enemy.skills
            if self.enemy_skill_cooldowns.get(skill.id, 0) <= 0
        ]
        heal = next((skill for skill in available if skill.kind == "heal"), None)
        if heal and self.enemy.current_hp <= self.enemy.max_hp * 0.70:
            return heal
        return next((skill for skill in available if skill.kind != "heal"), None)

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
        for passive in self.player.all_passives:
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
        duelist_flourish_ready = is_basic_attack and self.duelist_flourish_armed
        if duelist_flourish_ready:
            # Reserve the armed flourish for this action; stance consumption during
            # this same action can then arm a fresh flourish for the following attack.
            self.duelist_flourish_armed = False
        berserker_bonus_this_action = self.berserker_bonus_ready
        self._berserker_bonus_damage_active = berserker_bonus_this_action
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
                and any(ability.id == "pact_of_pain" for ability in self.player.all_passives)
            )
            if (
                self._has_signature("archmage_focus")
                and any(affinity in ("archmage", "hybrid") for affinity in self._current_action_affinities)
            ):
                self.arcane_momentum_stacks = min(5, self.arcane_momentum_stacks + 1)
                self._record_signature_proc("archmage_focus")
                self.combat_logs.append(
                    _t("combat_arcane_momentum", actor=self.player.name, stacks=self.arcane_momentum_stacks)
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
            audio.play_sfx(SND_CRIT if is_crit else SND_HIT)
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
                audio.play_sfx(SND_CRIT if is_crit else SND_HIT)

                # Check on_hit_status for player weapons
                weapon = self.player.inventory.get_equipment_in_slot("Main Hand")
                if weapon and getattr(weapon, "on_hit_status", None) and self.rng.random() < getattr(weapon,
                                                                                                     "on_hit_chance",
                                                                                                     0.0):
                    from src.systems.status import get_status_by_id
                    status_options = {}
                    if (
                        weapon.on_hit_status == "poison"
                        and any(
                            passive.id == "venomous_accumulation"
                            for passive in self.player.all_passives
                        )
                    ):
                        status_options["max_stacks"] = 3
                    effect = get_status_by_id(weapon.on_hit_status, **status_options)
                    if effect:
                        self.enemy.apply_status(effect)
                        self.combat_logs.append(
                            _t("combat_status_applied", target=self.enemy.name, effect=effect.localized_name))

                if (
                    dmg_dealt > 0
                    and (
                        self._has_signature("paladin_oath")
                        or duelist_flourish_ready
                    )
                ):
                    # Resolve attack passives per hit when a signature adds hits, so
                    # status procs can occur on each strike without double-firing later.
                    self.trigger_player_attack_passives(
                        dmg_dealt,
                        is_crit,
                        is_basic_attack=True,
                    )
                    self._passives_handled_per_hit = True

                if dmg_dealt > 0 and self.enemy.is_alive and self._has_signature("paladin_oath"):
                    extra_damage, extra_crit = self._signature_bonus_hit(0.50, "paladin_oath")
                    dmg_dealt += extra_damage
                    is_crit = is_crit or extra_crit

                # Summon Imp adds an independent strike to each successful basic attack.
                if dmg_dealt > 0 and self.enemy.is_alive and any(
                    ability.id == "summon_imp" for ability in self.player.all_passives
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

        if duelist_flourish_ready and dmg_dealt > 0:
            # The extra strikes apply weapon on-hit effects but do not trigger stances.
            self._record_signature_proc("duelist_precision")
            for _ in range(2):
                if not self.enemy.is_alive:
                    break
                extra_damage, extra_crit = self._signature_bonus_hit(0.50, "duelist_precision")
                dmg_dealt += extra_damage
                is_crit = is_crit or extra_crit
        elif duelist_flourish_ready:
            # A miss does not spend the stored flourish.
            self.duelist_flourish_armed = True

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
        self._berserker_bonus_damage_active = False
        if berserker_bonus_this_action and dmg_dealt > 0:
            self.berserker_bonus_ready = False
            heal_cap = int(self.player.max_hp * 0.30)
            healed = self.player.heal(min(dmg_dealt // 2, heal_cap))
            if healed:
                self.combat_logs.append(_t("combat_deathless_onslaught_heal", actor=self.player.name, heal=healed))

        if self.player.abilities.has_veterans_instincts and is_crit:
            self.player_gauge = min(100, self.player_gauge + 20)
            self.combat_logs.append(_t("combat_veteran", player=self.player.name))

    def _signature_bonus_hit(self, multiplier: float, signature_id: str) -> tuple[int, bool]:
        """Resolve an independent signature hit with crit and weapon on-hit behavior."""
        raw_damage = int(self.player.effective_stats.attack * multiplier)
        is_crit = self.rng.random() < self.player.effective_stats.crit_chance
        if is_crit:
            raw_damage = int(raw_damage * 1.5)
        damage = self.damage_enemy(raw_damage)
        if damage > 0:
            # Preserve ordinary on-hit effects for each bonus strike, while suppressing
            # the critical-hit stance trigger so a flourish cannot recursively arm itself.
            self.trigger_player_attack_passives(
                damage,
                is_crit,
                is_basic_attack=True,
                skip_ids={"whirlwind_defense"} if signature_id == "duelist_precision" else set(),
            )
            weapon = self.player.inventory.get_equipment_in_slot("Main Hand")
            if weapon and getattr(weapon, "on_hit_status", None) and self.rng.random() < getattr(weapon, "on_hit_chance", 0.0):
                from src.systems.status import get_status_by_id

                effect = get_status_by_id(weapon.on_hit_status)
                if effect:
                    self.enemy.apply_status(effect)
                    self.combat_logs.append(
                        _t("combat_status_applied", target=self.enemy.name, effect=effect.localized_name)
                    )
            if signature_id == "paladin_oath":
                self.player.heal(max(1, damage // 4))
            self._record_signature_proc(signature_id)
        log_key = "combat_signature_hit_crit" if is_crit else "combat_signature_hit"
        self.combat_logs.append(
            _t(log_key, actor=self.player.name, target=self.enemy.name, damage=damage)
        )
        return damage, is_crit

    def _execute_enemy_attack(self) -> None:
        """Resolve one enemy action, skill, or telegraphed signature move."""
        self.enemy_gauge -= ACTION_THRESHOLD
        self.enemy_actions_taken += 1
        for skill_id in list(self.enemy_skill_cooldowns):
            self.enemy_skill_cooldowns[skill_id] -= 1
            if self.enemy_skill_cooldowns[skill_id] <= 0:
                del self.enemy_skill_cooldowns[skill_id]
        if not self._can_actor_act(self.enemy):
            return

        skill = self.pending_enemy_signature
        if skill is not None:
            self.enemy_speech_actions_remaining -= 1
            if self.enemy_speech_actions_remaining <= 0:
                # The warning bubble disappears as the signature move begins.
                self.enemy_speech_bubble = None
                self.pending_enemy_signature = None
            else:
                skill = None
                return
        elif self.enemy_speech_bubble:
            self.enemy_speech_actions_remaining -= 1
            if self.enemy_speech_actions_remaining <= 0:
                self.enemy_speech_bubble = None

        if self.enemy.has_status("blind") and self.rng.random() < 0.50:
            self.combat_logs.append(_t("combat_blind_miss", actor=self.enemy.name))
            return

        if any(ability.id == "riposte" for ability in self.player.all_passives):
            if self.rng.random() < 0.25:
                self.player.activate_stance("riposte")
                self.combat_logs.append(_t("combat_riposte_block", actor=self.player.name))
                return

        if skill is None:
            skill = self._choose_enemy_skill()

        if skill is not None and skill.kind == "heal":
            amount = max(1, int(self.enemy.max_hp * skill.heal_fraction))
            healed = self.enemy.heal(amount)
            # This action has already advanced the enemy action clock. Add one
            # so a cooldown of N means N complete enemy actions must pass.
            self.enemy_skill_cooldowns[skill.id] = skill.cooldown + 1
            self.combat_logs.append(
                _t("combat_enemy_skill_heal", enemy=self.enemy.name, healed=healed)
            )
            audio.play_sfx(SND_HEAL)
            return

        if skill is not None and skill.kind == "status":
            from src.systems.status import get_status_by_id

            effect = get_status_by_id(skill.status_id or "stun", duration=skill.status_duration)
            if effect:
                self.player.apply_status(effect)
                self.combat_logs.append(
                    _t("combat_status_applied", target=self.player.name, effect=effect.localized_name)
                )
            self.enemy_skill_cooldowns[skill.id] = skill.cooldown + 1
            return

        if skill is not None:
            self.enemy_skill_cooldowns[skill.id] = skill.cooldown + 1
            self.combat_logs.append(
                _t("combat_enemy_skill_attack", enemy=self.enemy.name,
                   skill=_t(f"enemy_skill_{skill.id}"))
            )

        raw_dmg, is_crit = self.enemy.calculate_attack(self.rng)
        if skill is not None:
            raw_dmg = max(1, int(raw_dmg * skill.damage_multiplier))
        vulnerable = next((status for status in self.player.statuses if status.id == "vulnerable"), None)
        if vulnerable:
            # Preserve the legacy 30% Vulnerable effect when no potency is supplied.
            vulnerability = vulnerable.potency if vulnerable.potency > 0 else 30
            raw_dmg = int(raw_dmg * (1 + vulnerability / 100))
        dmg_dealt = self.player.take_damage(raw_dmg)

        # Audio feedback: Sound 1 (Crit) or Sound 0 (Hit)
        audio.play_sfx(SND_CRIT if is_crit else SND_HIT)

        if is_crit:
            self.combat_logs.append(_t("combat_crit", actor=self.enemy.name, target=self.player.name, damage=dmg_dealt))
        else:
            self.combat_logs.append(_t("combat_hit", actor=self.enemy.name, target=self.player.name, damage=dmg_dealt))

        if dmg_dealt > 0 and self.enemy.is_alive and any(
                ability.id == "ice_shards" for ability in self.player.all_passives):
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

        if skill is not None and skill.status_id and self.player.is_alive:
            from src.systems.status import get_status_by_id

            effect = get_status_by_id(skill.status_id, duration=skill.status_duration)
            if effect:
                self.player.apply_status(effect)
                self.combat_logs.append(
                    _t("combat_status_applied", target=self.player.name, effect=effect.localized_name)
                )

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
