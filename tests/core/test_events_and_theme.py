"""Unit tests for Phase 1 decoupling: EventBus, AudioCue, and Semantic Theme tokens."""

import pytest
from src.core.events import EventBus, DomainEvent, AudioCue, AudioCueEvent
from src.core.theme import ThemeToken, resolve_pyxel_color, resolve_rgb_color, PYXEL_THEME_MAP
from src.ui.audio_adapter import PyxelAudioAdapter, CUE_SFX_MAP
from src.config import SND_HIT, SND_CRIT, SND_VICTORY


class SampleDomainEvent(DomainEvent):
    def __init__(self, message: str) -> None:
        self.message = message


def test_event_bus_emit_and_drain():
    """EventBus stores emitted events in order and drains them completely."""
    bus = EventBus()
    assert bus.drain() == []

    e1 = SampleDomainEvent("first")
    e2 = SampleDomainEvent("second")
    bus.emit(e1)
    bus.emit(e2)

    drained = bus.drain()
    assert len(drained) == 2
    assert drained[0] == e1
    assert drained[1] == e2

    # Queue should now be empty
    assert bus.drain() == []


def test_event_bus_subscription():
    """Immediate subscribers receive events synchronously when emitted."""
    bus = EventBus()
    received = []

    bus.subscribe(SampleDomainEvent, lambda ev: received.append(ev.message))
    bus.emit(SampleDomainEvent("event_1"))
    bus.emit(SampleDomainEvent("event_2"))

    assert received == ["event_1", "event_2"]


def test_event_bus_emit_audio_helper():
    """emit_audio wraps AudioCue inside an AudioCueEvent."""
    bus = EventBus()
    bus.emit_audio(AudioCue.CRIT)

    drained = bus.drain()
    assert len(drained) == 1
    assert isinstance(drained[0], AudioCueEvent)
    assert drained[0].cue == AudioCue.CRIT


def test_audio_adapter_translates_cues():
    """PyxelAudioAdapter catches AudioCueEvents and routes to audio.play_sfx."""
    bus = EventBus()
    adapter = PyxelAudioAdapter(bus=bus)
    adapter.attach()

    played = []

    # Mock audio driver
    class MockAudio:
        @staticmethod
        def play_sfx(sfx_id: int):
            played.append(sfx_id)

    import src.ui.audio_adapter as adapter_module
    orig_audio = adapter_module.audio
    adapter_module.audio = MockAudio()

    try:
        bus.emit_audio(AudioCue.HIT)
        bus.emit_audio(AudioCue.CRIT)
        bus.emit_audio(AudioCue.VICTORY)

        assert played == [SND_HIT, SND_CRIT, SND_VICTORY]
    finally:
        adapter_module.audio = orig_audio


def test_theme_token_resolution():
    """Semantic tokens resolve correctly to both Pyxel palette index and RGB tuples."""
    assert resolve_pyxel_color(ThemeToken.TEXT_NORMAL) == 7
    assert resolve_pyxel_color(ThemeToken.HP_FILL) == 8

    # Check RGB resolution
    rgb = resolve_rgb_color(ThemeToken.TEXT_NORMAL)
    assert rgb == (255, 255, 255)

    alert_rgb = resolve_rgb_color(ThemeToken.TEXT_ALERT)
    assert alert_rgb == (255, 0, 77)
