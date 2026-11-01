"""Unit tests for Phase 2 Domain Services: ShopService, LootService, DraftService, ProgressionService."""

import pytest
from src.core.events import EventBus, AudioCue, AudioCueEvent
from src.core.game_state import GameMode
from src.entities.player import Player
from src.entities.item import Item, ItemType
from src.systems.shop_service import ShopService
from src.systems.loot_service import LootService
from src.systems.draft_service import DraftService
from src.systems.progression_service import ProgressionService
from src.data.abilities import ABILITY_REGISTRY, Ability, AbilityRarity, AbilityType


def create_player(class_id: str = "warrior", gold: int = 100, level: int = 1) -> Player:
    p = Player(class_id=class_id, name="Hero")
    p.gold = gold
    p.level = level
    p.inventory.pouch.clear()
    return p


def create_item(item_id: str = "iron_sword", gold_value: int = 30) -> Item:
    return Item(id=item_id, name="Test Item", description="Desc", item_type=ItemType.MATERIAL, gold_value=gold_value)


# =============================================================================
# ShopService Tests
# =============================================================================

class TestShopService:
    def test_calculate_sell_price(self):
        assert ShopService.calculate_sell_price(create_item(gold_value=6)) == 5   # clamped to 5
        assert ShopService.calculate_sell_price(create_item(gold_value=40)) == 20

    def test_buy_item_success(self):
        bus = EventBus()
        player = create_player(gold=50)
        stock = [(create_item("item1"), 30)]

        res = ShopService.buy_item(player, stock, 0, bus=bus)
        assert res.success is True
        assert player.gold == 20
        assert len(player.inventory.pouch) == 1
        assert len(stock) == 0

        # Audio click emitted
        events = bus.drain()
        assert any(isinstance(e, AudioCueEvent) and e.cue == AudioCue.CLICK for e in events)

    def test_buy_item_no_gold(self):
        bus = EventBus()
        player = create_player(gold=10)
        stock = [(create_item("item1"), 30)]

        res = ShopService.buy_item(player, stock, 0, bus=bus)
        assert res.success is False
        assert res.error_code == "NO_GOLD"
        assert player.gold == 10
        assert len(stock) == 1

    def test_buy_item_pouch_full(self):
        bus = EventBus()
        player = create_player(gold=100)
        for i in range(10):
            player.inventory.pouch.append(create_item(f"pouch_{i}"))

        stock = [(create_item("new_item"), 10)]
        res = ShopService.buy_item(player, stock, 0, bus=bus)
        assert res.success is False
        assert res.error_code == "POUCH_FULL"
        assert player.gold == 100
        assert len(stock) == 1

    def test_sell_item_success(self):
        bus = EventBus()
        player = create_player(gold=10)
        player.inventory.pouch.append(create_item("sellable", gold_value=60))

        res = ShopService.sell_item(player, 0, bus=bus)
        assert res.success is True
        assert player.gold == 40  # 10 + 30
        assert len(player.inventory.pouch) == 0


# =============================================================================
# LootService Tests
# =============================================================================

class TestLootService:
    def test_take_item_success(self):
        bus = EventBus()
        player = create_player()
        pending = [create_item("loot1")]

        res = LootService.take_item(player, pending, 0, bus=bus)
        assert res.success is True
        assert len(player.inventory.pouch) == 1
        assert len(pending) == 0
        events = bus.drain()
        assert any(isinstance(e, AudioCueEvent) and e.cue == AudioCue.CHEST for e in events)

    def test_take_item_pouch_full(self):
        bus = EventBus()
        player = create_player()
        for i in range(10):
            player.inventory.pouch.append(create_item(f"p_{i}"))
        pending = [create_item("loot1")]

        res = LootService.take_item(player, pending, 0, bus=bus)
        assert res.success is False
        assert res.error_code == "POUCH_FULL"
        assert len(pending) == 1

    def test_take_all(self):
        bus = EventBus()
        player = create_player()
        for i in range(8):
            player.inventory.pouch.append(create_item(f"p_{i}"))
        # 2 pouch slots free
        pending = [create_item("l1"), create_item("l2"), create_item("l3")]

        res = LootService.take_all(player, pending, bus=bus)
        assert res.payload["taken"] == 2
        assert res.payload["remaining"] == 1
        assert len(pending) == 1
        assert len(player.inventory.pouch) == 10

    def test_resolve_exit_mode(self):
        player = create_player(level=10)
        player.promotion_due = True
        assert LootService.resolve_exit_mode(player) == GameMode.PROMOTION

        player.promotion_due = False
        player.pending_ability_choices = ["STANDARD"]
        assert LootService.resolve_exit_mode(player) == GameMode.ABILITY_CHOICE

        player.pending_ability_choices = []
        assert LootService.resolve_exit_mode(player) is None


# =============================================================================
# DraftService Tests
# =============================================================================

class TestDraftService:
    def test_generate_draft_empty_when_no_tokens(self):
        player = create_player()
        player.pending_ability_choices = []
        assert DraftService.generate_draft(player) == []

    def test_generate_draft_with_token(self):
        player = create_player()
        player.pending_ability_choices = ["STANDARD"]
        draft = DraftService.generate_draft(player, count=2)
        assert len(draft) == 2

    def test_apply_selection_add_directly(self):
        bus = EventBus()
        player = create_player("warrior")
        player.pending_ability_choices = ["STANDARD"]
        passive = ABILITY_REGISTRY["iron_skin"]

        res = DraftService.apply_selection(player, passive, bus=bus, consume_token=True)
        assert res.success is True
        assert len(player.abilities.passive) == 1
        assert player.pending_ability_choices == []

    def test_apply_selection_requires_replace(self):
        bus = EventBus()
        player = create_player("warrior")
        player.pending_ability_choices = ["STANDARD"]
        player.abilities.passive = [
            ABILITY_REGISTRY["iron_skin"],
            ABILITY_REGISTRY["bloodlust"],
        ]
        new_passive = ABILITY_REGISTRY["veterans_instincts"]

        res = DraftService.apply_selection(player, new_passive, bus=bus, consume_token=True)
        assert res.success is False
        assert res.error_code == "REPLACE_REQUIRED"
        assert len(player.pending_ability_choices) == 1

        # Now replace slot 1
        res2 = DraftService.apply_selection(player, new_passive, replace_index=1, bus=bus, consume_token=True)
        assert res2.success is True
        assert player.abilities.passive[1].id == "veterans_instincts"
        assert player.pending_ability_choices == []

    def test_skip_draft(self):
        bus = EventBus()
        player = create_player()
        player.pending_ability_choices = ["STANDARD", "EPIC"]

        res = DraftService.skip_draft(player, bus=bus)
        assert res.success is True
        assert player.pending_ability_choices == ["EPIC"]


# =============================================================================
# ProgressionService Tests
# =============================================================================

class TestProgressionService:
    def test_recommendation_and_promotion(self):
        bus = EventBus()
        player = create_player("warrior", level=10)
        player.abilities.active = [ABILITY_REGISTRY["shield_bash"]]

        rec = ProgressionService.get_recommended_promotion(player)
        assert rec == "paladin"

        res = ProgressionService.promote_class(player, "paladin", bus=bus)
        assert res.success is True
        assert player.class_id == "paladin"
        events = bus.drain()
        assert any(isinstance(e, AudioCueEvent) and e.cue == AudioCue.VICTORY for e in events)
