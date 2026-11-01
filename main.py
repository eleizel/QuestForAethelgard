"""Entry point for Quest for Aethelgard supporting multi-frontend switching."""

import argparse
import sys


def main() -> None:
    """Initialize and run the Quest for Aethelgard engine."""
    parser = argparse.ArgumentParser(description="Quest for Aethelgard")
    parser.add_argument(
        "--frontend",
        choices=["pyxel", "pygame"],
        default="pyxel",
        help="Frontend presentation engine to run (default: pyxel)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without displaying a graphical window (for CI/simulations)",
    )
    args, _ = parser.parse_known_args()

    if args.frontend == "pygame":
        from src.frontends.pygame_ce.app import PygameApp
        app = PygameApp(headless=args.headless)
        if args.headless:
            app.run(max_frames=5)
        else:
            app.run()
    else:
        from src.ui.engine import Engine
        engine = Engine(headless=args.headless)
        if not args.headless:
            engine.run()


if __name__ == "__main__":
    main()
