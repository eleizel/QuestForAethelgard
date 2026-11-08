"""Pygame-CE audio adapter subscribing to domain audio cues."""

from __future__ import annotations

import array
import math
from typing import TYPE_CHECKING

import pygame

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.frontends.pygame_ce.music_engine import DynamicMusicEngine, MusicContext

if TYPE_CHECKING:
    from src.core.events import EventBus


class PygameAudioAdapter:
    """Translates high-level domain AudioCueEvents into Pygame-CE audio output."""

    def __init__(
        self,
        bus: EventBus | None = None,
        music_engine: DynamicMusicEngine | None = None,
    ) -> None:
        self.bus = bus if bus is not None else event_bus
        self.music_engine: DynamicMusicEngine = (
            music_engine if music_engine is not None else DynamicMusicEngine()
        )
        self.initialized: bool = False
        self._sounds: dict[AudioCue, pygame.mixer.Sound] = {}
        self._init_mixer()
        self.bus.subscribe(AudioCueEvent, self.handle_audio_event)

    def _init_mixer(self) -> None:
        """Initialize the Pygame audio mixer and procedural cue sounds."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.initialized = True
            self._generate_procedural_sounds()
        except (pygame.error, Exception) as e:
            # Running in environments without an audio device (e.g. CI/headless)
            self.initialized = False

    def _generate_procedural_sounds(self) -> None:
        """Synthesize short procedural waveform cues without requiring disk files."""
        if not self.initialized:
            return

        def make_tone(freq: float, duration_ms: int, volume: float = 0.25) -> pygame.mixer.Sound:
            sample_rate = 22050
            num_samples = int(sample_rate * (duration_ms / 1000.0))
            buf = array.array("h")
            amplitude = int(32767 * volume)
            for i in range(num_samples):
                t = i / sample_rate
                # Sine wave with exponential decay
                decay = math.exp(-3.0 * (i / num_samples))
                val = int(amplitude * decay * math.sin(2.0 * math.pi * freq * t))
                buf.append(max(-32768, min(32767, val)))
            return pygame.mixer.Sound(buffer=buf)

        try:
            self._sounds[AudioCue.HIT] = make_tone(180, 80, 0.3)
            self._sounds[AudioCue.CRIT] = make_tone(320, 140, 0.4)
            self._sounds[AudioCue.HEAL] = make_tone(520, 200, 0.25)
            self._sounds[AudioCue.CLICK] = make_tone(440, 40, 0.15)
            self._sounds[AudioCue.VICTORY] = make_tone(660, 300, 0.35)
            self._sounds[AudioCue.DEFEAT] = make_tone(110, 400, 0.35)
            self._sounds[AudioCue.CHEST] = make_tone(480, 160, 0.25)
            self._sounds[AudioCue.DOOR] = make_tone(220, 120, 0.2)
        except Exception:
            pass

    def handle_audio_event(self, event: AudioCueEvent) -> None:
        """Callback handling incoming AudioCueEvent."""
        self.play_cue(event.cue)

    def play_cue(self, cue: AudioCue) -> None:
        """Trigger audio cue sound."""
        if not self.initialized or not pygame.mixer.get_init():
            return
        sound = self._sounds.get(cue)
        if sound:
            try:
                sound.play()
            except (pygame.error, Exception):
                pass

    def set_music_context(self, context: MusicContext | None, force_restart: bool = False) -> None:
        """Delegate music context switch to internal DynamicMusicEngine."""
        self.music_engine.set_context(context, force_restart=force_restart)

    def update(self, dt: float) -> None:
        """Advance internal DynamicMusicEngine timers and loop detection."""
        self.music_engine.update(dt)

    def toggle_mute(self) -> bool:
        """Toggle music mute state and persist."""
        return self.music_engine.toggle_mute()

    def is_muted(self) -> bool:
        """Return True if background music is muted."""
        return self.music_engine.is_muted()
