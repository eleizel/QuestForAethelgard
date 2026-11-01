"""Behavioral characterization tests for business logic currently trapped inside UI views.

This suite freezes the exact expected behavior of:
1. Shop transactions (buy/sell constraints, pouch limits, gold mutations, pricing formula)
2. Loot collection (pouch limits, inventory transfer, pending loot queue, route transitions)
3. Ability draft choices (rarity selection, active/passive slot limits, replacement, skipping)
4. Promotion logic (affinity-based class recommendations, promotion execution, mode transitions)
"""

import pytest
from src.core.game_state import GameState, GameMode
from src.entities.player import Player
from src.entities.item import Item, ItemType
from src.data.abilities import ABILITY_REGISTRY, Ability, AbilityRarity, AbilityType


def create_mock_player(class_id: str = "warrior", gold: int = 100, level: int = 1) -> Player:
    """Helper to initialize a player with controlled gold and empty pouch."""
    player = Player(class_id=class_id, name="TestHero")
    player.gold = gold
    player.level = level
    # Clear starting pouch for deterministic test conditions
    player.inventory.pouch.clear()
    return player


def create_test_item(item_id: str = "iron_sword", gold_value: int = 30) -> Item:
    """Helper to generate a lightweight item."""
    return Item(
        id=item_id,
        name="Test Blade",
        description="A blade for testing",
        item_type=ItemType.MATERIAL,
        gold_value=gold_value,
    )


# =============================================================================
# 1. SHOP TRANSACTION CHARACTERIZATION
# =============================================================================

class TestShopCharacterization:
    """Characterizes merchant rules currently in `src/ui/views/shop.py`."""

    def test_buy_item_success(self):
        """When gold and pouch space are sufficient, purchasing deducts gold and transfers item."""
        state = GameState()
        state.player = create_mock_player(gold=100)
        item = create_test_item(item_id="steel_sword", gold_value=50)
        price = 45
        state.merchant_stock = [(item, price)]

        # Mimic shop view buy logic:
        # if player.gold >= price and len(player.inventory.pouch) < MAX_POUCH_SLOTS:
        if state.player.gold >= price and len(state.player.inventory.pouch) < 10:
            state.player.gold -= price
            state.player.inventory.add_to_pouch(item)
            state.merchant_stock.pop(0)

        assert state.player.gold == 55
        assert len(state.player.inventory.pouch) == 1
        assert state.player.inventory.pouch[0].id == "steel_sword"
        assert len(state.merchant_stock) == 0

    def test_buy_item_insufficient_gold(self):
        """Player cannot buy when gold is lower than the item price."""
        state = GameState()
        state.player = create_mock_player(gold=20)
        item = create_test_item(item_id="mythic_sword", gold_value=200)
        price = 100
        state.merchant_stock = [(item, price)]

        initial_gold = state.player.gold
        # Attempt transaction
        if state.player.gold >= price and len(state.player.inventory.pouch) < 10:
            state.player.gold -= price
            state.player.inventory.add_to_pouch(item)
            state.merchant_stock.pop(0)

        assert state.player.gold == initial_gold
        assert len(state.player.inventory.pouch) == 0
        assert len(state.merchant_stock) == 1

    def test_buy_item_pouch_full(self):
        """Player cannot buy when pouch is at capacity (10 items)."""
        state = GameState()
        state.player = create_mock_player(gold=500)
        # Fill pouch to 10
        for i in range(10):
            state.player.inventory.pouch.append(create_test_item(f"item_{i}"))
        assert len(state.player.inventory.pouch) == 10

        item = create_test_item("new_item", gold_value=30)
        price = 25
        state.merchant_stock = [(item, price)]

        # Attempt transaction
        if state.player.gold >= price and len(state.player.inventory.pouch) < 10:
            state.player.gold -= price
            state.player.inventory.add_to_pouch(item)
            state.merchant_stock.pop(0)

        assert state.player.gold == 500
        assert len(state.player.inventory.pouch) == 10
        assert len(state.merchant_stock) == 1

    def test_sell_item_pricing_and_removal(self):
        """Selling calculates sell_value = max(5, item.gold_value // 2) and removes from pouch."""
        state = GameState()
        state.player = create_mock_player(gold=10)
        item_cheap = create_test_item("cheap_rock", gold_value=6)    # 6 // 2 = 3 -> clamped to 5
        item_expensive = create_test_item("gem", gold_value=60)      # 60 // 2 = 30 -> 30

        state.player.inventory.pouch.extend([item_cheap, item_expensive])

        # Sell item_cheap (index 0)
        sell_val_1 = max(5, state.player.inventory.pouch[0].gold_value // 2)
        assert sell_val_1 == 5
        state.player.gold += sell_val_1
        state.player.inventory.pouch.pop(0)

        assert state.player.gold == 15
        assert len(state.player.inventory.pouch) == 1

        # Sell item_expensive (now at index 0)
        sell_val_2 = max(5, state.player.inventory.pouch[0].gold_value // 2)
        assert sell_val_2 == 30
        state.player.gold += sell_val_2
        state.player.inventory.pouch.pop(0)

        assert state.player.gold == 45
        assert len(state.player.inventory.pouch) == 0


# =============================================================================
# 2. LOOT COLLECTION CHARACTERIZATION
# =============================================================================

class TestLootCharacterization:
    """Characterizes loot collection and transitions currently in `src/ui/views/loot.py`."""

    def test_take_loot_single_success(self):
        """Taking an item moves it from pending_loot into pouch."""
        state = GameState()
        state.player = create_mock_player()
        item1 = create_test_item("loot_1")
        item2 = create_test_item("loot_2")
        state.pending_loot = [item1, item2]

        # Take index 0
        target = state.pending_loot[0]
        if state.player.inventory.add_to_pouch(target):
            state.pending_loot.pop(0)

        assert len(state.player.inventory.pouch) == 1
        assert state.player.inventory.pouch[0].id == "loot_1"
        assert len(state.pending_loot) == 1
        assert state.pending_loot[0].id == "loot_2"

    def test_take_loot_when_pouch_full(self):
        """Taking loot when pouch is full fails and item stays in pending_loot."""
        state = GameState()
        state.player = create_mock_player()
        for i in range(10):
            state.player.inventory.pouch.append(create_test_item(f"fill_{i}"))

        item = create_test_item("leftover")
        state.pending_loot = [item]

        added = state.player.inventory.add_to_pouch(state.pending_loot[0])
        if added:
            state.pending_loot.pop(0)

        assert not added
        assert len(state.pending_loot) == 1
        assert state.pending_loot[0].id == "leftover"

    def test_exit_loot_flow_precedence(self):
        """Exit flow evaluates promotion -> ability choices -> next floor in strict priority."""
        state = GameState()
        # Must be level 10 to have available promotions
        state.player = create_mock_player(level=10)

        # Case A: Promotion is due
        state.player.promotion_due = True
        state.player.pending_ability_choices = ["STANDARD"]
        assert state.player.promotion_due
        assert len(state.player.available_promotions()) > 0

        # If promotion due, it initiates promotion
        did_promote = state.begin_promotion(GameMode.LOOT)
        assert did_promote is True
        assert state.current_mode == GameMode.PROMOTION

        # Case B: No promotion due, but pending ability choices exist
        state.current_mode = GameMode.LOOT
        state.player.promotion_due = False
        assert bool(state.player.pending_ability_choices)
        if not state.player.promotion_due and state.player.pending_ability_choices:
            state.switch_mode(GameMode.ABILITY_CHOICE)
        assert state.current_mode == GameMode.ABILITY_CHOICE


# =============================================================================
# 3. ABILITY DRAFT CHARACTERIZATION
# =============================================================================

class TestAbilityDraftCharacterization:
    """Characterizes ability selection, limits, and replacement in `src/ui/views/ability_choice.py`."""

    def test_add_ability_under_limit(self):
        """Passives are added directly if slots are open (< 2 passive)."""
        player = create_mock_player("warrior")
        assert len(player.abilities.passive) == 0  # starts with 0 passives

        new_passive = ABILITY_REGISTRY["iron_skin"]
        assert new_passive.ability_type == AbilityType.PASSIVE

        success = player.abilities.add_ability(new_passive)
        assert success is True
        assert len(player.abilities.passive) == 1
        assert player.abilities.passive[0].id == "iron_skin"

    def test_add_ability_over_limit_requires_replacement(self):
        """When category slots are full (2/2), add_ability returns False."""
        player = create_mock_player("warrior")
        player.abilities.passive = [
            ABILITY_REGISTRY["iron_skin"],
            ABILITY_REGISTRY["bloodlust"],
        ]
        assert len(player.abilities.passive) == 2

        new_passive = ABILITY_REGISTRY["veterans_instincts"]
        added = player.abilities.add_ability(new_passive)
        assert added is False

        # Replace slot 0
        player.abilities.replace_ability(new_passive, 0)
        assert player.abilities.passive[0].id == "veterans_instincts"
        assert player.abilities.passive[1].id == "bloodlust"

    def test_skip_ability_choice_consumes_pending_token(self):
        """Skipping an ability choice consumes the choice token without mutating abilities."""
        player = create_mock_player("warrior")
        player.pending_ability_choices = ["STANDARD", "EPIC"]
        initial_actives = list(player.abilities.active)

        # Skip choice:
        player.pending_ability_choices.pop(0)

        assert player.pending_ability_choices == ["EPIC"]
        assert player.abilities.active == initial_actives


# =============================================================================
# 4. PROMOTION CHARACTERIZATION
# =============================================================================

class TestPromotionCharacterization:
    """Characterizes affinity scoring and promotion in `src/ui/views/promotion.py`."""

    def test_recommended_class_by_ability_affinities(self):
        """Recommendation chooses the available promotion with highest ability affinity count."""
        player = create_mock_player("warrior", level=10)
        promotions = player.available_promotions()  # ["paladin", "berserker"]
        assert "paladin" in promotions and "berserker" in promotions

        # Paladin affinities
        shield_bash = ABILITY_REGISTRY["shield_bash"]
        assert "paladin" in shield_bash.affinities
        player.abilities.active = [shield_bash]

        # Calculate scores as done in PromotionView._recommended_class:
        scores = {cid: 0 for cid in promotions}
        for ability in (*player.abilities.active, *player.abilities.passive):
            for cid in promotions:
                scores[cid] += ability.affinities.count(cid)

        recommended = max(promotions, key=lambda cid: (scores[cid], -promotions.index(cid)))
        assert recommended == "paladin"
