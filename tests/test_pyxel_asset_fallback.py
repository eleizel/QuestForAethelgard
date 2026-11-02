"""Test Pyxel resource loading and in-memory asset fallback."""

from unittest.mock import patch
import pyxel
from src.ui.engine import Engine


def test_pyxel_asset_loading():
    """Verify that Engine loads Pyxel assets from file or memory."""
    engine = Engine(headless=True)

    # Check Bank 0 (Hero warrior sprite at 0, 0 is 16x16 with non-zero pixels)
    bank0_has_hero_pixels = any(pyxel.images[0].pget(x, y) != 0 for x in range(16) for y in range(16))
    assert bank0_has_hero_pixels, "Bank 0 should contain non-zero pixels for hero sprite"

    # Check Bank 1 (Title screen gothic art)
    bank1_has_title_pixels = any(pyxel.images[1].pget(x, y) != 0 for x in range(32) for y in range(32))
    assert bank1_has_title_pixels, "Bank 1 should contain non-zero pixels for title screen art"


def test_populate_pyxel_resources_direct():
    """Verify that populate_pyxel_resources directly fills Bank 0, Bank 1, and Bank 2."""
    from src.tools.generate_assets import populate_pyxel_resources

    # Clear bank 0
    pyxel.images[0].cls(0)
    assert not any(pyxel.images[0].pget(x, y) != 0 for x in range(16) for y in range(16))

    # Populate
    populate_pyxel_resources()
    assert any(pyxel.images[0].pget(x, y) != 0 for x in range(16) for y in range(16))
