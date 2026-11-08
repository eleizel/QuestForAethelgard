"""Audio track loader and resolver for Quest for Aethelgard Pygame-CE frontend.

Provides cross-platform path resolution (desktop, PyInstaller, Pygbag WASM),
format fallback (.ogg -> .mp3 -> .wav), and graceful degradation in headless or
uninitialized mixer environments.
"""

from __future__ import annotations

from collections import OrderedDict
import logging
import os
from pathlib import Path
import sys
import threading
from typing import Final, Sequence

import pygame

logger = logging.getLogger(__name__)

# Fallback extension order: modern compressed OGG Vorbis first, then MP3, then legacy WAV
DEFAULT_AUDIO_EXTENSIONS: Final[tuple[str, ...]] = (".ogg", ".mp3", ".wav")
DEFAULT_MAX_CACHE_SIZE: Final[int] = 512
DOS_DEVICES: Final[set[str]] = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}



def get_default_music_dir() -> Path:
    """Discover default music asset directory across Desktop, PyInstaller, and Pygbag."""
    # 1. PyInstaller frozen single-file executable
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_music = Path(sys._MEIPASS) / "assets" / "music"
        if meipass_music.is_dir():
            return meipass_music

    # 2. Source tree root relative to this module: src/frontends/pygame_ce/ -> root
    source_root = Path(__file__).resolve().parents[3]
    source_music = source_root / "assets" / "music"
    if source_music.is_dir():
        return source_music

    # 3. Current working directory fallback
    cwd_music = Path.cwd() / "assets" / "music"
    if cwd_music.is_dir():
        return cwd_music

    # 4. Relative fallback
    rel_music = Path("assets") / "music"
    if rel_music.is_dir():
        return rel_music

    return source_music


class AudioTrackLoader:
    """Resolves audio track paths and loads background music with format fallback."""

    def __init__(
        self,
        music_dir: Path | str | None = None,
        extensions: Sequence[str] = DEFAULT_AUDIO_EXTENSIONS,
        auto_init_mixer: bool = True,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    ) -> None:
        self._custom_music_dir: Path | None = Path(music_dir) if music_dir is not None else None
        self.extensions: tuple[str, ...] = tuple(
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        )
        self.auto_init_mixer: bool = auto_init_mixer
        self._max_cache_size: int = max(1, max_cache_size)
        self._cache: OrderedDict[str, Path | None] = OrderedDict()
        self._cache_lock: threading.Lock = threading.Lock()
        self._current_track: str | None = None
        self._current_path: Path | None = None

        if self.auto_init_mixer:
            self.init_mixer()

    def _get_from_cache(self, key: str) -> tuple[bool, Path | None]:
        with self._cache_lock:
            if key in self._cache:
                val = self._cache[key]
                self._cache.move_to_end(key)
                return True, val
            return False, None

    def _put_into_cache(self, key: str, value: Path | None) -> None:
        with self._cache_lock:
            if key in self._cache:
                self._cache[key] = value
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_cache_size:
                    self._cache.popitem(last=False)
                self._cache[key] = value


    def is_mixer_available(self) -> bool:
        """Return True if pygame.mixer is initialized and ready for music playback."""
        try:
            return bool(pygame.mixer and pygame.mixer.get_init())
        except Exception:
            return False

    def init_mixer(
        self,
        frequency: int = 44100,
        size: int = -16,
        channels: int = 2,
        buffer: int = 512,
    ) -> bool:
        """Attempt to safely initialize pygame.mixer if not already initialized."""
        if self.is_mixer_available():
            return True
        try:
            pygame.mixer.init(frequency=frequency, size=size, channels=channels, buffer=buffer)
            return True
        except (pygame.error, Exception) as exc:
            logger.debug("Failed to initialize pygame.mixer: %s", exc)
            return False

    def get_search_directories(self) -> list[Path]:
        """Return candidate directories in search priority order."""
        dirs: list[Path] = []
        if self._custom_music_dir is not None:
            dirs.append(self._custom_music_dir)

        default_dir = get_default_music_dir()
        if default_dir not in dirs:
            dirs.append(default_dir)

        # Additional fallback search paths
        source_assets = Path(__file__).resolve().parents[3] / "assets"
        if source_assets not in dirs and source_assets.is_dir():
            dirs.append(source_assets)

        cwd_music = Path.cwd() / "assets" / "music"
        if cwd_music not in dirs and cwd_music.is_dir():
            dirs.append(cwd_music)

        return dirs

    def resolve_track(self, track_name: str | Path | None) -> Path | None:
        """Resolve a track name or path across search directories and extension fallback.

        Resolves bare names (e.g. 'exploration_01'), relative subpaths
        (e.g. 'ambient/cave_01'), or files with extensions through the
        fallback extension chain (.ogg -> .mp3 -> .wav).

        Returns:
            Resolved absolute Path if found within search directories, None if the track
            does not exist or is invalid/contained outside search roots.
        """
        if track_name is None:
            return None

        if not isinstance(track_name, (str, Path)):
            return None

        raw_str = str(track_name).strip()
        if not raw_str:
            return None

        hit, cached = self._get_from_cache(raw_str)
        if hit:
            return cached

        if "\x00" in raw_str:
            self._put_into_cache(raw_str, None)
            return None

        norm_str = raw_str.replace("\\", "/")

        if raw_str.startswith(("//", "\\\\")) or norm_str.startswith("//"):
            self._put_into_cache(raw_str, None)
            return None

        try:
            raw_path = Path(norm_str)
        except (ValueError, OSError):
            self._put_into_cache(raw_str, None)
            return None

        if ".." in raw_path.parts:
            self._put_into_cache(raw_str, None)
            return None

        if raw_path.stem.lower() in DOS_DEVICES:
            self._put_into_cache(raw_str, None)
            return None

        search_dirs = self.get_search_directories()

        # 1. Direct file check with extension and containment validation
        try:
            if raw_path.is_file() and raw_path.suffix.lower() in self.extensions:
                resolved = raw_path.resolve()
                for directory in search_dirs:
                    try:
                        if directory.exists() and resolved.is_relative_to(directory.resolve()):
                            self._put_into_cache(raw_str, resolved)
                            return resolved
                    except (ValueError, OSError):
                        continue
        except (ValueError, OSError):
            pass

        stem = raw_path.stem.lower()
        suffix = raw_path.suffix.lower()

        # Determine extension priority for this query
        if suffix and suffix in self.extensions:
            # Try specified extension first, then fallback to other supported extensions
            candidates_ext = [suffix] + [ext for ext in self.extensions if ext != suffix]
        else:
            candidates_ext = list(self.extensions)

        rel_parent = raw_path.parent

        # 2. Search candidate directories with extension fallback
        for directory in search_dirs:
            try:
                if not directory.exists() or not directory.is_dir():
                    continue
                dir_resolved = directory.resolve()
            except (ValueError, OSError):
                continue

            target_dir = directory / rel_parent
            try:
                target_resolved = target_dir.resolve()
                if not target_resolved.is_relative_to(dir_resolved):
                    continue
            except (ValueError, OSError):
                continue

            # Direct filename lookups
            for ext in candidates_ext:
                try:
                    candidate = target_dir / f"{stem}{ext}"
                    if candidate.is_file():
                        resolved = candidate.resolve()
                        if resolved.is_relative_to(dir_resolved):
                            self._put_into_cache(raw_str, resolved)
                            return resolved
                except (ValueError, OSError):
                    pass

            # Case-insensitive filesystem fallback (for Linux / WebAssembly MEMFS)
            try:
                if target_dir.is_dir():
                    for entry in target_dir.iterdir():
                        try:
                            if (
                                entry.is_file()
                                and entry.stem.lower() == stem
                                and entry.suffix.lower() in candidates_ext
                            ):
                                resolved = entry.resolve()
                                if resolved.is_relative_to(dir_resolved):
                                    self._put_into_cache(raw_str, resolved)
                                    return resolved
                        except (ValueError, OSError):
                            pass
            except (ValueError, OSError):
                pass

        self._put_into_cache(raw_str, None)
        return None


    def load_track(self, track_name: str | Path | None) -> bool:
        """Resolve and load track into pygame.mixer.music with graceful failure handling.

        Guaranteed not to raise uncaught exceptions on missing files, uninitialized
        mixers, or corrupted files.

        Returns:
            True if track was successfully loaded into pygame.mixer.music, False otherwise.
        """
        if track_name is None:
            return False

        if not self.is_mixer_available():
            if self.auto_init_mixer and not self.init_mixer():
                logger.debug("Mixer unavailable, skipping music load for '%s'", track_name)
                return False
            if not self.is_mixer_available():
                return False

        resolved_path = self.resolve_track(track_name)
        if resolved_path is None:
            logger.warning("Audio track '%s' not found across search directories", track_name)
            return False

        try:
            pygame.mixer.music.load(str(resolved_path))
            self._current_track = str(track_name)
            self._current_path = resolved_path
            return True
        except (pygame.error, OSError, Exception) as exc:
            logger.error("Failed to load audio track '%s' from %s: %s", track_name, resolved_path, exc)
            return False

    def play_track(
        self,
        track_name: str | Path | None,
        loops: int = -1,
        start: float = 0.0,
        fade_ms: int = 0,
    ) -> bool:
        """Resolve, load, and play track with looping and optional fade-in.

        Returns:
            True if track was loaded and playback started, False otherwise.
        """
        if not self.load_track(track_name):
            return False

        try:
            if fade_ms > 0:
                pygame.mixer.music.play(loops=loops, start=start, fade_ms=fade_ms)
            else:
                pygame.mixer.music.play(loops=loops, start=start)
            return True
        except (pygame.error, Exception) as exc:
            logger.warning("Failed to play audio track '%s': %s", track_name, exc)
            return False

    def stop(self, fade_ms: int = 0) -> None:
        """Stop music stream with optional fadeout."""
        if not self.is_mixer_available():
            return
        try:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
        except (pygame.error, Exception):
            pass

    def clear_cache(self) -> None:
        """Clear resolution cache."""
        with self._cache_lock:
            self._cache.clear()

    def get_available_tracks(self) -> dict[str, Path]:
        """Scan search directories and return map of stem -> resolved Path."""
        available: dict[str, Path] = {}
        for directory in reversed(self.get_search_directories()):
            if not directory.exists() or not directory.is_dir():
                continue
            for ext in reversed(self.extensions):
                for p in directory.glob(f"*{ext}"):
                    available[p.stem.lower()] = p.resolve()
        return available

    @property
    def current_track(self) -> str | None:
        return self._current_track

    @property
    def current_path(self) -> Path | None:
        return self._current_path


# Standalone functional API
def resolve_audio_track(track_name: str | Path | None, music_dir: Path | str | None = None) -> Path | None:
    """Resolve an audio track name using AudioTrackLoader."""
    loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=False)
    return loader.resolve_track(track_name)


def load_audio_track(track_name: str | Path | None, music_dir: Path | str | None = None) -> bool:
    """Resolve and load an audio track using AudioTrackLoader."""
    loader = AudioTrackLoader(music_dir=music_dir, auto_init_mixer=True)
    return loader.load_track(track_name)


def is_audio_available() -> bool:
    """Check if pygame.mixer is initialized and available."""
    try:
        return bool(pygame.mixer and pygame.mixer.get_init())
    except Exception:
        return False
