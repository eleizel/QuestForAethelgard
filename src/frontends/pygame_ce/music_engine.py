"""Dynamic Music Engine and audio track management for Pygame-CE frontend.

Provides contextual background music state machine, randomized track selection,
smooth fading transitions, and persistent mute management across platforms.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import json
import logging
import math
from pathlib import Path
import random
from typing import Any, Final, Sequence

import pygame

from src.core.game_state import GameMode
from src.core.save_manager import StorageBackend, detect_storage_backend
from src.entities.enemy import EnemyTier
from src.frontends.pygame_ce.audio_track_loader import (
    DEFAULT_AUDIO_EXTENSIONS,
    AudioTrackLoader,
    get_default_music_dir,
    is_audio_available,
    load_audio_track,
    resolve_audio_track,
)

logger = logging.getLogger(__name__)


class MusicContext(Enum):
    """Contexts determining background music tracks."""

    WELCOME = auto()  # tracks: ["welcome_01", "welcome_02"]
    MAP = auto()  # tracks: ["exploration_01", "exploration_02"]
    COMBAT = auto()  # tracks: ["combat_01", "combat_02"]
    BOSS = auto()  # tracks: ["boss_01", "boss_02"]


class PlaybackState(Enum):
    """Internal stream playback lifecycle state."""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FADING_OUT = auto()


CONTEXT_TRACKS: Final[dict[MusicContext, tuple[str, ...]]] = {
    MusicContext.WELCOME: ("welcome_01", "welcome_02"),
    MusicContext.MAP: ("exploration_01", "exploration_02"),
    MusicContext.COMBAT: ("combat_01", "combat_02"),
    MusicContext.BOSS: ("boss_01", "boss_02"),
}

DEFAULT_SETTINGS_KEY: Final[str] = "quest_for_aethelgard_settings"
SETTINGS_SCHEMA_VERSION: Final[int] = 1
DEFAULT_FADE_MS: Final[int] = 500


@dataclass
class AudioSettingsData:
    """Serializable data container for audio configuration settings."""

    version: int = SETTINGS_SCHEMA_VERSION
    music_muted: bool = False
    music_volume: float = 1.0
    sfx_muted: bool = False
    sfx_volume: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to a JSON-serializable dictionary."""
        return {
            "version": int(self.version),
            "music_muted": bool(self.music_muted),
            "music_volume": float(max(0.0, min(1.0, self.music_volume))),
            "sfx_muted": bool(self.sfx_muted),
            "sfx_volume": float(max(0.0, min(1.0, self.sfx_volume))),
        }

    @classmethod
    def from_dict(cls, data: Any) -> AudioSettingsData:
        """Construct AudioSettingsData with defensive sanitization and fallback defaults."""
        if not isinstance(data, dict):
            logger.warning("AudioSettingsData.from_dict received non-dict payload: %s", type(data))
            return cls()

        # 1. version
        try:
            version = int(data.get("version", SETTINGS_SCHEMA_VERSION))
        except (ValueError, TypeError):
            version = SETTINGS_SCHEMA_VERSION

        # 2. music_muted
        music_muted_raw = data.get("music_muted", False)
        music_muted = music_muted_raw if isinstance(music_muted_raw, bool) else False

        # 3. music_volume
        try:
            raw_mv = float(data.get("music_volume", 1.0))
            if math.isnan(raw_mv) or math.isinf(raw_mv):
                music_volume = 1.0
            else:
                music_volume = max(0.0, min(1.0, raw_mv))
        except (ValueError, TypeError):
            music_volume = 1.0

        # 4. sfx_muted
        sfx_muted_raw = data.get("sfx_muted", False)
        sfx_muted = sfx_muted_raw if isinstance(sfx_muted_raw, bool) else False

        # 5. sfx_volume
        try:
            raw_sv = float(data.get("sfx_volume", 1.0))
            if math.isnan(raw_sv) or math.isinf(raw_sv):
                sfx_volume = 1.0
            else:
                sfx_volume = max(0.0, min(1.0, raw_sv))
        except (ValueError, TypeError):
            sfx_volume = 1.0

        return cls(
            version=version,
            music_muted=music_muted,
            music_volume=music_volume,
            sfx_muted=sfx_muted,
            sfx_volume=sfx_volume,
        )


class AudioSettingsManager:
    """Manages audio persistence across desktop file saves and browser LocalStorage."""

    def __init__(
        self,
        backend: StorageBackend | None = None,
        storage_key: str = DEFAULT_SETTINGS_KEY,
        auto_load: bool = True,
    ) -> None:
        self.backend: StorageBackend = backend if backend is not None else detect_storage_backend()
        self.storage_key: str = storage_key
        self.data: AudioSettingsData = AudioSettingsData()
        if auto_load:
            self.load()

    def is_music_muted(self) -> bool:
        """Return True if background music is currently muted."""
        return self.data.music_muted

    def set_music_muted(self, muted: bool, auto_save: bool = True) -> None:
        """Update music mute state and persist to storage."""
        self.data.music_muted = bool(muted)
        if auto_save:
            self.save()

    def toggle_music_muted(self, auto_save: bool = True) -> bool:
        """Toggle mute state, persist, and return the new state."""
        new_val = not self.data.music_muted
        self.set_music_muted(new_val, auto_save=auto_save)
        return new_val

    def get_music_volume(self) -> float:
        """Return master music volume in range [0.0, 1.0]."""
        return self.data.music_volume

    def set_music_volume(self, volume: float, auto_save: bool = True) -> None:
        """Set music volume, clamped to [0.0, 1.0], and persist."""
        try:
            val = float(volume)
            if math.isnan(val) or math.isinf(val):
                val = 1.0
            else:
                val = max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            val = 1.0
        self.data.music_volume = val
        if auto_save:
            self.save()

    def get_sfx_muted(self) -> bool:
        """Return True if sound effects are muted."""
        return self.data.sfx_muted

    def set_sfx_muted(self, muted: bool, auto_save: bool = True) -> None:
        """Set sound effects mute state and persist."""
        self.data.sfx_muted = bool(muted)
        if auto_save:
            self.save()

    def get_sfx_volume(self) -> float:
        """Return sound effects volume in range [0.0, 1.0]."""
        return self.data.sfx_volume

    def set_sfx_volume(self, volume: float, auto_save: bool = True) -> None:
        """Set sound effects volume, clamped to [0.0, 1.0], and persist."""
        try:
            val = float(volume)
            if math.isnan(val) or math.isinf(val):
                val = 1.0
            else:
                val = max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            val = 1.0
        self.data.sfx_volume = val
        if auto_save:
            self.save()

    def save(self) -> bool:
        """Serialize settings to storage backend."""
        try:
            serialized = json.dumps(self.data.to_dict())
            return bool(self.backend.set(self.storage_key, serialized))
        except Exception as exc:
            logger.warning("Failed to save audio settings: %s", exc)
            return False

    def load(self) -> bool:
        """Deserialize settings from storage backend with fallback defaults."""
        try:
            raw = self.backend.get(self.storage_key)
            if not raw:
                self.data = AudioSettingsData()
                return False
            payload = json.loads(raw)
            self.data = AudioSettingsData.from_dict(payload)
            return True
        except Exception as exc:
            logger.debug("Failed to load audio settings (fallback to defaults): %s", exc)
            self.data = AudioSettingsData()
            return False


class DynamicMusicEngine:
    """Core state machine managing music contexts, track randomization, and transitions."""

    def __init__(
        self,
        settings_manager: AudioSettingsManager | None = None,
        assets_dir: Path | str | None = None,
        loader: AudioTrackLoader | None = None,
        rng: random.Random | None = None,
        auto_init_mixer: bool = True,
        default_fade_ms: int = 0,
    ) -> None:
        self.settings_manager: AudioSettingsManager = (
            settings_manager if settings_manager is not None else AudioSettingsManager()
        )
        self.loader: AudioTrackLoader = (
            loader
            if loader is not None
            else AudioTrackLoader(music_dir=assets_dir, auto_init_mixer=auto_init_mixer)
        )
        self._rng: random.Random = rng if rng is not None else random.Random()
        self.default_fade_ms: int = default_fade_ms

        self._current_context: MusicContext | None = None
        self._current_track: str | None = None
        self._playback_state: PlaybackState = PlaybackState.STOPPED

        self._volume: float = self.settings_manager.get_music_volume()
        self._fade_timer: float = 0.0
        self._fade_duration: float = 0.0
        self._pending_context: MusicContext | None = None
        self._pending_track: str | None = None

        self._end_event: int | None = None

        # Synchronize hardware volume with loaded mute setting
        self._apply_volume()

    # -------------------------------------------------------------------------
    # Context State Machine
    # -------------------------------------------------------------------------

    def set_context(
        self,
        context: MusicContext | None,
        force_restart: bool = False,
        fade_ms: int | None = None,
    ) -> None:
        """Switch or maintain active music context.

        Args:
            context: Target MusicContext, or None to retain current playback.
            force_restart: If True, re-randomizes and restarts playback even if
                the context is identical to current.
            fade_ms: Transition fade duration in milliseconds. Defaults to 0 or default_fade_ms.
        """
        if context is None:
            return

        fade_duration = fade_ms if fade_ms is not None else self.default_fade_ms

        # 1. Same context retention
        if context == self._current_context and not force_restart:
            if self._playback_state in (
                PlaybackState.PLAYING,
                PlaybackState.PAUSED,
                PlaybackState.FADING_OUT,
            ):
                return
            # If currently stopped, start track for this context
            new_track = self._select_track(context)
            self._start_track_playback(new_track, fade_ms=fade_duration)
            return

        # 2. Context switch or forced restart
        self._current_context = context
        new_track = self._select_track(context)

        # Immediate start
        self._pending_track = None
        self._pending_context = None
        self._fade_timer = 0.0
        self._start_track_playback(new_track, fade_ms=fade_duration)

    def _select_track(self, context: MusicContext) -> str:
        """Uniformly pick a track from the given context's registered tracks."""
        candidates = CONTEXT_TRACKS.get(context, ())
        if not candidates:
            return ""
        return self._rng.choice(candidates)

    def choose_track(self, context: MusicContext) -> str:
        """Public alias for _select_track."""
        return self._select_track(context)

    def resolve_track(self, track_name: str | Path | None) -> Path | None:
        """Resolve an audio track name or path via underlying loader."""
        return self.loader.resolve_track(track_name)

    def load_track(self, track_name: str | Path | None) -> bool:
        """Load an audio track via underlying loader."""
        return self.loader.load_track(track_name)

    def _start_track_playback(self, track_name: str, fade_ms: int = 0) -> bool:
        """Load and start playback of track with loops=0 for randomized re-looping."""
        if not track_name:
            self._playback_state = PlaybackState.STOPPED
            self._current_track = None
            return False

        self._current_track = track_name
        self._apply_volume()
        success = self.loader.play_track(track_name, loops=0, fade_ms=fade_ms)
        self._apply_volume()
        if success:
            self._playback_state = PlaybackState.PLAYING
        else:
            self._playback_state = PlaybackState.STOPPED
            if self.loader.is_mixer_available():
                self._current_track = None
        return success

    # -------------------------------------------------------------------------
    # Frame Update & Loop Re-Randomization
    # -------------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance transition timers and detect track completion for loop randomization."""
        if dt < 0:
            dt = 0.0

        if not self.loader.is_mixer_available():
            return

        if self._current_context is None:
            return

        # Case 1: Active fadeout transition
        if self._playback_state == PlaybackState.FADING_OUT:
            self._fade_timer -= dt
            if self._fade_timer <= 0.0 or not self._is_music_busy():
                if self._pending_track is not None:
                    next_track = self._pending_track
                    self._pending_track = None
                    self._pending_context = None
                    fade_in = int(self._fade_duration * 1000)
                    self._start_track_playback(next_track, fade_ms=fade_in)
                else:
                    self._playback_state = PlaybackState.STOPPED
                    self._current_track = None

        # Case 2: Natural track completion (loop point)
        elif self._playback_state == PlaybackState.PLAYING:
            if not self._is_music_busy():
                self._handle_track_finished()

    def _handle_track_finished(self) -> None:
        """Called when current track completes naturally. Re-randomizes within context."""
        if self._current_context is None:
            self._playback_state = PlaybackState.STOPPED
            self._current_track = None
            return

        next_track = self._select_track(self._current_context)
        self._start_track_playback(next_track, fade_ms=0)

    def _is_music_busy(self) -> bool:
        """Safe check for active mixer music stream."""
        if not self.loader.is_mixer_available():
            return False
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Event & Endevent Handling
    # -------------------------------------------------------------------------

    def set_end_event(self, event_type: int | None) -> None:
        """Register a Pygame custom event type for track completion."""
        self._end_event = event_type
        if self.loader.is_mixer_available():
            try:
                if event_type is not None:
                    pygame.mixer.music.set_endevent(event_type)
                else:
                    pygame.mixer.music.set_endevent()
            except Exception:
                pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle incoming Pygame events (e.g. registered endevent)."""
        if self._end_event is not None and getattr(event, "type", None) == self._end_event:
            if self._playback_state == PlaybackState.PLAYING and not self._is_music_busy():
                self._handle_track_finished()

    # -------------------------------------------------------------------------
    # Playback Controls: Stop, Pause, Unpause
    # -------------------------------------------------------------------------

    def stop(self, fade_ms: int = 0) -> None:
        """Stop music playback with optional fadeout."""
        if fade_ms > 0 and self._playback_state == PlaybackState.PLAYING:
            self._playback_state = PlaybackState.FADING_OUT
            self._pending_track = None
            self._pending_context = None
            self._fade_duration = fade_ms / 1000.0
            self._fade_timer = self._fade_duration
            self.loader.stop(fade_ms=fade_ms)
        else:
            self.loader.stop(0)
            self._playback_state = PlaybackState.STOPPED
            self._current_track = None
            self._pending_track = None
            self._pending_context = None
            self._fade_timer = 0.0

    def pause(self) -> None:
        """Pause playback if currently playing."""
        if self._playback_state == PlaybackState.PLAYING:
            if self.loader.is_mixer_available():
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
            self._playback_state = PlaybackState.PAUSED

    def unpause(self) -> None:
        """Resume playback if currently paused."""
        if self._playback_state == PlaybackState.PAUSED:
            if self.loader.is_mixer_available():
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
            self._playback_state = PlaybackState.PLAYING

    # -------------------------------------------------------------------------
    # Volume & Mute Management
    # -------------------------------------------------------------------------

    def is_muted(self) -> bool:
        """Return True if background music is silenced."""
        return self.settings_manager.is_music_muted()

    def set_muted(self, muted: bool) -> None:
        """Set mute state, persist to settings, and adjust volume immediately."""
        self.settings_manager.set_music_muted(muted)
        self._apply_volume()

    def toggle_mute(self) -> bool:
        """Toggle mute state, persist to settings, and return new mute state."""
        new_state = self.settings_manager.toggle_music_muted()
        self._apply_volume()
        return new_state

    def get_volume(self) -> float:
        """Return master unmuted volume."""
        return self._volume

    def set_volume(self, volume: float) -> None:
        """Set master unmuted volume [0.0, 1.0]."""
        self._volume = max(0.0, min(1.0, float(volume)))
        self.settings_manager.set_music_volume(self._volume)
        self._apply_volume()

    def _apply_volume(self) -> None:
        """Apply effective volume (0.0 if muted, else _volume) to Pygame mixer."""
        if not self.loader.is_mixer_available():
            return
        effective_vol = 0.0 if self.is_muted() else self._volume
        try:
            pygame.mixer.music.set_volume(effective_vol)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Introspection Properties
    # -------------------------------------------------------------------------

    def get_current_context(self) -> MusicContext | None:
        """Return active MusicContext or None."""
        return self._current_context

    def get_current_track(self) -> str | None:
        """Return currently active track name or None."""
        return self._current_track

    def is_playing(self) -> bool:
        """Return True if state is currently PLAYING."""
        return self._playback_state == PlaybackState.PLAYING

    def is_paused(self) -> bool:
        """Return True if state is currently PAUSED."""
        return self._playback_state == PlaybackState.PAUSED

    @property
    def playback_state(self) -> PlaybackState:
        """Return internal playback state."""
        return self._playback_state


# -----------------------------------------------------------------------------
# Context Resolution Function
# -----------------------------------------------------------------------------

def resolve_music_context(session: Any) -> MusicContext | None:
    """Resolve the appropriate MusicContext for the current GameSession state."""
    mode = getattr(session, "current_mode", None)

    if mode in (
        GameMode.WELCOME,
        GameMode.CLASS_SELECT,
        getattr(GameMode, "BIOME_SELECT", None),
        getattr(GameMode, "CREDITS", None),
    ):
        return MusicContext.WELCOME
    elif mode == GameMode.MAP:
        return MusicContext.MAP
    elif mode == GameMode.COMBAT:
        combat = getattr(session, "combat", None)
        enemy = getattr(combat, "enemy", None) if combat else None
        tier = getattr(enemy, "tier", None) if enemy else None
        if tier in (EnemyTier.ELITE, EnemyTier.BOSS):
            return MusicContext.BOSS
        return MusicContext.COMBAT

    # Retain current context across modals and loot/reward phases
    return None


__all__ = [
    "AudioSettingsData",
    "AudioSettingsManager",
    "AudioTrackLoader",
    "CONTEXT_TRACKS",
    "DEFAULT_AUDIO_EXTENSIONS",
    "DEFAULT_FADE_MS",
    "DEFAULT_SETTINGS_KEY",
    "DynamicMusicEngine",
    "MusicContext",
    "PlaybackState",
    "SETTINGS_SCHEMA_VERSION",
    "get_default_music_dir",
    "is_audio_available",
    "load_audio_track",
    "resolve_audio_track",
    "resolve_music_context",
]
