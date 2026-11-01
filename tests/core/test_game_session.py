"""Unit tests for GameSession Facade."""

import pytest
from src.core.session import GameSession
from src.core.commands import (
    BuyItemCommand,
    SellItemCommand,
    TakeLootCommand,
    TakeAllLootCommand,
    ChooseAbilityCommand,
    SkipAbilityDraftCommand,
    PromoteClassCommand,
)
from src.core.game_state import GameMode
from src.core.persistence import MemoryStorageBackend
from src.core.save_manager import SaveManager
from src.entities.item import Item, ItemType
from src.data.abilities import ABILITY_REGISTRY


def create_session() -> GameSession:
    mem_storage = MemoryStorageBackend()
    save_mgr = SaveManager(storage=mem_storage)
    session = GameSession(save_mgr=save_mgr)
    session.start_new_game(class_id="warrior")
    return session


def test_session_state_delegation():
    """GameSession delegates mode queries and transitions to internal GameState and FSM."""
    session = create_session()
    assert session.player.name == "Sir Aethelgard"
    assert session.player.class_id == "warrior"

    session.switch_mode(GameMode.MAP)
    assert session.current_mode == GameMode.MAP
    assert session.can_open_overlay() is True

    session.toggle_inventory()
    assert session.current_mode == GameMode.INVENTORY

    session.toggle_inventory()
    assert session.current_mode == GameMode.MAP


def test_session_persistence_lifecycle():
    """GameSession save/load operates cleanly via pluggable SaveManager."""
    session = create_session()
    session.state.floor = 4
    session.player.gold = 300

    assert session.has_saved_game() is False
    assert session.save_game() is True
    assert session.has_saved_game() is True

    # Mutate live session
    session.state.floor = 99
    session.player.gold = 0

    assert session.load_game() is True
    assert session.state.floor == 4
    assert session.player.gold == 300

    assert session.delete_save() is True
    assert session.has_saved_game() is False


def test_session_dispatch_shop_commands():
    """Dispatching Buy and Sell commands successfully processes transactions through ShopService."""
    session = create_session()
    session.player.gold = 100
    session.player.inventory.pouch.clear()

    item = Item(id="test_gem", name="Gem", description="Shiny", item_type=ItemType.MATERIAL, gold_value=40)
    session.state.merchant_stock = [(item, 50)]

    # Buy
    res = session.dispatch(BuyItemCommand(stock_index=0))
    assert res.success is True
    assert session.player.gold == 50
    assert len(session.player.inventory.pouch) == 1
    assert len(session.state.merchant_stock) == 0

    # Sell
    res_sell = session.dispatch(SellItemCommand(pouch_index=0))
    assert res_sell.success is True
    assert session.player.gold == 70  # 50 + max(5, 40 // 2) = 70
    assert len(session.player.inventory.pouch) == 0


def test_session_dispatch_loot_commands():
    """Dispatching TakeLoot and TakeAllLoot commands transfers loot through LootService."""
    session = create_session()
    session.player.inventory.pouch.clear()
    l1 = Item(id="l1", name="Loot 1", description="D", item_type=ItemType.MATERIAL)
    l2 = Item(id="l2", name="Loot 2", description="D", item_type=ItemType.MATERIAL)
    session.state.pending_loot = [l1, l2]

    # Take single
    res1 = session.dispatch(TakeLootCommand(loot_index=0))
    assert res1.success is True
    assert len(session.player.inventory.pouch) == 1
    assert len(session.state.pending_loot) == 1

    # Take all remaining
    res2 = session.dispatch(TakeAllLootCommand())
    assert res2.success is True
    assert len(session.player.inventory.pouch) == 2
    assert len(session.state.pending_loot) == 0


def test_session_dispatch_draft_and_promote_commands():
    """Dispatching ChooseAbility and PromoteClass routes through Draft and Progression services."""
    session = create_session()
    session.player.pending_ability_choices = ["STANDARD"]
    session.player.level = 10

    iron_skin = ABILITY_REGISTRY["iron_skin"]
    res_draft = session.dispatch(ChooseAbilityCommand(ability=iron_skin))
    assert res_draft.success is True
    assert session.player.pending_ability_choices == []
    assert any(a.id == "iron_skin" for a in session.player.abilities.passive)

    res_promote = session.dispatch(PromoteClassCommand(class_id="paladin"))
    assert res_promote.success is True
    assert session.player.class_id == "paladin"
