import os
import pygame
from src.core.session import GameSession
from src.core.game_state import GameMode
from src.entities.item import EquipmentItem, EquipSlot
from src.entities.actor import Stats
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.end_game import PygameEndGameView

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
renderer = PygameRenderer()
surface = pygame.Surface((960, 540))

artifact_dir = "C:/Users/Sergio/.gemini/antigravity/brain/b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# 1. Defeat Screen (Hero Defeated / Catacomb Altar)
s_defeat = GameSession()
s_defeat.start_new_game(class_id="warrior")
s_defeat.player.level = 6
s_defeat.player.gold = 320
s_defeat.state.act = 2
s_defeat.state.floor = 8
s_defeat.state.current_biome = "foundry"
s_defeat.switch_mode(GameMode.GAME_OVER)

view_defeat = PygameEndGameView()
view_defeat.update(0.016, s_defeat)
view_defeat.draw(surface, renderer, s_defeat)
p_def = os.path.join(artifact_dir, "end_game_view_defeat.png")
pygame.image.save(surface, p_def)
print(f"Saved {p_def}")

# 2. Victory Screen (Ascension Achieved / Celestial Shrine)
s_victory = GameSession()
s_victory.start_new_game(class_id="paladin")
s_victory.player.level = 10
s_victory.player.gold = 1450
s_victory.state.act = 3
s_victory.state.floor = 15
s_victory.state.current_biome = "sanctum"
s_victory.switch_mode(GameMode.VICTORY)

view_victory = PygameEndGameView()
view_victory.update(0.016, s_victory)
view_victory.draw(surface, renderer, s_victory)
p_vic = os.path.join(artifact_dir, "end_game_view_victory.png")
pygame.image.save(surface, p_vic)
print(f"Saved {p_vic}")
