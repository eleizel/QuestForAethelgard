import os
import pygame
from src.core.session import GameSession
from src.core.game_state import GameMode
from src.data.events import get_random_event
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.events import PygameEventsView

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
renderer = PygameRenderer()
surface = pygame.Surface((960, 540))

artifact_dir = "C:/Users/Sergio/.gemini/antigravity/brain/b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

# 1. Decision State: Event with choices (Scholar / Shrine)
s1 = GameSession()
s1.start_new_game(class_id="warrior")
s1.switch_mode(GameMode.EVENTS)
# Find an event with multiple choices
event_scholar = None
for _ in range(50):
    ev = get_random_event("cathedral")
    if ev and len(ev.choices) >= 2:
        event_scholar = ev
        break

s1.state.current_event = event_scholar
view1 = PygameEventsView()
view1.update(0.016, s1)
view1.draw(surface, renderer, s1)
p1 = os.path.join(artifact_dir, "event_view_decision.png")
pygame.image.save(surface, p1)
print(f"Saved {p1}")

# 2. Resolved State: Execute choice 1 and render outcome
s2 = GameSession()
s2.start_new_game(class_id="warrior")
s2.player.gold = 100
s2.switch_mode(GameMode.EVENTS)
ev_resolved = get_random_event("cathedral")
s2.state.current_event = ev_resolved
view2 = PygameEventsView()
# Trigger choice 0
view2.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), s2)
view2.update(0.016, s2)
view2.draw(surface, renderer, s2)
p2 = os.path.join(artifact_dir, "event_view_resolved.png")
pygame.image.save(surface, p2)
print(f"Saved {p2}")

# 3. Shrine Encounter Scene
s3 = GameSession()
s3.start_new_game(class_id="paladin")
s3.switch_mode(GameMode.EVENTS)
for _ in range(50):
    ev = get_random_event("cathedral")
    if ev and ev.scene_type in ("SHRINE", "ALTAR"):
        s3.state.current_event = ev
        break
view3 = PygameEventsView()
view3.update(0.016, s3)
view3.draw(surface, renderer, s3)
p3 = os.path.join(artifact_dir, "event_view_shrine.png")
pygame.image.save(surface, p3)
print(f"Saved {p3}")

# 4. Forge Encounter Scene
s4 = GameSession()
s4.start_new_game(class_id="warrior")
s4.state.current_biome = "foundry"
s4.switch_mode(GameMode.EVENTS)
for _ in range(100):
    ev = get_random_event("foundry")
    if ev and ev.scene_type == "FORGE":
        s4.state.current_event = ev
        break
view4 = PygameEventsView()
view4.update(0.016, s4)
view4.draw(surface, renderer, s4)
p4 = os.path.join(artifact_dir, "event_view_forge.png")
pygame.image.save(surface, p4)
print(f"Saved {p4}")

# 5. Rest Sanctuary Node (Simple Notification)
s5 = GameSession()
s5.start_new_game(class_id="rogue")
s5.switch_mode(GameMode.EVENTS)
s5.state.current_event = None
s5.state.current_event_text = "You discover a secluded sanctuary undisturbed by the ruins. Resting by the hearth restores 60 HP."
view5 = PygameEventsView()
view5.update(0.016, s5)
view5.draw(surface, renderer, s5)
p5 = os.path.join(artifact_dir, "event_view_rest.png")
pygame.image.save(surface, p5)
print(f"Saved {p5}")
