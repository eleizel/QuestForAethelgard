import os
import sys

import pytest

# Ensure the src directory is in the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from src.data.abilities import (
    Ability,
    AbilityType,
    AbilityRarity,
    get_ability_by_id,
    CROSS_CUT,
    SHADOW_STRIKE,
    ARCANE_BOLT,
)
from src.systems.abilities import PlayerAbilities

from src.entities.actor import Stats
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.systems.combat import CombatSystem


def test_player_abilities_manager():
    manager = PlayerAbilities()

    active_1 = Ability("a1", "A1", "desc", AbilityType.ACTIVE, AbilityRarity.STANDARD)
    active_2 = Ability("a2", "A2", "desc", AbilityType.ACTIVE, AbilityRarity.STANDARD)
    active_3 = Ability("a3", "A3", "desc", AbilityType.ACTIVE, AbilityRarity.STANDARD)

    passive_1 = Ability("p1", "P1", "desc", AbilityType.PASSIVE, AbilityRarity.STANDARD)
    passive_2 = Ability(
        "veterans_instincts", "Vet", "desc", AbilityType.PASSIVE, AbilityRarity.STANDARD
    )
    passive_3 = Ability("p3", "P3", "desc", AbilityType.PASSIVE, AbilityRarity.STANDARD)

    # Test adding capabilities
    assert manager.add_ability(active_1) == True
    assert manager.add_ability(active_2) == True
    assert manager.add_ability(active_3) == False  # Capacity 2

    assert manager.add_ability(passive_1) == True
    assert manager.add_ability(passive_2) == True
    assert manager.add_ability(passive_3) == False  # Capacity 2

    assert len(manager.active) == 2
    assert len(manager.passive) == 2

    # Check cached flags update
    assert manager.has_veterans_instincts == True

    # Test replacement
    manager.replace_ability(active_3, 0)
    assert manager.active[0].id == "a3"

    manager.replace_ability(passive_3, 1)
    assert manager.passive[1].id == "p3"

    # Check cached flags update on replace
    assert manager.has_veterans_instincts == False


def test_ability_base_methods():
    # Test execute
    executed = False

    def mock_execute(combat_state):
        nonlocal executed
        executed = True
        return "log", 10, True

    ability = Ability(
        "t1",
        "T1",
        "desc",
        AbilityType.ACTIVE,
        AbilityRarity.STANDARD,
        execute_hook=mock_execute,
    )
    log, dmg, crit = ability.execute(None)
    assert executed == True
    assert log == "log"
    assert dmg == 10
    # assert crit == False

    # Test modify stats
    modified = False

    def mock_modify_stats(stats):
        nonlocal modified
        modified = True
        return Stats(max_hp=999, attack=0, defense=0, speed=0, crit_chance=0.0)

    ability_passive = Ability(
        "t2",
        "T2",
        "desc",
        AbilityType.PASSIVE,
        AbilityRarity.STANDARD,
        modify_stats_hook=mock_modify_stats,
    )
    base_stats = Stats(max_hp=10, attack=10, defense=10, speed=10, crit_chance=0.1)
    new_stats = ability_passive.modify_stats(base_stats)
    assert modified == True
    assert new_stats.max_hp == 999

    # Test on damage taken
    damage_taken = False

    def mock_on_damage_taken(actor, raw_damage):
        nonlocal damage_taken
        damage_taken = True
        return raw_damage - 5

    ability_passive.on_damage_taken_hook = mock_on_damage_taken
    reduced_damage = ability_passive.on_damage_taken(None, 20)
    assert damage_taken == True
    assert reduced_damage == 15

    # Test on attack dealt
    attack_dealt = False

    def mock_on_attack_dealt(actor, target, damage, is_crit):
        nonlocal attack_dealt
        attack_dealt = True

    ability_passive.on_attack_dealt_hook = mock_on_attack_dealt
    ability_passive.on_attack_dealt(None, None, 10, False)
    assert attack_dealt == True


def test_active_abilities(monkeypatch):
    player = Player(name="TestPlayer", class_id="warrior")
    from src.entities.enemy import EnemyTier

    enemy = Enemy(
        name="TestEnemy",
        stats=Stats(100, 10, 20, 10, 0.0),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=10,
        gold_reward=10,
    )

    # Give them some fixed stats for predictability
    player.base_stats = Stats(
        max_hp=100, attack=100, defense=0, speed=10, crit_chance=0.0
    )
    player.current_hp = 100
    enemy.base_stats = Stats(
        max_hp=100, attack=10, defense=20, speed=10, crit_chance=0.0
    )
    enemy.current_hp = 100

    combat = CombatSystem(player, enemy)

    # Mocking rng to not crit
    class MockRNG:
        def random(self):
            return 0.99

        def uniform(self, a, b):
            return 1.0

    combat.rng = MockRNG()

    # CROSS_CUT (warrior): 2 strikes at 90% ATK each
    # take_damage reduces by defense if it's an attack, but abilities deal raw damage to take_damage which does its own mitigation
    # Oh wait, take_damage uses defense. Let's see how take_damage works.

    # Since take_damage uses actor.defense, let's just assert enemy hp dropped
    # Let's mock take_damage to return exact value
    def mock_take_damage(self, dmg, defense_penetration=0.0):
        return dmg

    monkeypatch.setattr(Enemy, "take_damage", mock_take_damage)

    # CROSS_CUT
    log, dmg, crit = CROSS_CUT.execute(combat)
    # player attack 100 -> 90% = 90. Two strikes = 180
    assert dmg == 180
    assert crit == False

    # SHADOW_STRIKE (rogue): 115% ATK and +15 percentage points of crit chance
    log, dmg, crit = SHADOW_STRIKE.execute(combat)
    assert dmg == 115
    assert crit == False

    # Let's mock RNG to always crit for SHADOW_STRIKE
    class MockRNGCrit:
        def random(self):
            return 0.01

        def uniform(self, a, b):
            return 1.0

    combat.rng = MockRNGCrit()

    combat.player_gauge = 0
    log, dmg, crit = SHADOW_STRIKE.execute(combat)
    assert dmg == int(115 * 1.5)  # 172
    # assert crit == False
    assert combat.player_gauge == 15  # refunded gauge

    # ARCANE_BOLT deals 110% ATK and passes 20% defense penetration to damage resolution.
    log, dmg, crit = ARCANE_BOLT.execute(combat)
    assert dmg == 110
    assert crit is False

    # PW_KILL
    # just test it does 999999
    pw_kill_ability = get_ability_by_id("pw_kill")
    log, dmg, crit = pw_kill_ability.execute(combat)
    assert dmg == 999999
    # assert crit == False


def test_passive_abilities(monkeypatch):
    # Test iron_skin
    iron_skin = get_ability_by_id("iron_skin")
    base_stats = Stats(max_hp=10, attack=10, defense=10, speed=10, crit_chance=0.1)
    new_stats = iron_skin.modify_stats(base_stats)
    # 15% of defense (10 * 0.15 = 1)
    assert new_stats.defense == 11

    reduced_dmg = iron_skin.on_damage_taken(None, 10)
    assert reduced_dmg == 9  # 10% reduction
    reduced_dmg = iron_skin.on_damage_taken(None, 1)
    assert reduced_dmg == 1  # minimum damage remains 1)

    # Test bloodlust
    bloodlust = get_ability_by_id("bloodlust")
    player = Player(name="TestPlayer", class_id="warrior")
    player.base_stats = Stats(
        max_hp=100, attack=10, defense=10, speed=10, crit_chance=0.1
    )
    player.current_hp = 50

    # damage dealt = 20, heal = 20% of 20 = 4
    bloodlust.on_attack_dealt(player, None, 20, False)
    assert player.current_hp == 54

    # Test the Warlock and Archmage damage-reduction passives.
    bone_barrier = get_ability_by_id("bone_barrier")
    assert bone_barrier.on_damage_taken(None, 100) == 80
    assert bone_barrier.on_damage_taken(None, 1) == 1

    ice_shards = get_ability_by_id("ice_shards")
    assert ice_shards.on_damage_taken(None, 100) == 90
    assert ice_shards.on_damage_taken(None, 1) == 1

    # Test nimble_reflexes
    nimble_reflexes = get_ability_by_id("nimble_reflexes")
    new_stats = nimble_reflexes.modify_stats(base_stats)
    assert new_stats.speed == pytest.approx(11)  # +10%
    assert new_stats.crit_chance == pytest.approx(0.15)  # +5 percentage points
    assert new_stats.defense == pytest.approx(10.5)  # +5%



def test_rogue_standard_effects(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier

    player = Player(name="RogueTest", class_id="rogue")
    player.base_stats = Stats(max_hp=100, attack=20, defense=0, speed=15, crit_chance=0.1)
    player.current_hp = 100
    enemy = Enemy(name="Target", stats=Stats(100, 10, 0, 10, 0.0), tier=EnemyTier.COMMON,
                  floor_level=1, exp_reward=1, gold_reward=1)
    enemy.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    enemy.current_hp = 100
    combat = CombatSystem(player, enemy)

    def exact_damage(self, raw_damage, defense_penetration=0.0):
        return raw_damage
    monkeypatch.setattr(Enemy, "take_damage", exact_damage)

    # Poison Shiv applies the existing poison status as well as its direct hit.
    poison_shiv = get_ability_by_id("poison_shiv")
    assert poison_shiv is not None
    poison_shiv.execute(combat)
    poison = next((status for status in enemy.statuses if status.id == "poison"), None)
    assert poison is not None
    assert poison.duration == 5
    assert poison.potency == 2

    # Exposed Weakness applies a 25% bonus to one subsequent damaging strike only.
    exposed = get_ability_by_id("exposed_weakness")
    assert exposed is not None
    player.abilities.add_ability(exposed)
    exposed.on_attack_dealt(player, enemy, 10, True)
    assert getattr(player, "_next_strike_bonus", False) is True
    assert combat.damage_enemy(100) == 125
    assert getattr(player, "_next_strike_bonus", False) is False
    assert combat.damage_enemy(100) == 100

    # Shadow Step updates the combat gauge through the combat reference.
    shadow_step = get_ability_by_id("shadow_step")
    assert shadow_step is not None
    player.abilities.add_ability(shadow_step)
    combat.player_gauge = 10
    player.take_damage(10)
    assert combat.player_gauge == 25


def test_ability_registry_and_retrieval():
    from src.data.abilities import get_random_abilities, ABILITY_REGISTRY

    # get_ability_by_id
    assert get_ability_by_id("cross_cut").name == "Cross Cut"
    assert get_ability_by_id("non_existent") == None

    # get_random_abilities
    random_standard_warrior = get_random_abilities(
        AbilityRarity.STANDARD, [], player_class="warrior", count=2
    )
    assert len(random_standard_warrior) == 2
    for ab in random_standard_warrior:
        assert ab.rarity == AbilityRarity.STANDARD
        assert ab.required_class in ("warrior", None)

    # Exclude known
    known = [
        ab.id for ab in ABILITY_REGISTRY.values() if ab.rarity == AbilityRarity.STANDARD
    ]
    random_all_known = get_random_abilities(AbilityRarity.STANDARD, known)
    assert len(random_all_known) == 0

    # Fallback when not enough available (should return known if nothing else available - wait, let's check code for get_random_abilities)
    # The code does:
    # if len(available) < count:
    #     available = [ab for ab in pool if ab.id not in known_abilities]
    # It removes class filter. Let's test that fallback.

    # Say we ask for 100 warrior abilities but there aren't that many
    random_fallback = get_random_abilities(
        AbilityRarity.STANDARD, [], player_class="warrior", count=100
    )
    # the pool of all standards is len(STANDARD_ABILITIES)
    from src.data.abilities import STANDARD_ABILITIES

    assert len(random_fallback) == len(STANDARD_ABILITIES)


def test_berserker_standard_abilities(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier

    player = Player(name="BerserkerTest", class_id="warrior")
    player.base_stats = Stats(max_hp=100, attack=100, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    enemy = Enemy(name="Target", stats=Stats(100, 10, 20, 10, 0.0), tier=EnemyTier.COMMON,
                  floor_level=1, exp_reward=1, gold_reward=1)
    enemy.base_stats = Stats(max_hp=100, attack=10, defense=20, speed=10, crit_chance=0.0)
    enemy.current_hp = 100
    combat = CombatSystem(player, enemy)

    def exact_damage(self, raw_damage, defense_penetration=0.0):
        return raw_damage
    monkeypatch.setattr(Enemy, "take_damage", exact_damage)

    reckless = get_ability_by_id("reckless_assault")
    assert reckless is not None and reckless.affinities == ("berserker",)
    _, damage, crit = reckless.execute(combat)
    assert damage == 150 and not crit
    assert player._reckless_assault_vulnerable is True

    blood_frenzy = get_ability_by_id("blood_frenzy")
    assert blood_frenzy is not None
    # Blood Frenzy is an acquired passive, so grant it before testing its scaling.
    assert all(ability.id != "blood_frenzy" for ability in player.abilities.passive)
    player.abilities.add_ability(blood_frenzy)
    assert player.effective_stats.attack == 100
    player.current_hp = 50
    assert player.effective_stats.attack == 125
    player.current_hp = 20
    assert player.effective_stats.attack == 140

    cull = get_ability_by_id("cull_the_weak")
    assert cull is not None and cull.affinities == ("berserker",)
    player.abilities.add_ability(cull)
    enemy.current_hp = 30
    assert combat.damage_enemy(100) == 130


def test_paladin_standard_abilities(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier

    player = Player(name="PaladinTest", class_id="warrior")
    player.base_stats = Stats(max_hp=100, attack=100, defense=30, speed=10, crit_chance=0.0)
    player.current_hp = 100
    enemy = Enemy(name="Target", stats=Stats(100, 10, 10, 10, 0.0), tier=EnemyTier.COMMON,
                  floor_level=1, exp_reward=1, gold_reward=1)
    enemy.base_stats = Stats(max_hp=100, attack=10, defense=10, speed=10, crit_chance=0.0)
    enemy.current_hp = 100
    combat = CombatSystem(player, enemy)

    def exact_damage(self, raw_damage, defense_penetration=0.0):
        self.last_penetration = defense_penetration
        return raw_damage
    monkeypatch.setattr(Enemy, "take_damage", exact_damage)

    strike = get_ability_by_id("shieldbreaker_strike")
    assert strike is not None and strike.affinities == ("paladin",)
    _, damage, crit = strike.execute(combat)
    assert damage == 115 and not crit

    defensive = get_ability_by_id("defensive_superiority")
    guard = get_ability_by_id("paladin_guard")
    assert defensive is not None and defensive.affinities == ("paladin",)
    assert guard is not None and guard.affinities == ("paladin",)

    player.abilities.add_ability(defensive)
    # Player DEF 30 vs enemy DEF 10 -> capped at 75% penetration.
    combat.damage_enemy(100)
    assert enemy.last_penetration == pytest.approx(0.75)

    player.abilities.add_ability(guard)
    player._last_ability_affinities = ("paladin",)
    assert guard.on_damage_taken(player, 100) == 90
    player._last_ability_affinities = ("berserker",)
    assert guard.on_damage_taken(player, 100) == 100



def test_burn_stacks_scale_with_max_hp_and_ignore_defense():
    from src.systems.status import get_status_by_id

    from src.entities.enemy import EnemyTier

    enemy = Enemy(
        name="BurnTarget",
        stats=Stats(max_hp=1000, attack=10, defense=999, speed=10, crit_chance=0.0),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=1,
        gold_reward=1,
    )
    enemy.current_hp = 1000

    for _ in range(3):
        burn = get_status_by_id("burn", duration=8, potency=1)
        assert burn is not None
        enemy.apply_status(burn)

    active_burn = next(status for status in enemy.statuses if status.id == "burn")
    assert active_burn.stacks == 3
    assert active_burn.max_stacks == 3
    assert active_burn.duration == 8

    # Reapplication adds no more than three stacks and refreshes the duration.
    active_burn.duration = 2
    burn = get_status_by_id("burn", duration=8, potency=1)
    assert burn is not None
    enemy.apply_status(burn)
    assert active_burn.stacks == 3
    assert active_burn.duration == 8

    # 3 stacks deal 3% of max HP (30) and bypass the enemy's 999 DEF.
    player = Player(name="TickSource", class_id="mage")
    combat = CombatSystem(player, enemy)
    combat._process_status_ticks(enemy)
    assert enemy.current_hp == 970


def test_soulfire_triggers_on_basic_attacks_but_not_abilities(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier

    player = Player(name="SoulfireTest", class_id="mage")
    player.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    enemy = Enemy(
        name="SoulfireTarget",
        stats=Stats(max_hp=1000, attack=10, defense=0, speed=10, crit_chance=0.0),
        tier=EnemyTier.COMMON,
        floor_level=1,
        exp_reward=1,
        gold_reward=1,
    )
    enemy.current_hp = 1000
    combat = CombatSystem(player, enemy)
    monkeypatch.setattr("src.systems.combat.pyxel.play", lambda *args: None)

    class ProcRNG:
        def random(self):
            return 0.0

        def uniform(self, a, b):
            return 1.0

    combat.rng = ProcRNG()
    soulfire = get_ability_by_id("soulfire")
    assert soulfire is not None
    player.abilities.add_ability(soulfire)

    combat.player_gauge = 100
    combat._execute_player_attack()
    burn = next((status for status in enemy.statuses if status.id == "burn"), None)
    assert burn is not None
    assert burn.stacks == 1

    # An active spell must not trigger Soulfire, even when its damage lands.
    enemy.statuses.clear()
    enemy.current_hp = 1000
    combat.player_gauge = 100
    combat.queued_ability = get_ability_by_id("arcane_bolt")
    combat._execute_player_attack()
    assert not enemy.has_status("burn")



def test_rogue_affinity_ability_roster():
    from src.data.abilities import get_ability_by_id
    expected = {
        "venomous_accumulation": "venomancer", "toxic_blood": "venomancer",
        "venomous_extraction": "venomancer", "riposte": "duelist",
        "whirlwind_defense": "duelist", "hilt_strike": "duelist",
    }
    for ability_id, affinity in expected.items():
        ability = get_ability_by_id(ability_id)
        assert ability is not None and affinity in ability.affinities
    assert get_ability_by_id("smoke_bomb") is None
    assert get_ability_by_id("dirty_tricks") is not None


def test_venom_stacks_tick_and_extract():
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier
    player = Player(name="VenomTest", class_id="rogue")
    player.base_stats = Stats(max_hp=100, attack=100, defense=0, speed=10, crit_chance=0.0)
    enemy = Enemy(name="VenomTarget", stats=Stats(1000, 10, 0, 10, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    enemy.current_hp = 1000
    combat = CombatSystem(player, enemy)
    mastery = get_ability_by_id("venomous_accumulation")
    shiv = get_ability_by_id("poison_shiv")
    extraction = get_ability_by_id("venomous_extraction")
    assert mastery and shiv and extraction
    player.abilities.add_ability(mastery)
    for _ in range(3):
        shiv.execute(combat)
    poison = next(status for status in enemy.statuses if status.id == "poison")
    assert (poison.stacks, poison.max_stacks, poison.duration) == (3, 3, 5)
    combat._process_status_ticks(enemy)
    assert enemy.current_hp == 655
    _, damage, _ = extraction.execute(combat)
    assert damage == 150 and enemy.current_hp == 505
    assert not enemy.has_status("poison")


def test_poison_without_venom_mastery_does_not_stack():
    from src.systems.status import get_status_by_id
    from src.entities.enemy import EnemyTier
    enemy = Enemy(name="PlainPoisonTarget", stats=Stats(100, 1, 0, 1, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    for _ in range(2):
        effect = get_status_by_id("poison", duration=5, potency=3)
        assert effect
        enemy.apply_status(effect)
    poison = next(status for status in enemy.statuses if status.id == "poison")
    assert poison.stacks == 1


def test_toxic_blood_reduces_damage_while_enemy_is_poisoned():
    from src.data.abilities import get_ability_by_id
    from src.systems.status import get_status_by_id
    from src.entities.enemy import EnemyTier
    player = Player(name="ToxicBloodTest", class_id="rogue")
    player.base_stats = Stats(100, 10, 0, 10, 0.0)
    player.current_hp = 100
    enemy = Enemy(name="PoisonedTarget", stats=Stats(100, 10, 0, 10, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    CombatSystem(player, enemy)
    passive = get_ability_by_id("toxic_blood")
    poison = get_status_by_id("poison")
    assert passive and poison
    player.abilities.add_ability(passive)
    enemy.apply_status(poison)
    assert player.take_damage(100) == 90


def test_dirty_tricks_and_hilt_strike_apply_control():
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier
    player = Player(name="ControlTest", class_id="rogue")
    player.base_stats = Stats(100, 100, 0, 10, 0.0)
    enemy = Enemy(name="ControlTarget", stats=Stats(1000, 10, 0, 10, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    combat = CombatSystem(player, enemy)
    class ProcRNG:
        def random(self): return 0.0
        def uniform(self, a, b): return 1.0
    combat.rng = ProcRNG()
    dirty = get_ability_by_id("dirty_tricks")
    hilt = get_ability_by_id("hilt_strike")
    assert dirty and hilt
    dirty.execute(combat)
    assert enemy.has_status("vulnerable") and enemy.has_status("blind")
    hilt.execute(combat)
    assert enemy.has_status("stun")


def test_riposte_blocks_then_counters_on_next_damage(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier
    player = Player(name="RiposteTest", class_id="rogue")
    player.base_stats = Stats(100, 40, 0, 10, 0.0)
    enemy = Enemy(name="RiposteTarget", stats=Stats(100, 10, 0, 10, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    enemy.current_hp = 100
    combat = CombatSystem(player, enemy)
    monkeypatch.setattr("src.systems.combat.pyxel.play", lambda *args: None)
    riposte = get_ability_by_id("riposte")
    assert riposte and riposte.is_stance
    player.abilities.add_ability(riposte)
    class BlockRNG:
        def random(self): return 0.0
        def uniform(self, a, b): return 1.0
    combat.rng = BlockRNG()
    hp = player.current_hp
    combat._execute_enemy_attack()
    assert player.current_hp == hp and player.has_stance("riposte")
    player.take_damage(10)
    assert enemy.current_hp == 80 and not player.has_stance("riposte")


def test_whirlwind_stance_adds_critical_hit_to_next_basic_attack(monkeypatch):
    from src.data.abilities import get_ability_by_id
    from src.entities.enemy import EnemyTier
    player = Player(name="WhirlwindTest", class_id="rogue")
    player.base_stats = Stats(100, 100, 10, 10, 1.0)
    enemy = Enemy(name="WhirlwindTarget", stats=Stats(1000, 10, 0, 10, 0.0),
                  tier=EnemyTier.COMMON, floor_level=1, exp_reward=1, gold_reward=1)
    enemy.current_hp = 1000
    combat = CombatSystem(player, enemy)
    monkeypatch.setattr("src.systems.combat.pyxel.play", lambda *args: None)
    whirlwind = get_ability_by_id("whirlwind_defense")
    assert whirlwind and whirlwind.is_stance
    player.abilities.add_ability(whirlwind)
    assert player.effective_stats.defense == pytest.approx(11)
    class CritRNG:
        def random(self): return 0.0
        def uniform(self, a, b): return 1.0
    combat.rng = CritRNG()
    combat.player_gauge = 100
    combat._execute_player_attack()
    assert player.has_stance("whirlwind_defense")
    combat.player_gauge = 100
    combat._execute_player_attack()
    assert enemy.current_hp == 663
    assert player.has_stance("whirlwind_defense")
