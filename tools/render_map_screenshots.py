"""
Render visual screenshots of the redesigned PygameMapView across different classes and biomes.
"""

import os
import pygame

# Initialize headless pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

from src.core.session import GameSession
from src.core.game_state import GameMode
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.map_view import PygameMapView

ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

cases = [
    ("warrior", "arboretum", 1, 6, "map_view_arboretum_warrior.png"),
    ("mage", "cathedral", 1, 3, "map_view_cathedral_mage.png"),
    ("rogue", "ossuary", 2, 14, "map_view_ossuary_rogue.png"),
    ("paladin", "sanctum", 3, 28, "map_view_sanctum_paladin.png"),
]

for class_id, biome, act, floor, filename in cases:
    session = GameSession()
    session.start_new_game(class_id=class_id)
    session.state.act = act
    session.state.floor = floor
    session.state.current_biome = biome
    session.player.gold = 462
    session.player.experience = 223
    session.player.exp_to_next_level = 752
    session.player.level = 10
    session.switch_mode(GameMode.MAP)

    view = PygameMapView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.update(0.016, session)
    view.draw(surface, renderer, session)

    out_path = os.path.join(ARTIFACT_DIR, filename)
    pygame.image.save(surface, out_path)
    print(f"Saved screenshot: {out_path}")
