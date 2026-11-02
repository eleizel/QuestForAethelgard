# /// script
# dependencies = [
#  "pygame-ce",
# ]
# ///
"""Entry point for Quest for Aethelgard supporting multi-frontend switching."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import pygame
import pygame.display
import pygame.font
import pygame.image
import pygame.mixer


async def main() -> None:
    """Initialize and run the Quest for Aethelgard engine."""
    parser = argparse.ArgumentParser(description="Quest for Aethelgard")
    default_frontend = "pygame" if sys.platform == "emscripten" else "pygame"
    parser.add_argument(
        "--frontend",
        choices=["pyxel", "pygame"],
        default=default_frontend,
        help="Frontend presentation engine to run (default: pygame)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without displaying a graphical window (for CI/simulations)",
    )
    parser.add_argument(
        "--fullscreen",
        "-f",
        action="store_true",
        help="Launch the pygame frontend in fullscreen mode",
    )
    parser.add_argument(
        "--maximized",
        "-m",
        action="store_true",
        help="Launch the pygame frontend in a maximized window",
    )
    args, _ = parser.parse_known_args()

    if args.frontend == "pygame":
        from src.frontends.pygame_ce.app import PygameApp
        app = PygameApp(
            headless=args.headless,
            fullscreen=args.fullscreen,
            maximized=args.maximized,
        )
        if sys.platform == "emscripten":
            await app.run_async()
        elif args.headless:
            app.run(max_frames=5)
        else:
            await app.run_async()
    else:
        from src.ui.engine import Engine
        engine = Engine(headless=args.headless)
        if not args.headless:
            engine.run()


if __name__ == "__main__":
    asyncio.run(main())
