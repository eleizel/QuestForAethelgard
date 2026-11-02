"""Render Combat View screenshots across various biomes and enemies to verify aesthetics."""

import os
import sys
import pygame
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
ARTIFACT_DIR = r"C:\Users\Sergio\.gemini\antigravity\brain\b858e7d8-01ae-40cd-9d47-c3f8b985bfb9"

from src.core.session import GameSession
from src.core.game_state import GameState, GameMode
from src.entities.actor import Stats
from src.entities.player import Player
from src.entities.enemy import Enemy, EnemyTier
from src.entities.item import ConsumableItem
from src.data.enemies import ENEMY_CATALOG
from src.systems.combat import CombatSystem
from src.systems.status import create_poison, create_haste, create_bleed, create_burn, create_fortify
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.combat_view import PygameCombatView, FloatingNumber

def render_combat_screenshot(biome: str, enemy_id: str, class_id: str, filename: str):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    surface = pygame.Surface((960, 540))
    renderer = PygameRenderer()
    combat_view = PygameCombatView()

    # Create Player & Enemy
    player = Player(name="Sir Aethelgard", class_id=class_id)
    player.current_hp = 105
    player.gold = 462
    player.level = 10
    player.experience = 223
    player.exp_to_next_level = 752

    # Add belt items
    player.inventory.belt[0] = ConsumableItem(id="potion_health", name="Health Potion", description="Heals 35 HP", heal_amount=35)
    player.inventory.belt[1] = ConsumableItem(id="potion_mana", name="Mana Potion", description="Restores mana", heal_amount=20)
    player.inventory.belt[2] = ConsumableItem(id="herb", name="Antidote Herb", description="Cleanses poison", heal_amount=15)

    # Add active status effects
    player.apply_status(create_haste(duration=8, potency=4))
    player.apply_status(create_fortify(duration=12, potency=5))

    arch = ENEMY_CATALOG.get(enemy_id)
    if arch:
        e_stats = Stats(max_hp=arch.base_hp, attack=arch.base_atk, defense=arch.base_def, speed=arch.base_spd, crit_chance=arch.base_crit)
        enemy = Enemy(name=arch.name, stats=e_stats, tier=EnemyTier.COMMON, floor_level=6, exp_reward=50, gold_reward=10, archetype_id=arch.id)
    else:
        e_stats = Stats(max_hp=40, attack=8, defense=5, speed=18, crit_chance=0.05)
        enemy = Enemy(name="Thornvein Creeper", stats=e_stats, tier=EnemyTier.COMMON, floor_level=6, exp_reward=50, gold_reward=10, archetype_id="thornvein_creeper")

    enemy.current_hp = max(7, enemy.max_hp // 3)
    enemy.apply_status(create_poison(duration=5, potency=2))
    enemy.apply_status(create_bleed(duration=4, potency=3))

    combat = CombatSystem(player, enemy)
    combat.player_gauge = 62.0
    combat.enemy_gauge = 44.0
    combat.combat_logs = [
        f"Battle commenced: {player.name} vs {enemy.name}!",
        f"{player.name} strikes {enemy.name} for 33 dmg!",
        f"{enemy.name} suffers 1 poison dmg!",
    ]

    session = GameSession()
    session.state.player = player
    session.state.current_biome = biome
    session.state.floor = 6
    session.state.mode = GameMode.COMBAT
    session.state.combat = combat

    # Add popups
    combat_view.popups = [
        FloatingNumber(x=280, y=120, text="-33!", color=(255, 236, 39)),
        FloatingNumber(x=690, y=110, text="-1", color=(80, 240, 100)),
    ]

    # Draw view
    combat_view.draw(surface, renderer, session)

    # Save artifact
    out_path = os.path.join(ARTIFACT_DIR, filename)
    pygame.image.save(surface, out_path)
    print(f"Saved combat screenshot to: {out_path}")
    pygame.quit()

if __name__ == "__main__":
    render_combat_screenshot("arboretum", "thornvein_creeper", "warrior", "combat_view_arboretum_warrior.png")
    render_combat_screenshot("cathedral", "blind_archbishop", "mage", "combat_view_cathedral_mage.png")
    render_combat_screenshot("ossuary", "scylla_bone_weaver", "rogue", "combat_view_ossuary_rogue.png")
    render_combat_screenshot("sanctum", "high_lord_carmilla", "paladin", "combat_view_sanctum_paladin.png")
