import os
import sys

import pytest

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from src.systems.combat import CombatSystem, CombatResult
from src.entities.player import Player
from src.entities.enemy import Enemy, EnemyTier
from src.entities.actor import Stats
from src.systems.status import StatusEffect, StatusTrigger, StatusType


class MockRNG:
    def __init__(self, random_val=0.5, uniform_val=1.0):
        self.random_val = random_val
        self.uniform_val = uniform_val

    def random(self):
        return self.random_val

    def uniform(self, a, b):
        return self.uniform_val


@pytest.fixture
def base_player():
    player = Player(name="Hero", class_id="warrior")
    # override stats for deterministic testing
    player.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    return player


@pytest.fixture
def base_enemy():
    stats = Stats(max_hp=50, attack=5, defense=0, speed=5, crit_chance=0.0)
    return Enemy(
        name="Goblin",
        stats=stats,
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=10,
        gold_reward=5
    )


def test_combat_init(base_player, base_enemy):
    combat = CombatSystem(player=base_player, enemy=base_enemy, seed=42)
    assert combat.is_active()
    assert combat.result == CombatResult.IN_PROGRESS
    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 0


def test_speed_determines_turn(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    # Player speed 100, Enemy speed 10
    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)  # no crit, 1.0 variance

    combat.step()

    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 10
    assert base_enemy.current_hp == 40


def test_resolve_all_player_victory(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.attack = 50
    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)  # guaranteed 50 damage -> exactly enemy max_hp

    result = combat.resolve_all(max_ticks=10)

    assert result == CombatResult.PLAYER_VICTORY
    assert not base_enemy.is_alive
    assert base_player.gold == 5  # 0 + 5 from base_enemy gold reward


def test_resolve_all_player_defeat(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 10
    base_enemy.base_stats.attack = 100
    base_enemy.base_stats.speed = 100

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)  # guaranteed 100 damage -> exactly player max_hp

    result = combat.resolve_all(max_ticks=10)

    assert result == CombatResult.PLAYER_DEFEAT
    assert not base_player.is_alive


def test_stun_status_prevents_action(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_enemy.base_stats.speed = 10

    stun_effect = StatusEffect(
        id="stun",
        name="Stun",
        badge="STN",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.PRE_ACTION,
        duration=1
    )
    base_player.apply_status(stun_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(uniform_val=1.0)

    combat.step()

    # Player gauge reached 100, but is stunned, so action is skipped, gauge is reset to 0, stun duration decreased
    assert combat.player_gauge == 0
    assert combat.enemy_gauge == 10
    # No damage taken by enemy
    assert base_enemy.current_hp == 50
    # Stun duration decreased to 0 and removed
    assert len(base_player.statuses) == 0


def test_combat_crit(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_player.base_stats.crit_chance = 1.0  # Guarantee crit

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    # mock rng random to return 0.0 (less than 1.0) -> is_crit is True
    # mock rng uniform to return 1.0
    combat.rng = MockRNG(random_val=0.0, uniform_val=1.0)

    combat.step()

    # damage should be 10 * 1.5 = 15
    assert base_enemy.current_hp == 35


def test_blind_status_miss(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100

    blind_effect = StatusEffect(
        id="blind",
        name="Blind",
        badge="BLN",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.ON_TICK,
        duration=2
    )
    base_player.apply_status(blind_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.1, uniform_val=1.0)  # rng < 0.50 triggers miss

    combat.step()

    # Enemy should take no damage
    assert base_enemy.current_hp == 50


def test_vulnerable_status_extra_damage(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 100
    base_player.base_stats.attack = 10  # with uniform_val=1.0, raw_dmg = 10

    vuln_effect = StatusEffect(
        id="vulnerable",
        name="Vulnerable",
        badge="VUL",
        color=8,
        status_type=StatusType.DEBUFF,
        trigger=StatusTrigger.ON_TICK,
        duration=2
    )
    base_enemy.apply_status(vuln_effect)

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)

    combat.step()

    # damage should be int(10 * 1.30) = 13
    assert base_enemy.current_hp == 37


def test_enemy_attacks_player(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_enemy.base_stats.speed = 100
    base_player.base_stats.speed = 10

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)

    combat.step()

    assert combat.enemy_gauge == 0
    assert combat.player_gauge == 10
    # Player takes damage: enemy attack (5) - player def (0) = 5
    assert base_player.current_hp == 95
from src.data.abilities import get_ability_by_id

def test_archmage_barrier_mechanics(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    # Attach archmage_focus signature passive
    base_player.signature_passive = get_ability_by_id("archmage_focus")
    base_player.base_stats.hp = 100
    base_player.current_hp = 100

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    # 20% barrier of 100 max HP = 20 shield
    assert base_player.shield == 20

    # Enemy hits player for 15 damage
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)
    base_player.take_damage(15)
    assert base_player.shield == 5
    assert base_player.current_hp == 100

    # Another hit for 10 damage: 5 absorbed by shield, 5 applied to HP
    base_player.take_damage(10)
    assert base_player.shield == 0
    assert base_player.current_hp == 95

    # Combat ends with victory -> shield reset to 0
    base_enemy.current_hp = 0
    combat._evaluate_battle_outcome()
    assert base_player.shield == 0


def test_paladin_oath_heal_quarter(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.signature_passive = get_ability_by_id("paladin_oath")
    base_player.base_stats.speed = 100
    base_player.base_stats.attack = 20
    base_player.base_stats.crit_chance = 0.0
    base_enemy.base_stats.speed = 10
    base_enemy.base_stats.defense = 0
    base_enemy.base_stats.hp = 100
    base_enemy.current_hp = 100

    base_player.current_hp = 50  # Missing 50 HP

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)
    combat.step()

    # Base hit deals 20 damage. Signature hit deals 50% ATK = 10 damage.
    # Total damage to enemy: 30
    assert base_enemy.current_hp == 70
    # Paladin heal is 15% of signature damage: max(1, int(10 * 0.15)) = 1 HP
    assert base_player.current_hp == 51


def test_venomancer_mastery_combat_start_poison_and_first_tick_detonation(base_player, base_enemy, monkeypatch):
    import pyxel
    from src.systems.status import get_status_by_id

    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.signature_passive = get_ability_by_id("venomancer_mastery")
    base_player.base_stats.speed = 10
    base_player.base_stats.attack = 20
    base_enemy.base_stats.speed = 10
    base_enemy.base_stats.defense = 0
    base_enemy.base_stats.max_hp = 100
    base_enemy.current_hp = 100

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    poison = next((s for s in base_enemy.statuses if s.id == "poison"), None)
    assert poison is not None
    assert poison.stacks == 2
    assert poison.max_stacks == 1

    # Tick 1: 2 stacks * 2 potency = 4 poison dmg + 200% detonation (8 dmg) = 12 total dmg
    combat.step()
    assert base_enemy.current_hp == 88
    assert combat.signature_proc_counts.get("venomancer_mastery", 0) == 1

    # Tick 2: same poison application does NOT detonate again (only 4 poison dmg)
    combat.step()
    assert base_enemy.current_hp == 84
    assert combat.signature_proc_counts.get("venomancer_mastery", 0) == 1

    # Re-applying poison triggers detonation again on the next tick
    base_enemy.apply_status(get_status_by_id("poison", duration=5, potency=2, max_stacks=1))
    combat.step()
    assert base_enemy.current_hp == 72
    assert combat.signature_proc_counts.get("venomancer_mastery", 0) == 2


def test_berserker_rage_threshold_and_heal(base_player, base_enemy, monkeypatch):
    import pyxel
    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.signature_passive = get_ability_by_id("berserker_rage")
    base_player.base_stats.hp = 100
    base_player.current_hp = 45  # Under 50% max HP at start of combat
    base_player.base_stats.speed = 100
    base_player.base_stats.attack = 50
    base_enemy.base_stats.speed = 10
    base_enemy.base_stats.defense = 0
    base_enemy.base_stats.hp = 200
    base_enemy.current_hp = 200

    combat = CombatSystem(player=base_player, enemy=base_enemy)
    # Starts armed because HP <= 50%
    assert combat.berserker_threshold_triggered is True
    assert combat.berserker_bonus_ready is True

    combat.rng = MockRNG(random_val=0.5, uniform_val=1.0)
    combat.step()

    # Berserker double damage: 50 * 2 = 100 damage
    assert base_enemy.current_hp == 100
    # Heal is half damage (50), but capped at 30% max HP (30 HP)
    # 45 + 30 = 75 HP
    assert base_player.current_hp == 75


def test_speed_normalization_preserves_ratio_and_caps_tick_rate(base_player, base_enemy, monkeypatch):
    import pyxel
    from src.config import TARGET_COMBAT_SPEED

    monkeypatch.setattr(pyxel, "play", lambda *args, **kwargs: None)

    base_player.base_stats.speed = 50
    base_enemy.base_stats.speed = 75

    combat = CombatSystem(player=base_player, enemy=base_enemy, normalize_speeds=True)
    assert base_player.base_stats.speed == 50
    assert base_enemy.base_stats.speed == 75

    scaled_p = combat.get_scaled_speed(base_player.effective_stats.speed)
    scaled_e = combat.get_scaled_speed(base_enemy.effective_stats.speed)

    # Faster combatant is scaled to TARGET_COMBAT_SPEED (12.5 gauge/tick -> 8 ticks = 4.0s at 1x speed)
    assert pytest.approx(scaled_e) == TARGET_COMBAT_SPEED
    # Relative speed ratio (50 / 75 == 2 / 3) is strictly preserved
    assert pytest.approx(scaled_p / scaled_e) == 50 / 75

    # After 7 ticks, neither combatant has acted yet (7 * 12.5 = 87.5 < 100)
    for _ in range(7):
        combat.step()
    assert combat.enemy_actions_taken == 0

    # On tick 8 (4.0s at 1x speed), the faster combatant acts
    combat.step()
    assert combat.enemy_actions_taken == 1
