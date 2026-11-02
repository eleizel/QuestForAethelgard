import os
import pygame
from src.core.session import GameSession
from src.core.game_state import GameMode
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.ability_choice import PygameAbilityChoiceView
from src.frontends.pygame_ce.views.promotion import PygamePromotionView
from src.systems.progression_service import ProgressionService
from src.systems.abilities import AbilityType

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
renderer = PygameRenderer()
surface = pygame.Surface((960, 540))

artifact_dir = "C:/Users/Sergio/.gemini/antigravity/brain/b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# 1. Level 4 Standard Ability Draft View
s1 = GameSession()
s1.start_new_game(class_id="warrior")
s1.player.level = 4
s1.player.pending_ability_choices = ["STANDARD"]
s1.switch_mode(GameMode.ABILITY_CHOICE)

draft_view = PygameAbilityChoiceView()
draft_view.update(0.016, s1)
draft_view.draw(surface, renderer, s1)
p1 = os.path.join(artifact_dir, "ability_choice_standard.png")
pygame.image.save(surface, p1)
print(f"Saved {p1}")

# 2. Level 10 Class Promotion View (Warrior -> Paladin / Berserker)
s2 = GameSession()
s2.start_new_game(class_id="warrior")
s2.player.level = 10
s2.player.promotion_due = True
s2.switch_mode(GameMode.PROMOTION)

promo_view = PygamePromotionView()
promo_view.update(0.016, s2)
promo_view.draw(surface, renderer, s2)
p2 = os.path.join(artifact_dir, "promotion_view_warrior.png")
pygame.image.save(surface, p2)
print(f"Saved {p2}")

# 3. Level 10 Class Promotion View (Rogue -> Venomancer / Duelist)
s3 = GameSession()
s3.start_new_game(class_id="rogue")
s3.player.level = 10
s3.player.promotion_due = True
s3.switch_mode(GameMode.PROMOTION)

promo_view_rogue = PygamePromotionView()
promo_view_rogue.selected_index = 1
promo_view_rogue.update(0.016, s3)
promo_view_rogue.draw(surface, renderer, s3)
p3 = os.path.join(artifact_dir, "promotion_view_rogue.png")
pygame.image.save(surface, p3)
print(f"Saved {p3}")

# 4. Level 10 Epic Ability Draft View for Paladin
s4 = GameSession()
s4.start_new_game(class_id="warrior")
s4.player.level = 10
ProgressionService.promote_class(s4.player, "paladin")
s4.switch_mode(GameMode.ABILITY_CHOICE)

draft_epic = PygameAbilityChoiceView()
draft_epic.update(0.016, s4)
draft_epic.draw(surface, renderer, s4)
p4 = os.path.join(artifact_dir, "ability_choice_epic_paladin.png")
pygame.image.save(surface, p4)
print(f"Saved {p4}")

# 5. Replacement Mode UI Preview
s5 = GameSession()
s5.start_new_game(class_id="warrior")
s5.player.level = 6
s5.player.pending_ability_choices = ["STANDARD"]
s5.switch_mode(GameMode.ABILITY_CHOICE)

draft_rep = PygameAbilityChoiceView()
draft_rep.update(0.016, s5)
# trigger replacement by picking an active ability when active slots full
if draft_rep.choices:
    draft_rep._handle_choice(s5, draft_rep.choices[0])
draft_rep.draw(surface, renderer, s5)
p5 = os.path.join(artifact_dir, "ability_choice_replacement.png")
pygame.image.save(surface, p5)
print(f"Saved {p5}")
