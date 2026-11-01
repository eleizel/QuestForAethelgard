"""Audio adapter connecting domain audio cues to the Pyxel audio engine."""

from __future__ import annotations

from src.core.events import AudioCue, AudioCueEvent, event_bus
from src.core.audio import audio
from src.config import (
    SND_HIT,
    SND_CRIT,
    SND_HEAL,
    SND_CLICK,
    SND_VICTORY,
    SND_DEFEAT,
    SND_CHEST,
    SND_DOOR,
)

CUE_SFX_MAP: dict[AudioCue, int] = {
    AudioCue.HIT: SND_HIT,
    AudioCue.CRIT: SND_CRIT,
    AudioCue.HEAL: SND_HEAL,
    AudioCue.CLICK: SND_CLICK,
    AudioCue.VICTORY: SND_VICTORY,
    AudioCue.DEFEAT: SND_DEFEAT,
    AudioCue.CHEST: SND_CHEST,
    AudioCue.DOOR: SND_DOOR,
}


class PyxelAudioAdapter:
    """Listens for domain AudioCueEvents and translates them to Pyxel audio playback."""

    def __init__(self, bus=event_bus) -> None:
        self.bus = bus
        self._subscribed = False

    def attach(self) -> None:
        """Subscribe to the event bus."""
        if not self._subscribed:
            self.bus.subscribe(AudioCueEvent, self._handle_audio_event)
            self._subscribed = True

    def _handle_audio_event(self, event: AudioCueEvent) -> None:
        sfx_id = CUE_SFX_MAP.get(event.cue)
        if sfx_id is not None:
            audio.play_sfx(sfx_id)


# Global adapter instance
audio_adapter = PyxelAudioAdapter()
