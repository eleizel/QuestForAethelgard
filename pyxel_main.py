"""Pyxel 8-Bit Retro presentation entrypoint for Quest for Aethelgard."""

from src.ui.engine import Engine


def main() -> None:
    """Run the Pyxel 8-bit retro engine."""
    engine = Engine()
    engine.run()


if __name__ == "__main__":
    main()
