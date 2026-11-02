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
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.loot import PygameLootView

def render_loot():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    surface = pygame.Surface((960, 540))
    renderer = PygameRenderer()
    view = PygameLootView()

    player = Player(name="Sir Aethelgard", class_id="warrior")
    player.level = 5
    player.experience = 70
    player.exp_to_next_level = 222
    player.gold = 87
    player.current_hp = 110

    # Equip some boots to test stat difference
    equipped_boots = EquipmentItem(
        id="iron_greaves",
        name="Iron Greaves",
        description="Sturdy iron plates protecting the shins.",
        slot=EquipSlot.LEGS,
        stats_bonus=Stats(max_hp=0, attack=1, defense=2, speed=0, crit_chance=0.0),
        tier=1,
    )
    player.inventory.equipment[EquipSlot.LEGS] = equipped_boots

    # Pending loot matching design image:
    # 1. Health P. L (Consumable)
    pot = ConsumableItem(
        id="item_potion_health",
        name="Health P. L",
        description="Restores 180 health points.",
        heal_amount=180,
    )
    # 2. Quicksilver Sabatons (Legs, ATK +2, DEF +4)
    sab = EquipmentItem(
        id="quicksilver_sabatons",
        name="Quicksilver Sabatons",
        description="Greaves infused with liquid silver.",
        slot=EquipSlot.LEGS,
        stats_bonus=Stats(max_hp=0, attack=2, defense=4, speed=0, crit_chance=0.0),
        tier=2,
    )

    session = GameSession()
    session.state.player = player
    session.state.floor = 5
    session.state.current_biome = "arboretum"
    session.state.mode = GameMode.LOOT
    session.state.pending_loot = [pot, sab]
    session.state.last_exp_earned = 218
    session.state.last_gold_earned = 34

    view.draw(surface, renderer, session)

    out_path = os.path.join(ARTIFACT_DIR, "rewards_view_design_match.png")
    pygame.image.save(surface, out_path)
    print(f"Saved rewards screenshot to: {out_path}")

if __name__ == "__main__":
    render_loot()
