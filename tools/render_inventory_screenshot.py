import os
import sys
import pygame

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

from src.core.session import GameSession
from src.core.game_state import GameMode
from src.entities.actor import Stats
from src.entities.player import Player
from src.entities.item import EquipSlot, EquipmentItem, ConsumableItem
from src.data.items import StatPotion
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.inventory_modal import PygameInventoryModalView

def render_inventory():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    surface = pygame.Surface((960, 540))
    renderer = PygameRenderer()
    view = PygameInventoryModalView()

    player = Player(name="Sir Aethelgard", class_id="warrior")
    player.level = 7
    player.experience = 180
    player.exp_to_next_level = 420
    player.gold = 350
    player.current_hp = 115

    # Equip several items
    player.inventory.equipment[EquipSlot.HEAD] = EquipmentItem(
        id="iron_helm",
        name="Iron Greathelm",
        description="A heavy visage of forged iron offering solid defense.",
        slot=EquipSlot.HEAD,
        stats_bonus=Stats(max_hp=10, attack=0, defense=4, speed=-1, crit_chance=0.0),
        tier=1,
    )
    player.inventory.equipment[EquipSlot.CHEST] = EquipmentItem(
        id="iron_cuirass",
        name="Plate Cuirass",
        description="Thick banded steel breastplate protecting vital organs.",
        slot=EquipSlot.CHEST,
        stats_bonus=Stats(max_hp=25, attack=0, defense=8, speed=-2, crit_chance=0.0),
        tier=2,
    )
    player.inventory.equipment[EquipSlot.MAIN_HAND] = EquipmentItem(
        id="broadsword",
        name="Steel Broadsword",
        description="A razor sharp knightly broadsword.",
        slot=EquipSlot.MAIN_HAND,
        stats_bonus=Stats(max_hp=0, attack=8, defense=1, speed=0, crit_chance=0.05),
        tier=2,
    )
    player.inventory.equipment[EquipSlot.LEGS] = EquipmentItem(
        id="quicksilver_sabatons",
        name="Quicksilver Sabatons",
        description="Greaves infused with liquid silver for swift footing.",
        slot=EquipSlot.LEGS,
        stats_bonus=Stats(max_hp=0, attack=2, defense=4, speed=2, crit_chance=0.0),
        tier=3,
    )

    # Belt items
    player.inventory.belt[0] = ConsumableItem(
        id="item_potion_health",
        name="Health Potion",
        description="Restores 35 HP instantly in battle or on the trail.",
        heal_amount=35,
    )
    player.inventory.belt[1] = StatPotion(
        id="item_potion_mana",
        name="Elixir of Might",
        description="Permanently elevates base attack by 2.",
        stat_bonus=Stats(max_hp=0, attack=2, defense=0, speed=0, crit_chance=0.0),
    )

    # Pouch items
    player.inventory.pouch.append(EquipmentItem(
        id="bastion_shield",
        name="Bastion Buckler",
        description="A reinforced tower shield capable of repelling heavy strikes.",
        slot=EquipSlot.OFF_HAND,
        stats_bonus=Stats(max_hp=15, attack=0, defense=6, speed=-1, crit_chance=0.0),
        tier=3,
    ))
    player.inventory.pouch.append(EquipmentItem(
        id="flame_blade",
        name="Searing Claymore",
        description="A massive two-handed greatsword imbued with fire essences.",
        slot=EquipSlot.MAIN_HAND,
        stats_bonus=Stats(max_hp=0, attack=14, defense=0, speed=-2, crit_chance=0.10),
        tier=4,
    ))
    player.inventory.pouch.append(ConsumableItem(
        id="item_potion_health_l",
        name="Health P. L",
        description="A large draught of healing draught healing 180 HP.",
        heal_amount=180,
    ))

    session = GameSession()
    session.state.player = player
    session.state.floor = 7
    session.state.current_biome = "arboretum"
    session.state.mode = GameMode.INVENTORY

    # Active pane: POUCH, cursor: 1 (Searing Claymore selected to view comparison vs Steel Broadsword!)
    view.active_pane = "POUCH"
    view.pouch_cursor = 1

    view.draw(surface, renderer, session)

    out_path = os.path.join(ARTIFACT_DIR, "inventory_view_inspection.png")
    pygame.image.save(surface, out_path)
    print(f"Saved inventory screenshot to: {out_path}")

if __name__ == "__main__":
    render_inventory()
