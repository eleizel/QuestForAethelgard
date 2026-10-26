from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING
import pyxel
from src.core.i18n import t
if TYPE_CHECKING:
    from src.core.game_state import GameState
    from src.ui.renderer import Renderer
ENEMY_SPRITE_COORDS: dict[str, tuple[int, int]] = {
    # Act 1A: The Wilted Arboretum (y=48)
    "thornvein_creeper": (0, 48),
    "spore_pod": (16, 48),
    "bramble_hound": (32, 48),
    "rotting_woodwose": (48, 48),
    "mandragora_matron": (64, 48),
    "corpse_treant": (80, 48),
    "malignant_belladonna": (96, 48),
    "verdant_abomination": (112, 48),

    # Act 1B: The Desecrated Cathedral (y=64)
    "cathedral_imp": (0, 64),
    "possessed_grimoire": (16, 64),
    "candelabra_fiend": (32, 64),
    "penitent_zealot": (48, 64),
    "belltower_gargoyle": (64, 64),
    "inquisitor_automaton": (80, 64),
    "blind_archbishop": (96, 64),
    "chorus_of_damned": (112, 64),

    # Act 2A: The Drowned Ossuary (y=80)
    "mire_ghoul": (0, 80),
    "drowned_skulls": (16, 80),
    "leech_husk": (32, 80),
    "crypt_lurker": (48, 80),
    "tide_gravekeeper": (64, 80),
    "carrion_behemoth": (80, 80),
    "drowned_patriarch": (96, 80),
    "scylla_bone_weaver": (112, 80),

    # Act 2B: The Foundry of Torment (y=96)
    "slag_homunculus": (0, 96),
    "cinder_sprite": (16, 96),
    "clockwork_flayer": (32, 96),
    "ashen_overseer": (48, 96),
    "furnace_warden": (64, 96),
    "retching_alchemist": (80, 96),
    "ironforge_tyrant": (96, 96),
    "molten_sovereign": (112, 96),

    # Act 3A: The Astral Observatory (y=112)
    "void_mirror": (0, 112),
    "stareater_wisp": (16, 112),
    "comet_stalker": (32, 112),
    "celestial_hermit": (48, 112),
    "rift_warden": (64, 112),
    "null_singularity": (80, 112),
    "chronomancer_praetor": (96, 112),
    "devouring_constellation": (112, 112),

    # Act 3B: The Blood Sanctum (y=128)
    "sanguine_thrall": (0, 128),
    "crimson_gargoyle": (16, 128),
    "hemomancer_acolyte": (32, 128),
    "flayed_duelist": (48, 128),
    "baroness_vespera": (64, 128),
    "amalgam_of_veins": (80, 128),
    "high_lord_carmilla": (96, 128),
    "blood_god_avatar": (112, 128),
}

SPEED_INTERVALS = [15, 7, 2]
SPEED_LABELS = ["1x", "2x", "3x"]



@dataclass
class CombatPopup:
    x: int
    y: int
    text: str
    color: int
    lifetime: int = 18

class View:
    """Base abstract interface for game screens."""
    def update(self, game_state: GameState) -> None:
        pass
    def draw(self, game_state: GameState, renderer: Renderer) -> None:
        pass
