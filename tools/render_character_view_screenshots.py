import os
import pygame
from src.core.session import GameSession
from src.core.game_state import GameMode
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.character_modal import PygameCharacterModalView
from src.frontends.pygame_ce.views.map_view import PygameMapView
from src.systems.progression_service import ProgressionService
from src.data.abilities import get_ability_by_id

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
renderer = PygameRenderer()
surface = pygame.Surface((960, 540))

artifact_dir = "C:/Users/Sergio/.gemini/antigravity/brain/b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# 1. Character View - Warrior Lv.4
s1 = GameSession()
s1.start_new_game(class_id="warrior")
s1.player.level = 4
s1.player.gold = 150
s1.player.experience = 45
s1.player.stat_points = 2
ab_passive = get_ability_by_id("iron_skin")
if ab_passive:
    s1.player.abilities.add_ability(ab_passive)

# Underlay map view
map_view = PygameMapView()
map_view.draw(surface, renderer, s1)

char_view = PygameCharacterModalView()
char_view.update(0.016, s1)
char_view.draw(surface, renderer, s1)

p1 = os.path.join(artifact_dir, "character_view_warrior.png")
pygame.image.save(surface, p1)
print(f"Saved {p1}")

# 2. Character View - Paladin Lv.10
s2 = GameSession()
s2.start_new_game(class_id="warrior")
s2.player.gain_experience(6000)
ProgressionService.promote_class(s2.player, "paladin")
s2.player.gold = 520
s2.player.stat_points = 4
blade_storm = get_ability_by_id("blade_storm")
if blade_storm:
    s2.player.abilities.replace_ability(blade_storm, 0)
vets = get_ability_by_id("veterans_instincts")
if vets:
    s2.player.abilities.add_ability(vets)

map_view.draw(surface, renderer, s2)
char_view.draw(surface, renderer, s2)

p2 = os.path.join(artifact_dir, "character_view_paladin.png")
pygame.image.save(surface, p2)
print(f"Saved {p2}")

# 3. Character View - Rogue Lv.7
s3 = GameSession()
s3.start_new_game(class_id="rogue")
s3.player.level = 7
s3.player.gold = 340
s3.player.experience = 110
s3.state.current_biome = "ossuary"
nimble = get_ability_by_id("nimble_reflexes")
if nimble:
    s3.player.abilities.add_ability(nimble)

map_view.draw(surface, renderer, s3)
char_view.draw(surface, renderer, s3)

p3 = os.path.join(artifact_dir, "character_view_rogue.png")
pygame.image.save(surface, p3)
print(f"Saved {p3}")
