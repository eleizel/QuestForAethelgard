from __future__ import annotations

from types import SimpleNamespace

from src.config import COLOR_BLACK, COLOR_WHITE, COLOR_YELLOW
from src.core.audio import audio
from src.data.enemies import ENEMY_SKILLS, EnemySkill
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.entities.player import Player
from src.systems.combat import CombatResult, CombatSystem
from src.systems.status import create_bleed
from src.ui.views.combat import CombatView


def make_enemy(archetype_id: str, tier: EnemyTier) -> Enemy:
    return Enemy(
        name=archetype_id,
        stats=Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0),
        tier=tier,
        floor_level=1,
        exp_reward=0,
        gold_reward=0,
        archetype_id=archetype_id,
    )


def make_player() -> Player:
    player = Player(name="Hero", class_id="warrior")
    player.base_stats = Stats(max_hp=100, attack=10, defense=0, speed=10, crit_chance=0.0)
    player.current_hp = 100
    return player


def silence_audio(monkeypatch) -> None:
    monkeypatch.setattr(audio, "play_sfx", lambda *_args, **_kwargs: None)


class FixedRng:
    def random(self) -> float:
        return 0.5

    def uniform(self, _low: float, _high: float) -> float:
        return 1.0


def test_common_enemy_death_hook_uses_its_concept_status(monkeypatch) -> None:
    silence_audio(monkeypatch)
    enemy = make_enemy("spore_pod", EnemyTier.COMMON)
    player = make_player()
    combat = CombatSystem(player, enemy)
    enemy.current_hp = 0

    combat._evaluate_battle_outcome()
    combat._trigger_enemy_death_hook()

    assert combat.result == CombatResult.PLAYER_VICTORY
    assert player.has_status("poison")
    assert combat.enemy_speech_bubble


def test_common_enemy_without_status_deals_defense_ignoring_death_burst(monkeypatch) -> None:
    silence_audio(monkeypatch)
    enemy = make_enemy("bramble_hound", EnemyTier.COMMON)
    player = make_player()
    player.base_stats.defense = 100
    combat = CombatSystem(player, enemy)
    enemy.current_hp = 0

    combat._evaluate_battle_outcome()
    combat._trigger_enemy_death_hook()

    assert player.current_hp == 90
    assert combat.completion_delay_ticks == 3


def test_enemy_skills_are_assigned_by_tier_and_cool_down_in_enemy_actions(monkeypatch) -> None:
    silence_audio(monkeypatch)
    player = make_player()
    enemy = make_enemy("bramble_hound", EnemyTier.UNCOMMON)
    combat = CombatSystem(player, enemy)
    combat.rng = FixedRng()

    combat._execute_enemy_attack()
    assert player.current_hp == 87  # 130% of 10 ATK
    assert combat.enemy_skill_cooldowns["strong_attack"] == 4

    # Three complete enemy actions pass before a three-action cooldown is ready.
    hp_after_skill = player.current_hp
    combat._execute_enemy_attack()
    combat._execute_enemy_attack()
    assert player.current_hp == hp_after_skill - 20
    combat._execute_enemy_attack()
    assert player.current_hp == hp_after_skill - 30
    combat._execute_enemy_attack()
    assert player.current_hp == hp_after_skill - 43

    healer = make_enemy("rotting_woodwose", EnemyTier.UNCOMMON)
    assert [skill.id for skill in healer.skills] == ["heal"]
    healer.current_hp = 50
    heal_combat = CombatSystem(make_player(), healer)
    heal_combat._execute_enemy_attack()
    assert healer.current_hp == 60
    assert heal_combat.enemy_skill_cooldowns["heal"] == 3

    boss = make_enemy("blood_god_avatar", EnemyTier.BOSS)
    assert [skill.id for skill in boss.skills] == ["heal", "strong_attack"]
    assert make_enemy("bramble_hound", EnemyTier.COMMON).skills == ()
    assert ENEMY_SKILLS["signature_attack"].damage_multiplier == 2.0


def test_half_health_phase_applies_tradeoff_and_boss_threshold_replaces_bubble(monkeypatch) -> None:
    silence_audio(monkeypatch)
    elite = make_enemy("verdant_abomination", EnemyTier.ELITE)
    player = make_player()
    combat = CombatSystem(player, elite)
    combat.damage_enemy(50)

    assert combat._enemy_half_phase_triggered
    assert elite.has_status("haste")
    assert elite.has_status("bleed")
    assert combat.enemy_speech_bubble == "Now I'm really mad!"

    boss = make_enemy("blood_god_avatar", EnemyTier.BOSS)
    boss_combat = CombatSystem(make_player(), boss)
    boss_combat.damage_enemy(80)  # Crosses both thresholds in one hit.

    assert boss_combat._enemy_half_phase_triggered
    assert boss_combat._enemy_quarter_hook_triggered
    assert boss_combat.enemy_speech_bubble == "Feel my real power!"
    assert boss_combat.pending_enemy_signature is ENEMY_SKILLS["signature_attack"]

    boss_combat.rng = FixedRng()
    boss_combat._execute_enemy_attack()
    assert boss_combat.pending_enemy_signature is None
    assert boss_combat.enemy_speech_bubble is None
    assert boss_combat.player.current_hp == 76
    assert any("Signature Attack" in line for line in boss_combat.combat_logs)
    boss.current_hp = 0
    boss_combat._evaluate_battle_outcome()
    assert boss_combat.enemy_speech_bubble is None


def test_status_skill_and_dot_crossing_threshold(monkeypatch) -> None:
    silence_audio(monkeypatch)
    player = make_player()
    enemy = make_enemy("bramble_hound", EnemyTier.UNCOMMON)
    enemy.skills = (EnemySkill(
        id="crippling_blow", kind="status", cooldown=2, status_id="stun", status_duration=2,
    ),)
    combat = CombatSystem(player, enemy)
    combat._execute_enemy_attack()
    assert player.has_status("stun")
    assert combat.enemy_skill_cooldowns["crippling_blow"] == 3

    boss = make_enemy("blood_god_avatar", EnemyTier.BOSS)
    boss.current_hp = 60
    boss_combat = CombatSystem(make_player(), boss)
    boss.apply_status(create_bleed(duration=1, potency=20))
    boss_combat._process_status_ticks(boss)

    assert boss.current_hp == 40
    assert boss_combat._enemy_half_phase_triggered
    assert boss_combat.enemy_speech_bubble == "Now I'm really mad!"


def test_enemy_speech_bubble_is_drawn_in_the_arena(monkeypatch) -> None:
    drawn_rects: list[tuple[int, ...]] = []
    drawn_text: list[tuple[int, int, str, int]] = []
    monkeypatch.setattr("pyxel.rect", lambda *args: drawn_rects.append(args))
    monkeypatch.setattr("pyxel.rectb", lambda *args: drawn_rects.append(args))
    monkeypatch.setattr("pyxel.tri", lambda *args: None)

    renderer = SimpleNamespace(
        get_text_width=lambda text: len(text) * 4,
        draw_text=lambda x, y, text, color: drawn_text.append((x, y, text, color)),
    )
    combat = SimpleNamespace(enemy_speech_bubble="Feel my real power!")

    CombatView._draw_enemy_speech_bubble(combat, renderer)

    assert len(drawn_rects) == 2
    assert drawn_rects[0][-1] == COLOR_WHITE
    assert drawn_rects[1][-1] == COLOR_YELLOW
    assert drawn_text[0][2] == "Feel my real power!"
    assert drawn_text[0][3] == COLOR_BLACK
