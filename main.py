"""Entry point for Quest for Aethelgard."""

import sys

from src.ui.engine import Engine


def main() -> None:
    """Initialize and run the Quest for Aethelgard engine."""
    headless = "--headless" in sys.argv
    engine = Engine(headless=headless)
    if not headless:
        engine.run()


if __name__ == "__main__":
    main()
