"""Centralized audio manager handling sound effects, biome themes, and mute states."""

from __future__ import annotations

import pyxel

from src.config import (
    MUS_BOSS,
    MUS_COMBAT,
    MUS_MAP_ARBORETUM,
    MUS_MAP_CATHEDRAL,
    MUS_MAP_FOUNDRY,
    MUS_MAP_OBSERVATORY,
    MUS_MAP_OSSUARY,
    MUS_MAP_SANCTUM,
    MUS_TITLE,
    SND_CH_SFX,
)


class AudioManager:
    """Manages audio playback, mute toggles, and track transitions."""

    def __init__(self) -> None:
        self.music_enabled: bool = True
        self.sfx_enabled: bool = True
        self.current_track: int | None = None

        self._biome_track_map: dict[str, int] = {
            "arboretum": MUS_MAP_ARBORETUM,
            "cathedral": MUS_MAP_CATHEDRAL,
            "ossuary": MUS_MAP_OSSUARY,
            "foundry": MUS_MAP_FOUNDRY,
            "observatory": MUS_MAP_OBSERVATORY,
            "sanctum": MUS_MAP_SANCTUM,
        }

    def toggle_music(self) -> bool:
        """Toggle music state and update playback immediately."""
        self.music_enabled = not self.music_enabled
        if not self.music_enabled:
            self.stop_music()
        else:
            if self.current_track is not None:
                track = self.current_track
                self.current_track = None
                self.play_music(track)
        return self.music_enabled

    def toggle_sfx(self) -> bool:
        """Toggle sound effects state."""
        self.sfx_enabled = not self.sfx_enabled
        return self.sfx_enabled

    def play_sfx(self, sound_id: int) -> None:
        """Play sound effect on Channel 3 if enabled."""
        if self.sfx_enabled:
            pyxel.play(SND_CH_SFX, sound_id)

    def play_music(self, track_id: int) -> None:
        """Play designated music track across channels 0-2 with repeat."""
        if self.current_track == track_id and self.music_enabled:
            return

        self.current_track = track_id
        if self.music_enabled:
            pyxel.playm(track_id, loop=True)
        else:
            self.stop_music()

    def stop_music(self) -> None:
        """Stop music on channels 0, 1, and 2."""
        pyxel.stop(0)
        pyxel.stop(1)
        pyxel.stop(2)

    def play_biome_music(self, biome_id: str) -> None:
        """Select and play the thematic map music for the current biome."""
        track = self._biome_track_map.get(biome_id, MUS_MAP_ARBORETUM)
        self.play_music(track)

    def play_combat_music(self, is_boss: bool = False) -> None:
        """Play combat or boss theme."""
        self.play_music(MUS_BOSS if is_boss else MUS_COMBAT)


audio = AudioManager()