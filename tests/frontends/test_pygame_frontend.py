"""Unit test suite for the Pygame-CE frontend client."""

from __future__ import annotations

import os
import pytest
import pygame

from src.core.events import AudioCue, AudioCueEvent, DamageDealtEvent, event_bus
from src.core.game_state import GameMode
from src.core.session import GameSession
from src.core.theme import ThemeToken, resolve_rgb_color
from src.frontends.pygame_ce.app import PygameApp
from src.frontends.pygame_ce.audio_adapter import PygameAudioAdapter
from src.frontends.pygame_ce.renderer import PygameRenderer
from src.frontends.pygame_ce.views.title_view import PygameTitleView
from src.frontends.pygame_ce.views.map_view import PygameMapView
from src.frontends.pygame_ce.views.combat_view import PygameCombatView


@pytest.fixture(scope="module", autouse=True)
def setup_headless_sdl():
    """Ensure headless SDL environment for testing."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    yield


def test_pygame_renderer_theme_token_resolution():
    """Verify PygameRenderer maps theme tokens to valid 3-channel RGB tuples."""
    renderer = PygameRenderer()
    for token in ThemeToken:
        rgb = renderer.color(token)
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3
        assert all(0 <= c <= 255 for c in rgb)


def test_pygame_audio_adapter_handles_cues_safely():
    """Verify PygameAudioAdapter subscribes to event bus and executes cues without raising."""
    adapter = PygameAudioAdapter()
    for cue in AudioCue:
        adapter.play_cue(cue)

    # Trigger via DomainEvent on EventBus
    event_bus.emit(AudioCueEvent(cue=AudioCue.HIT))
    event_bus.drain()


def test_pygame_app_initialization_and_rendering():
    """Verify PygameApp initializes in headless mode and processes frames."""
    app = PygameApp(headless=True)
    assert app.session is not None
    assert app.screen is not None
    assert app.screen.get_width() == 960
    assert app.screen.get_height() == 540

    # Advance 5 frames through main loop
    app.run(max_frames=5)
    assert not app.is_running or app.headless


def test_pygame_title_view_workflow():
    """Verify PygameTitleView handles archetype selection and starts game."""
    session = GameSession()
    view = PygameTitleView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    assert view.selected_class == "warrior"

    # Select Rogue via keyboard '2'
    key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)
    view.handle_event(key_event, session)
    assert view.selected_class == "rogue"

    # Start journey via SPACE
    space_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    view.handle_event(space_event, session)

    assert session.current_mode == GameMode.MAP
    assert session.player.class_id == "rogue"

    # Ensure draw executes without errors
    view.draw(surface, renderer, session)


def test_pygame_map_view_workflow():
    """Verify PygameMapView renders nodes and handles node selection."""
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.switch_mode(GameMode.MAP)

    view = PygameMapView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    assert session.state.map_graph is not None
    available = session.state.map_graph.available_nodes
    assert len(available) > 0

    view.update(dt=0.016, session=session)
    view.draw(surface, renderer, session)

    # Select first available node via keyboard '1'
    key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    view.handle_event(key_event, session)

    # Upon selection, mode changes to the node's encounter (COMBAT, EVENTS, SHOP, etc.)
    assert session.current_mode in (GameMode.COMBAT, GameMode.EVENTS, GameMode.SHOP)


def test_pygame_combat_view_workflow():
    """Verify PygameCombatView animates floating damage popups and ticks turns."""
    session = GameSession()
    session.start_new_game(class_id="warrior")
    session.select_map_node(session.state.map_graph.available_nodes[0].id)

    # Force combat if first node was not monster
    if session.current_mode != GameMode.COMBAT:
        from src.systems.combat import CombatSystem
        from src.entities.enemy import Enemy
        dummy_enemy = Enemy(name="Test Goblin", max_hp=30, attack=5, defense=2)
        session.state.combat = CombatSystem(session.player, dummy_enemy, bus=session.bus)
        session.switch_mode(GameMode.COMBAT)

    view = PygameCombatView()
    renderer = PygameRenderer()
    surface = pygame.Surface((960, 540))

    assert session.combat is not None

    # Step combat via space key
    space_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    view.handle_event(space_event, session)

    # Simulate damage event to verify floating numbers
    session.bus.emit(
        DamageDealtEvent(
            source=session.player.name,
            target=session.combat.enemy.name,
            amount=15,
            is_crit=True,
        )
    )
    view._tick_combat(session)
    assert len(view.popups) > 0

    view.update(dt=0.05, session=session)
    view.draw(surface, renderer, session)
