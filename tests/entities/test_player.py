import pytest

from src.data.classes import CLASS_REGISTRY
from src.entities.actor import Stats
from src.entities.player import Player
from src.systems.abilities import Ability, AbilityType, AbilityRarity


def test_available_promotions_underleveled():
    player = Player(class_id="warrior")
    assert player.level == 1
    assert player.available_promotions() == []


def test_available_promotions_leveled():
    player = Player(class_id="warrior")
    player.level = 10
    promotions = player.available_promotions()
    assert "paladin" in promotions
    assert "berserker" in promotions
    assert len(promotions) == 2


def test_available_promotions_max_tier():
    player = Player(class_id="paladin")
    player.level = 20
    assert player.available_promotions() == []


def test_promote_ineligible_class():
    player = Player(class_id="warrior")
    player.level = 15
    # Warrior cannot promote to Assassin
    assert not player.promote("assassin")
    assert player.class_id == "warrior"


def test_promote_underleveled():
    player = Player(class_id="warrior")
    player.level = 9
    # Warrior under level 10 cannot promote
    assert not player.promote("paladin")
    assert player.class_id == "warrior"


def test_promote_success():
    player = Player(class_id="warrior")
    player.level = 15

    # Give a level up bonus first to ensure it's retained
    player.base_stats = player.base_stats.add(Stats(max_hp=5, attack=2, defense=1, speed=0, crit_chance=0))
    initial_base_stats = player.base_stats

    # Promote to paladin
    assert player.promote("paladin")

    assert player.class_id == "paladin"

    assert player.base_stats == initial_base_stats
    assert player.signature_passive.id == "paladin_oath"
    assert len(player.abilities.passive) <= 2
    assert player.pending_ability_choices[0] == "EPIC"


def test_effective_stats_base():
    player = Player(class_id="warrior")
    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp
    assert stats.attack == player.base_stats.attack
    assert stats.defense == player.base_stats.defense
    assert stats.speed == player.base_stats.speed
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance)


def test_player_base_stats_are_not_shared_with_class_template():
    template_attack = CLASS_REGISTRY["warrior"].base_stats.attack
    first = Player(class_id="warrior")
    first.base_stats.attack += 5

    second = Player(class_id="warrior")

    assert CLASS_REGISTRY["warrior"].base_stats.attack == template_attack
    assert second.base_stats.attack == template_attack


def test_rogue_has_modest_survivability_tuning():
    rogue = CLASS_REGISTRY["rogue"]

    assert rogue.base_stats.max_hp == 105
    assert rogue.growth_per_level.max_hp == 12


def test_effective_stats_with_equipment(monkeypatch):
    player = Player(class_id="warrior")

    def mock_get_equipment_stats():
        return Stats(max_hp=20, attack=10, defense=5, speed=2, crit_chance=0.05)

    monkeypatch.setattr(player.inventory, "get_equipment_stats", mock_get_equipment_stats)

    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp + 20
    assert stats.attack == player.base_stats.attack + 10
    assert stats.defense == player.base_stats.defense + 5
    assert stats.speed == player.base_stats.speed + 2
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance + 0.05)


def test_effective_stats_with_passive():
    player = Player(class_id="warrior")

    def modify_stats_hook(stats: Stats) -> Stats:
        return stats.add(Stats(max_hp=15, attack=8, defense=4, speed=3, crit_chance=0.10))

    passive_ability = Ability(
        id="mock_passive",
        name="Mock Passive",
        description="A mocked passive ability for testing.",
        ability_type=AbilityType.PASSIVE,
        rarity=AbilityRarity.STANDARD,
        modify_stats_hook=modify_stats_hook
    )

    player.abilities.passive.append(passive_ability)

    stats = player.effective_stats
    assert stats.max_hp == player.base_stats.max_hp + 15
    assert stats.attack == player.base_stats.attack + 8
    assert stats.defense == player.base_stats.defense + 4
    assert stats.speed == player.base_stats.speed + 3
    assert stats.crit_chance == pytest.approx(player.base_stats.crit_chance + 0.10)


def test_gain_experience_single_level_up():
    player = Player(class_id="warrior")
    initial_max_hp = player.max_hp
    initial_attack = player.base_stats.attack
    initial_defense = player.base_stats.defense
    initial_speed = player.base_stats.speed
    initial_crit = player.base_stats.crit_chance
    initial_stat_points = player.stat_points

    # Damage the player to verify HP restoration
    player.current_hp = 1

    # Level 1 to 2 requires 50 exp
    assert player.exp_to_next_level == 50
    assert player.gain_experience(50)
    assert player.level == 2
    assert player.experience == 0

    class_def = CLASS_REGISTRY["warrior"]

    # Check stat bonuses
    assert player.max_hp == initial_max_hp + class_def.growth_per_level.max_hp
    assert player.base_stats.attack == initial_attack + class_def.growth_per_level.attack
    assert player.base_stats.defense == initial_defense + class_def.growth_per_level.defense
    assert player.base_stats.speed == initial_speed + class_def.growth_per_level.speed
    assert player.base_stats.crit_chance == pytest.approx(initial_crit + class_def.growth_per_level.crit_chance)

    # Level-up restores half of the new maximum HP.
    assert player.current_hp == min(player.max_hp, 1 + int(player.max_hp * 0.50))

    # Check stat points
    assert player.stat_points == initial_stat_points + 2


def test_gain_experience_negative_or_zero():
    player = Player(class_id="warrior")
    assert player.experience == 0

    assert not player.gain_experience(0)
    assert player.experience == 0

    assert not player.gain_experience(-10)
    assert player.experience == 0


def test_gain_experience_no_level_up():
    player = Player(class_id="warrior")
    assert player.level == 1
    assert player.experience == 0

    # 50 exp to next level. Let's give less than that.
    # Base multiplier for warrior is 1.0
    assert not player.gain_experience(40)
    assert player.experience == 40
    assert player.level == 1


def test_gain_experience_multiplier():
    player = Player(class_id="warrior")
    # Change multiplier for test
    player.exp_multiplier = 1.5

    assert not player.gain_experience(10)
    # 10 * 1.5 = 15
    assert player.experience == 15


def test_gain_experience_multiple_level_ups():
    player = Player(class_id="warrior")
    assert player.level == 1
    initial_hp = player.max_hp

    # From level 1, calculate exp thresholds for next few levels
    # Lvl 1->2: 50 + 15(0) + 7(0) = 50
    # Lvl 2->3: 50 + 15(1) + 7(1) = 72
    # Total needed for Lvl 3 = 122

    assert player.gain_experience(150)
    assert player.level == 3
    assert player.experience == 150 - 122  # 28


def test_gain_experience_max_level_cap():
    player = Player(class_id="warrior")
    # Artificially set to level 19
    player.level = 19

    # Calculate exp needed for level 19 to 20
    from src.core.math_utils import calculate_exp_threshold
    needed = calculate_exp_threshold(19)
    player.exp_to_next_level = needed
    player.experience = 0

    # Give enough to reach level 20 and overflow greatly
    assert player.gain_experience(needed + 50000)

    assert player.level == 20
    # Experience should be capped at exp_to_next_level when max level is reached
    assert player.experience == player.exp_to_next_level


def test_gain_experience_ability_milestones():
    player = Player(class_id="warrior")

    # At level 1, no milestones
    assert player.pending_ability_choices == []

    # Reach level 4 ("STANDARD")
    player.level = 3
    player.experience = 0
    from src.core.math_utils import calculate_exp_threshold
    needed = calculate_exp_threshold(3)
    player.exp_to_next_level = needed

    player.gain_experience(needed)
    assert player.level == 4
    assert player.pending_ability_choices == ["STANDARD"]

    # Clear and reach level 10 ("EPIC")
    player.pending_ability_choices.clear()
    player.level = 9
    player.experience = 0
    needed = calculate_exp_threshold(9)
    player.exp_to_next_level = needed

    player.gain_experience(needed)
    assert player.level == 10
    assert player.pending_ability_choices == ["EPIC"]

    # Check a level without milestone logic (level 11)
    player.pending_ability_choices.clear()
    player.level = 11
    player._check_ability_milestone()
    assert player.pending_ability_choices == []

    player.level = 8
    player._check_ability_milestone()
    assert player.pending_ability_choices == ["STANDARD"]

    player.level = 20
    player.pending_ability_choices.clear()
    player._check_ability_milestone()
    assert player.pending_ability_choices == ["EPIC"]



def test_rogue_promotions_and_legacy_assassin_save_alias():
    rogue = Player(class_id="rogue")
    assert set(CLASS_REGISTRY["rogue"].promotions) == {"venomancer", "duelist"}
    for legacy_id in ("assassin", "envenomator"):
        legacy_player = Player(class_id=legacy_id)
        assert legacy_player.class_id == "venomancer"


def test_level_ten_sets_promotion_due_and_uses_current_class_growth():
    player = Player(class_id="warrior")
    player.level = 9
    from src.core.math_utils import calculate_exp_threshold
    player.exp_to_next_level = calculate_exp_threshold(9)
    player.current_hp = 1

    assert player.gain_experience(player.exp_to_next_level)

    assert player.level == 10
    assert player.promotion_due
    assert player.pending_ability_choices == ["EPIC"]
    assert player.current_hp < player.max_hp

    old_attack = player.base_stats.attack
    assert player.promote("berserker")
    assert player.base_stats.attack == old_attack
    assert player.signature_passive.id == "berserker_rage"
    assert player.current_hp <= player.max_hp
    assert player.pending_ability_choices == ["EPIC"]

    player.level = 10
    player._apply_level_up_bonuses()
    assert player.base_stats.attack == old_attack + CLASS_REGISTRY["berserker"].growth_per_level.attack


def test_signature_passive_is_applied_but_not_in_regular_slots():
    player = Player(class_id="warrior")
    player.level = 10
    assert player.promote("paladin")
    assert len(player.abilities.passive) == 0
    assert player.signature_passive not in player.abilities.passive
    assert player.effective_stats.defense == player.base_stats.defense + 3


def test_every_advanced_class_has_a_combat_sprite():
    from src.tools.generate_assets import CLASS_SPRITE_COORDS

    advanced_classes = {
        promoted for class_def in CLASS_REGISTRY.values() for promoted in class_def.promotions
    }
    assert advanced_classes
    assert advanced_classes <= CLASS_SPRITE_COORDS.keys()


def test_promotion_portrait_requires_a_second_tap_to_confirm(monkeypatch):
    import pyxel

    from src.core.game_state import GameMode, GameState
    from src.ui.renderer import Renderer
    from src.ui.views.promotion import PromotionView

    state = GameState()
    state.player.level = 10
    state.player.promotion_due = True
    state.current_mode = GameMode.PROMOTION
    view = PromotionView()
    assert view.selected_index is None

    monkeypatch.setattr(pyxel, "btnp", lambda *_args: False)
    monkeypatch.setattr(
        Renderer,
        "is_clicked",
        staticmethod(lambda x, _y, _w, _h: x == 8),
    )

    view.update(state)
    assert view.selected_index == 0
    assert state.current_mode == GameMode.PROMOTION
    assert state.player.class_id == "warrior"

    view.update(state)
    assert state.current_mode == GameMode.ABILITY_CHOICE
    assert state.player.class_id == "paladin"


def test_game_state_can_start_level_ten_promotion_and_restore_return_mode():
    from src.core.game_state import GameMode, GameState

    state = GameState()
    state.player.level = 10
    state.player.promotion_due = True
    state.current_mode = GameMode.EVENTS

    assert state.begin_promotion()
    assert state.current_mode == GameMode.PROMOTION
    assert state.promotion_return_mode == GameMode.EVENTS


def test_promotion_from_ability_choice_does_not_restore_an_empty_choice_view():
    from src.core.game_state import GameMode, GameState

    state = GameState()
    state.player.level = 10
    state.player.promotion_due = True
    state.current_mode = GameMode.ABILITY_CHOICE

    assert state.begin_promotion()
    assert state.promotion_return_mode is None


def test_promotion_epic_choice_resumes_after_act_boss_rewards():
    from types import SimpleNamespace

    from src.core.game_state import GameMode, GameState
    from src.systems.map_gen import NodeType
    from src.ui.views.ability_choice import AbilityChoiceView

    state = GameState()
    state.player.pending_ability_choices = ["EPIC"]
    state.promotion_return_mode = GameMode.LOOT
    state.map_graph = SimpleNamespace(current_node=SimpleNamespace(node_type=NodeType.BOSS))
    state.act = 1
    state.biome_route_mode = "PATHFINDER"

    AbilityChoiceView()._finish_choice(state)

    assert state.current_mode == GameMode.BIOME_SELECT
    assert state.act == 2


def test_promotion_epic_choice_finishes_act_three_boss_run():
    from types import SimpleNamespace

    from src.core.game_state import GameMode, GameState
    from src.systems.map_gen import NodeType
    from src.ui.views.ability_choice import AbilityChoiceView

    state = GameState()
    state.player.pending_ability_choices = ["EPIC"]
    state.promotion_return_mode = GameMode.LOOT
    state.map_graph = SimpleNamespace(current_node=SimpleNamespace(node_type=NodeType.BOSS))
    state.act = 3

    AbilityChoiceView()._finish_choice(state)

    assert state.current_mode == GameMode.VICTORY


def test_promotion_epic_choice_returns_to_map_for_middle_node():
    from types import SimpleNamespace

    from src.core.game_state import GameMode, GameState
    from src.systems.map_gen import NodeType
    from src.ui.views.ability_choice import AbilityChoiceView

    state = GameState()
    state.player.pending_ability_choices = ["EPIC"]
    state.promotion_return_mode = GameMode.LOOT
    state.map_graph = SimpleNamespace(current_node=SimpleNamespace(node_type=NodeType.COMBAT))

    AbilityChoiceView()._finish_choice(state)

    assert state.current_mode == GameMode.MAP
