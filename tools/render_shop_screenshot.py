import os
import pygame
from src.core.session import GameSession
from src.core.game_state import GameMode
from src.entities.item import EquipmentItem, EquipSlot
from src.entities.actor import Stats
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.shop import PygameShopView

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
renderer = PygameRenderer()
surface = pygame.Surface((960, 540))

artifact_dir = "C:/Users/Sergio/.gemini/antigravity/brain/b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

session = GameSession()
session.start_new_game(class_id="warrior")
session.player.gold = 150
session.switch_mode(GameMode.SHOP)

# Stock items
item1 = EquipmentItem(
    id="silver_broadsword",
    name="Silver Broadsword",
    description="A gleaming blade tempered in celestial flame. Cuts through darkness.",
    gold_value=60,
    slot=EquipSlot.MAIN_HAND,
    stats_bonus=Stats(max_hp=0, attack=5, defense=0, speed=1, crit_chance=0.05),
    tier=3,
)
item2 = EquipmentItem(
    id="quicksilver_sabatons",
    name="Quicksilver Sabatons",
    description="Lightweight greaves forged from liquid metal. Enhances swift footwork.",
    gold_value=45,
    slot=EquipSlot.LEGS,
    stats_bonus=Stats(max_hp=0, attack=1, defense=3, speed=4, crit_chance=0.0),
    tier=2,
)
item3 = EquipmentItem(
    id="aegis_bulwark",
    name="Aegis Bulwark",
    description="Heavy tower shield embossed with the sovereign crest.",
    gold_value=85,
    slot=EquipSlot.OFF_HAND,
    stats_bonus=Stats(max_hp=20, attack=0, defense=7, speed=-1, crit_chance=0.0),
    tier=4,
)
from src.entities.item import ConsumableItem
item4 = ConsumableItem(
    id="item_potion_health",
    name="Greater Health Elixir",
    description="A concentrated crimson brew that restores vital life energy.",
    gold_value=25,
    heal_amount=120,
)
session.state.merchant_stock = [(item1, 60), (item2, 45), (item3, 85), (item4, 25)]

view = PygameShopView()
view.update(0.016, session)
view.draw(surface, renderer, session)
p = os.path.join(artifact_dir, "shop_view_buy.png")
pygame.image.save(surface, p)
print(f"Saved {p}")

# Switch to SELL tab and render
session.player.inventory.pouch.append(item2)
view.active_tab = "SELL"
view.update(0.016, session)
view.draw(surface, renderer, session)
p_sell = os.path.join(artifact_dir, "shop_view_sell.png")
pygame.image.save(surface, p_sell)
print(f"Saved {p_sell}")
