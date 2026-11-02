"""Comprehensive test suite for Pygame-CE frontend client covering all 14 game screens."""

from __future__ import annotations

import os
import pytest
import pygame

from src.core.events import AudioCue, AudioCueEvent, DamageDealtEvent, event_bus
from src.core.game_state import GameMode
from src.core.session import GameSession
from src.core.theme import ThemeToken
from src.entities.item import EquipmentItem, EquipSlot
from src.entities.actor import Stats
from src.entities.enemy import Enemy, EnemyTier
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.asset_manager import assets
from src.frontends.pygame_ce.views.welcome import PygameWelcomeView
from src.frontends.pygame_ce.views.class_select import PygameClassSelectView
from src.frontends.pygame_ce.views.biome_select import PygameBiomeSelectView
from src.frontends.pygame_ce.views.map_view import PygameMapView
from src.frontends.pygame_ce.views.combat_view import PygameCombatView
from src.frontends.pygame_ce.views.loot import PygameLootView
from src.frontends.pygame_ce.views.shop import PygameShopView
from src.frontends.pygame_ce.views.ability_choice import PygameAbilityChoiceView
from src.frontends.pygame_ce.views.promotion import PygamePromotionView
from src.frontends.pygame_ce.views.events import PygameEventsView
from src.frontends.pygame_ce.views.inventory_modal import PygameInventoryModalView
from src.frontends.pygame_ce.views.character_modal import PygameCharacterModalView
from src.frontends.pygame_ce.views.end_game import PygameEndGameView
from src.frontends.pygame_ce.views.credits import PygameCreditsView


@pytest.fixture(scope="module", autouse=True)
def setup_headless_sdl():
    """Ensure headless SDL environment for testing."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    yield


def test_asset_manager_loads_snes_backgrounds_and_sprites():
    """Verify AssetManager loads all 9 backgrounds and extracts sprites."""
    assert len(assets.background_surfaces) >= 9
    assert assets.get_background("welcome") is not None
    assert assets.get_background("cathedral") is not None
    assert assets.get_class_portrait("warrior", scale=2) is not None
    assert assets.get_enemy_sprite("cathedral_imp", scale=3) is not None


def test_pygame_welcome_view():
    session = GameSession()
    view = PygameWelcomeView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), session)
    assert session.current_mode == GameMode.CLASS_SELECT

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_class_select_view():
    session = GameSession()
    view = PygameClassSelectView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b), session)
    assert view.route_mode == "PATHFINDER"

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3), session)
    assert view.selected_class_id == "mage"

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), session)
    assert session.current_mode == GameMode.BIOME_SELECT
    assert session.player.class_id == "mage"

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_biome_select_view():
    session = GameSession()
    session.start_new_game(class_id="warrior", route_mode="PATHFINDER")
    session.switch_mode(GameMode.BIOME_SELECT)

    view = PygameBiomeSelectView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2), session)
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), session)

    assert session.current_mode == GameMode.MAP
    assert session.state.current_biome == "cathedral"

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_map_view():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.switch_mode(GameMode.MAP)

    view = PygameMapView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i), session)
    assert session.current_mode == GameMode.INVENTORY
    session.toggle_inventory()

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), session)
    assert session.current_mode in (GameMode.COMBAT, GameMode.EVENTS, GameMode.SHOP)

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_combat_view_and_qte():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    from src.systems.combat import CombatSystem
    stats = Stats(max_hp=40, attack=6, defense=2, speed=8, crit_chance=0.05)
    dummy_enemy = Enemy(name="Goblin", stats=stats, tier=EnemyTier.COMMON, floor_level=1, exp_reward=10, gold_reward=5)
    session.state.combat = CombatSystem(session.player, dummy_enemy)
    session.switch_mode(GameMode.COMBAT)

    view = PygameCombatView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), session)
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z), session)
    assert view.step_interval < 0.3

    view.update(0.05, session)
    view.draw(surface, renderer, session)

    # Test QTE sequence lifecycle and rendering
    combat = session.state.combat
    qte = combat.start_qte_sequence(count=3)
    assert combat.is_qte_active()
    assert qte.in_intro

    # Draw during intro
    view.draw(surface, renderer, session)

    # Skip intro with SPACE
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), session)
    assert not qte.in_intro

    # Draw during active button target
    view.draw(surface, renderer, session)

    # Resolve target button
    cur_target = qte.current_target
    assert cur_target is not None
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), session)
    assert cur_target.resolved

    # Update through feedback pause
    cur_target.feedback_frames = 0
    view.update(0.016, session)
    assert qte.current_index == 1


def test_pygame_loot_view():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.switch_mode(GameMode.LOOT)

    test_sword = EquipmentItem(
        id="test_sword",
        name="Steel Longsword",
        description="A sharp steel blade",
        gold_value=30,
        slot=EquipSlot.MAIN_HAND,
        stats_bonus=Stats(max_hp=0, attack=10, defense=2, speed=0, crit_chance=0.0),
        tier=2,
    )
    session.state.pending_loot = [test_sword]

    view = PygameLootView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), session)
    assert test_sword in session.player.inventory.pouch or test_sword in session.player.inventory.equipment.values()

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_shop_view():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.player.gold = 100
    session.switch_mode(GameMode.SHOP)

    test_pot = EquipmentItem(
        id="test_pot",
        name="Healing Tonic",
        description="Restores vital health",
        gold_value=20,
        slot=EquipSlot.MAIN_HAND,
        stats_bonus=Stats(max_hp=10, attack=0, defense=0, speed=0, crit_chance=0.0),
    )
    session.state.merchant_stock = [(test_pot, 20)]

    view = PygameShopView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), session)
    assert session.player.gold < 100

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_ability_choice_view():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.switch_mode(GameMode.ABILITY_CHOICE)

    from src.data.abilities import get_ability_by_id
    ab1 = get_ability_by_id("cleave")
    session.state.offered_abilities = [ab1] if ab1 else []

    view = PygameAbilityChoiceView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    if session.state.offered_abilities:
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), session)

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_promotion_view():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.player.level = 10
    session.switch_mode(GameMode.PROMOTION)

    view = PygamePromotionView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1), session)
    view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), session)

    assert session.player.class_id == "paladin"

    view.update(0.016, session)
    view.draw(surface, renderer, session)


def test_pygame_inventory_and_character_modals():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    test_helm = EquipmentItem(
        id="test_helm",
        name="Iron Helm",
        description="Sturdy iron helmet",
        gold_value=15,
        slot=EquipSlot.HEAD,
        stats_bonus=Stats(max_hp=5, attack=0, defense=3, speed=0, crit_chance=0.0),
    )
    session.player.inventory.pouch.append(test_helm)

    inv_view = PygameInventoryModalView()
    inv_view.draw(surface, renderer, session)

    # Equip via key '1' (first pouch slot)
    first_pouch_idx = len(session.player.inventory.pouch) - 1
    # Trigger mouse click on the pouch item
    pouch_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(550, 130 + first_pouch_idx * 30 + 10))
    inv_view.handle_event(pouch_click, session)
    assert session.player.inventory.equipment[EquipSlot.HEAD] is not None
    assert session.player.inventory.equipment[EquipSlot.HEAD].id == "test_helm"

    # Unequip by clicking on HEAD slot (index 0 in EQUIP_SLOT_ORDER)
    head_slot_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(150, 130 + 10))
    inv_view.handle_event(head_slot_click, session)
    assert session.player.inventory.equipment[EquipSlot.HEAD] is None

    # Toggle modal closed
    inv_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i), session)

    char_view = PygameCharacterModalView()
    char_view.draw(surface, renderer, session)
    char_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c), session)


def test_pygame_end_game_and_credits_views():
    session = GameSession()
    session.start_new_game(class_id="warrior")
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    session.switch_mode(GameMode.GAME_OVER)
    end_view = PygameEndGameView()
    end_view.draw(surface, renderer, session)

    session.switch_mode(GameMode.CREDITS)
    cred_view = PygameCreditsView()
    cred_view.draw(surface, renderer, session)
    cred_view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), session)
    assert session.current_mode == GameMode.WELCOME


def test_pygame_app_lifecycle_all_modes():
    """Verify PygameApp correctly routes and updates all 14 game modes."""
    app = PygameApp(headless=True)
    for mode in GameMode:
        app.session.switch_mode(mode)
        active_view = app.get_active_view()
        assert active_view is not None
        app.update(0.016)
        app.draw()


def test_pygame_app_fullscreen_and_maximized_flags():
    """Verify PygameApp initializes with fullscreen and maximized options."""
    app_fs = PygameApp(headless=True, fullscreen=True)
    assert app_fs.fullscreen is True

    app_max = PygameApp(headless=True, maximized=True)
    assert app_max.maximized is True

    # Test F11 key handling
    app = PygameApp(headless=True)
    event_f11 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0)
    pygame.event.post(event_f11)
    app.handle_events()
