"""Pyxel application lifecycle controller (init, update, draw)."""

from __future__ import annotations

import os
import pyxel

from src.config import BG_COLOR, FPS, RESOURCE_PATH, SCREEN_HEIGHT, SCREEN_WIDTH, WINDOW_TITLE
from src.core.game_state import GameState
from src.ui.renderer import Renderer
from src.ui.views import ViewManager


class Engine:
    """Master application engine driving the Pyxel game lifecycle."""

    def __init__(self, headless: bool = False) -> None:
        self.headless: bool = headless
        pyxel.init(
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            title=WINDOW_TITLE,
            fps=FPS,
            headless=self.headless,
            quit_key=pyxel.KEY_NONE,

        )

        if not self.headless:
            pyxel.mouse(True)

        abs_resource_path = os.path.abspath(RESOURCE_PATH)
        if os.path.exists(abs_resource_path):
            try:
                pyxel.load(abs_resource_path)
            except (RuntimeError, ValueError) as e:
                print(f"Warning: Could not load resource file {abs_resource_path}: {e}")

        self.game_state: GameState = GameState()
        self.renderer: Renderer = Renderer()
        self.view_manager: ViewManager = ViewManager()

    def update(self) -> None:
        """Frame update loop delegating input and state progression."""
        self.view_manager.update(self.game_state)

    def draw(self) -> None:
        """Frame render loop delegating drawing calls."""
        pyxel.cls(BG_COLOR)
        self.view_manager.draw(self.game_state, self.renderer)

    def run(self) -> None:
        """Start the interactive Pyxel application loop."""
        pyxel.run(self.update, self.draw)
