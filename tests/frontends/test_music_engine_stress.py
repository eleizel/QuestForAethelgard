"""Empirical stress and robustness test harness for DynamicMusicEngine.

Challenger 1 Verification Suite:
1. Empirical statistical test: 500 transitions per context (WELCOME, MAP, COMBAT, BOSS),
   verifying binomial fairness [150, 350] per track.
2. High-frequency context thrashing: 200 rapid context switches in <1.0 second.
3. Loop re-selection stress: simulate 100 track end events in update(dt) verifying track
   re-selection strictly within active context with zero context leakage.
4. Robustness against degenerate inputs: negative dt, massive dt (10000.0, inf),
   calling stop/play/pause/unpause while paused or fading.
"""

from __future__ import annotations

import os
from pathlib import Path
import random
import time
from unittest.mock import MagicMock, patch

import pytest
import pygame

from src.core.persistence import MemoryStorageBackend
from src.frontends.pygame_ce.music_engine import (
    CONTEXT_TRACKS,
    AudioSettingsManager,
    DynamicMusicEngine,
    MusicContext,
    PlaybackState,
)


@pytest.fixture(autouse=True)
def ensure_dummy_audio_driver():
    """Ensure headless SDL audio and video drivers with clean mixer teardown."""
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass
    yield
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


@pytest.fixture
def memory_backend() -> MemoryStorageBackend:
    return MemoryStorageBackend()


@pytest.fixture
def audio_settings(memory_backend: MemoryStorageBackend) -> AudioSettingsManager:
    return AudioSettingsManager(backend=memory_backend)


@pytest.fixture
def engine(audio_settings: AudioSettingsManager) -> DynamicMusicEngine:
    eng = DynamicMusicEngine(settings_manager=audio_settings)
    yield eng
    eng.stop()


# =============================================================================
# 1. EMPIRICAL STATISTICAL TEST (500 TRANSITIONS PER CONTEXT)
# =============================================================================
class TestEmpiricalStatisticalFairness:
    """Stress-test binomial fairness of randomized track selection over N=500 iterations."""

    @pytest.mark.parametrize(
        "context",
        [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ],
    )
    def test_500_forced_transitions_binomial_fairness(
        self,
        engine: DynamicMusicEngine,
        context: MusicContext,
    ):
        """Run 500 forced transitions for a context and verify binomial fairness [150, 350]."""
        track_candidates = CONTEXT_TRACKS[context]
        assert len(track_candidates) == 2, f"Expected 2 tracks for {context}, got {track_candidates}"
        track_a, track_b = track_candidates

        counts = {track_a: 0, track_b: 0}
        n_trials = 500

        for _ in range(n_trials):
            engine.set_context(context, force_restart=True)
            chosen = engine.get_current_track()
            assert chosen in counts, f"Invalid track {chosen} chosen for {context}"
            counts[chosen] += 1

        assert counts[track_a] + counts[track_b] == n_trials
        # Binomial bounds check: [150, 350] out of 500 (~8.94 sigma bounds for p=0.5, sigma=11.18)
        assert 150 <= counts[track_a] <= 350, (
            f"Context {context.name} track '{track_a}' failed binomial fairness: "
            f"count={counts[track_a]} (expected between 150 and 350 out of 500)"
        )
        assert 150 <= counts[track_b] <= 350, (
            f"Context {context.name} track '{track_b}' failed binomial fairness: "
            f"count={counts[track_b]} (expected between 150 and 350 out of 500)"
        )

    @pytest.mark.parametrize(
        "context",
        [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ],
    )
    def test_500_direct_select_track_binomial_fairness(
        self,
        engine: DynamicMusicEngine,
        context: MusicContext,
    ):
        """Directly invoke _select_track 500 times per context and verify bounds [150, 350]."""
        track_a, track_b = CONTEXT_TRACKS[context]
        counts = {track_a: 0, track_b: 0}
        n_trials = 500

        for _ in range(n_trials):
            chosen = engine.choose_track(context)
            assert chosen in counts
            counts[chosen] += 1

        assert counts[track_a] + counts[track_b] == n_trials
        assert 150 <= counts[track_a] <= 350, (
            f"Direct selection for {context.name} '{track_a}' out of bounds: count={counts[track_a]}"
        )
        assert 150 <= counts[track_b] <= 350, (
            f"Direct selection for {context.name} '{track_b}' out of bounds: count={counts[track_b]}"
        )


# =============================================================================
# 2. HIGH-FREQUENCY CONTEXT THRASHING (200 SWITCHES IN <1 SECOND)
# =============================================================================
class TestHighFrequencyContextThrashing:
    """Stress-test high-frequency context switching under dummy audio driver."""

    def test_200_rapid_switches_under_one_second(self, engine: DynamicMusicEngine):
        """200 rapid context switches must execute in strictly less than 1.0 second."""
        contexts = [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ]

        # Pre-generate 200 alternating context requests
        switch_plan = [contexts[i % len(contexts)] for i in range(200)]

        t_start = time.perf_counter()
        for target_ctx in switch_plan:
            engine.set_context(target_ctx)
        t_elapsed = time.perf_counter() - t_start

        # State integrity checks
        expected_final_ctx = switch_plan[-1]
        assert engine.get_current_context() == expected_final_ctx
        assert engine.get_current_track() in CONTEXT_TRACKS[expected_final_ctx]
        assert engine.playback_state == PlaybackState.PLAYING
        assert engine.is_playing() is True

        # Performance constraint: strictly < 1.0 second
        assert t_elapsed < 1.0, f"200 context switches took {t_elapsed:.4f}s (exceeded 1.0s threshold)"

    def test_200_rapid_switches_with_force_restart_under_one_second(
        self,
        engine: DynamicMusicEngine,
    ):
        """200 switches with force_restart=True must execute in strictly less than 1.0 second."""
        contexts = [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ]
        switch_plan = [contexts[i % len(contexts)] for i in range(200)]

        t_start = time.perf_counter()
        for target_ctx in switch_plan:
            engine.set_context(target_ctx, force_restart=True)
        t_elapsed = time.perf_counter() - t_start

        expected_final_ctx = switch_plan[-1]
        assert engine.get_current_context() == expected_final_ctx
        assert engine.get_current_track() in CONTEXT_TRACKS[expected_final_ctx]
        assert t_elapsed < 1.0, (
            f"200 force-restart switches took {t_elapsed:.4f}s (exceeded 1.0s threshold)"
        )

    def test_200_rapid_switches_with_interleaved_updates(self, engine: DynamicMusicEngine):
        """200 cycles of context switch followed by frame update(0.016) in < 1.0 second."""
        contexts = [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ]

        t_start = time.perf_counter()
        for i in range(200):
            engine.set_context(contexts[i % len(contexts)])
            engine.update(dt=0.016)
        t_elapsed = time.perf_counter() - t_start

        assert engine.get_current_context() == contexts[-1]
        assert engine.playback_state == PlaybackState.PLAYING
        assert t_elapsed < 1.0, f"200 switches + updates took {t_elapsed:.4f}s (> 1.0s)"


# =============================================================================
# 3. LOOP RE-SELECTION STRESS (100 TRACK END EVENTS)
# =============================================================================
class TestLoopReSelectionStress:
    """Stress-test loop re-selection across 100 track end events in update(dt)."""

    @pytest.mark.parametrize(
        "context",
        [
            MusicContext.WELCOME,
            MusicContext.MAP,
            MusicContext.COMBAT,
            MusicContext.BOSS,
        ],
    )
    def test_100_track_end_events_strictly_within_context(
        self,
        engine: DynamicMusicEngine,
        context: MusicContext,
    ):
        """Simulate 100 track end events and verify re-selection is strictly within context."""
        engine.set_context(context)
        valid_tracks = set(CONTEXT_TRACKS[context])
        other_tracks = set()
        for ctx, tracks in CONTEXT_TRACKS.items():
            if ctx != context:
                other_tracks.update(tracks)

        counts = {track: 0 for track in valid_tracks}
        n_loop_events = 100

        # Mock get_busy to simulate track ending
        with patch("pygame.mixer.music.get_busy", return_value=False):
            for _ in range(n_loop_events):
                engine.update(dt=0.05)
                current_track = engine.get_current_track()
                assert current_track is not None
                assert current_track in valid_tracks, (
                    f"Context leak! Selected track '{current_track}' not in active context {context.name} tracks {valid_tracks}"
                )
                assert current_track not in other_tracks, (
                    f"Context leak! Selected track '{current_track}' belongs to other context"
                )
                assert engine.get_current_context() == context
                counts[current_track] += 1

        # Verify that over 100 loops both tracks were chosen (no stuck track)
        for track, count in counts.items():
            assert count > 0, f"Track {track} was never re-selected during 100 loop events"
            # 6-sigma check for N=100: each track should get between 15 and 85 selections
            assert 15 <= count <= 85, f"Track {track} loop selection count {count} is unbalanced"

    def test_100_pygame_custom_endevents(self, engine: DynamicMusicEngine):
        """Simulate 100 custom Pygame endevents via handle_event()."""
        custom_event_type = pygame.USEREVENT + 42
        engine.set_end_event(custom_event_type)
        engine.set_context(MusicContext.MAP)
        map_tracks = set(CONTEXT_TRACKS[MusicContext.MAP])

        fake_event = pygame.event.Event(custom_event_type)

        with patch("pygame.mixer.music.get_busy", return_value=False):
            for _ in range(100):
                engine.handle_event(fake_event)
                assert engine.get_current_context() == MusicContext.MAP
                assert engine.get_current_track() in map_tracks

    def test_busy_stream_never_triggers_reselection(self, engine: DynamicMusicEngine):
        """100 update(dt) calls while get_busy() is True must not re-select or reload track."""
        engine.set_context(MusicContext.COMBAT)
        initial_track = engine.get_current_track()

        with patch("pygame.mixer.music.get_busy", return_value=True), patch(
            "pygame.mixer.music.load"
        ) as mock_load, patch("pygame.mixer.music.play") as mock_play:
            for _ in range(100):
                engine.update(dt=0.1)

            mock_load.assert_not_called()
            mock_play.assert_not_called()
            assert engine.get_current_track() == initial_track


# =============================================================================
# 4. ROBUSTNESS & DEGENERATE INPUTS
# =============================================================================
class TestRobustnessAndDegenerateInputs:
    """Stress-test negative dt, massive dt, stop/play while paused/fading, and invalid states."""

    def test_negative_dt_resilience(self, engine: DynamicMusicEngine):
        """Negative dt inputs must be clamped to 0.0 or handled safely without crashing."""
        engine.set_context(MusicContext.WELCOME)

        # Apply various negative dt values
        for bad_dt in [-0.0001, -1.0, -100.0, -10000.0]:
            engine.update(dt=bad_dt)
            assert engine.get_current_context() == MusicContext.WELCOME
            assert engine.playback_state == PlaybackState.PLAYING

    def test_massive_dt_resilience(self, engine: DynamicMusicEngine):
        """Massive dt inputs (10000.0, 1e9, inf) must execute without overflow or infinite loops."""
        engine.set_context(MusicContext.MAP)

        for large_dt in [10000.0, 1e6, 1e9, float("inf")]:
            engine.update(dt=large_dt)
            assert engine.get_current_context() == MusicContext.MAP

    def test_stop_while_paused(self, engine: DynamicMusicEngine):
        """Calling stop() while PAUSED transitions cleanly to STOPPED and clears track."""
        engine.set_context(MusicContext.WELCOME)
        assert engine.playback_state == PlaybackState.PLAYING

        engine.pause()
        assert engine.is_paused() is True
        assert engine.playback_state == PlaybackState.PAUSED

        engine.stop()
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None

        # Subsequent unpause() while STOPPED must be a no-op
        engine.unpause()
        assert engine.playback_state == PlaybackState.STOPPED

    def test_play_new_context_while_paused(self, engine: DynamicMusicEngine):
        """Calling set_context with a new context while PAUSED starts playing the new context."""
        engine.set_context(MusicContext.WELCOME)
        engine.pause()
        assert engine.is_paused() is True

        engine.set_context(MusicContext.COMBAT)
        assert engine.get_current_context() == MusicContext.COMBAT
        assert engine.get_current_track() in CONTEXT_TRACKS[MusicContext.COMBAT]
        assert engine.is_playing() is True
        assert engine.playback_state == PlaybackState.PLAYING

    def test_play_same_context_force_restart_while_paused(self, engine: DynamicMusicEngine):
        """Calling set_context with force_restart=True while PAUSED restarts playback."""
        engine.set_context(MusicContext.WELCOME)
        engine.pause()
        assert engine.is_paused() is True

        engine.set_context(MusicContext.WELCOME, force_restart=True)
        assert engine.is_playing() is True
        assert engine.playback_state == PlaybackState.PLAYING

    def test_stop_while_fading_cancels_fade_immediately(self, engine: DynamicMusicEngine):
        """Calling stop(fade_ms=0) while FADING_OUT immediately halts without waiting for timer."""
        engine.set_context(MusicContext.WELCOME)
        engine.stop(fade_ms=1000)
        assert engine.playback_state == PlaybackState.FADING_OUT

        # Immediate hard stop
        engine.stop(fade_ms=0)
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None

    def test_rapid_stop_pause_unpause_chaos_sequence(self, engine: DynamicMusicEngine):
        """Execute a chaotic sequence of stop, pause, unpause, and set_context calls."""
        operations = [
            lambda: engine.set_context(MusicContext.WELCOME),
            lambda: engine.pause(),
            lambda: engine.pause(),  # idempotent pause
            lambda: engine.unpause(),
            lambda: engine.unpause(),  # idempotent unpause
            lambda: engine.stop(fade_ms=500),
            lambda: engine.stop(fade_ms=0),
            lambda: engine.stop(),  # idempotent stop
            lambda: engine.pause(),  # pause when stopped
            lambda: engine.unpause(),  # unpause when stopped
            lambda: engine.set_context(MusicContext.MAP),
            lambda: engine.set_context(None),  # None context retention
            lambda: engine.set_context(MusicContext.BOSS, force_restart=True),
            lambda: engine.update(dt=0.016),
            lambda: engine.update(dt=-1.0),
            lambda: engine.update(dt=1000.0),
        ]

        # Execute 50 chaotic permutations
        rng = random.Random(42)
        for _ in range(50):
            op = rng.choice(operations)
            op()

        # Engine must still be functional
        engine.set_context(MusicContext.COMBAT, force_restart=True)
        assert engine.get_current_context() == MusicContext.COMBAT
        assert engine.get_current_track() in CONTEXT_TRACKS[MusicContext.COMBAT]
        assert engine.playback_state == PlaybackState.PLAYING


    def test_same_context_set_during_fadeout_edge_case(self, engine: DynamicMusicEngine):
        """Document behavior: setting same context while fading out is ignored and stops playback."""
        engine.set_context(MusicContext.WELCOME)
        assert engine.playback_state == PlaybackState.PLAYING

        # Initiate fadeout stop
        engine.stop(fade_ms=500)
        assert engine.playback_state == PlaybackState.FADING_OUT

        # Calling set_context for WELCOME while fading out returns early
        engine.set_context(MusicContext.WELCOME)
        assert engine.playback_state == PlaybackState.FADING_OUT

        # Update advances past fade duration
        with patch("pygame.mixer.music.get_busy", return_value=False):
            engine.update(dt=0.6)

        # Because _pending_track was None, state transitioned to STOPPED
        assert engine.playback_state == PlaybackState.STOPPED
        assert engine.get_current_track() is None


class TestAudioSettingsStress:
    """Stress tests on AudioSettingsManager persistence and volume clamping."""

    def test_500_rapid_mute_toggles(self, audio_settings: AudioSettingsManager):
        """Toggle mute 500 times in rapid succession and verify state consistency."""
        t_start = time.perf_counter()
        expected = False
        for _ in range(500):
            res = audio_settings.toggle_music_muted()
            expected = not expected
            assert res == expected
            assert audio_settings.is_music_muted() == expected
        t_elapsed = time.perf_counter() - t_start
        assert t_elapsed < 1.0, f"500 mute toggles took {t_elapsed:.4f}s"

    def test_settings_persistence_under_extreme_volume_inputs(
        self,
        audio_settings: AudioSettingsManager,
    ):
        """Verify volume clamping under extreme values (-999, 999, nan, inf)."""
        audio_settings.set_music_volume(-100.0)
        assert audio_settings.get_music_volume() == 0.0

        audio_settings.set_music_volume(100.0)
        assert audio_settings.get_music_volume() == 1.0

        audio_settings.set_music_volume(float("nan"))
        assert 0.0 <= audio_settings.get_music_volume() <= 1.0

        audio_settings.set_music_volume(float("inf"))
        assert 0.0 <= audio_settings.get_music_volume() <= 1.0


class TestContextResolutionStress:
    """Stress tests for resolve_music_context under adversarial session structures."""

    def test_resolve_music_context_robustness(self):
        """resolve_music_context handles None, empty objects, and corrupt sessions safely."""
        from src.core.game_state import GameMode
        from src.entities.enemy import EnemyTier
        from src.frontends.pygame_ce.music_engine import resolve_music_context

        # 1. None session
        assert resolve_music_context(None) is None

        # 2. Empty object
        class EmptySession:
            pass

        assert resolve_music_context(EmptySession()) is None

        # 3. Session with current_mode = None
        class SessionNoneMode:
            current_mode = None

        assert resolve_music_context(SessionNoneMode()) is None

        # 4. Session with COMBAT but combat is None
        class SessionCombatNone:
            current_mode = GameMode.COMBAT
            combat = None

        assert resolve_music_context(SessionCombatNone()) == MusicContext.COMBAT

        # 5. Session with COMBAT, combat.enemy is None
        class MockCombatNoEnemy:
            enemy = None

        class SessionCombatNoEnemy:
            current_mode = GameMode.COMBAT
            combat = MockCombatNoEnemy()

        assert resolve_music_context(SessionCombatNoEnemy()) == MusicContext.COMBAT

        # 6. Session with COMBAT, enemy.tier is ELITE or BOSS
        class MockEnemyElite:
            tier = EnemyTier.ELITE

        class MockCombatElite:
            enemy = MockEnemyElite()

        class SessionCombatElite:
            current_mode = GameMode.COMBAT
            combat = MockCombatElite()

        assert resolve_music_context(SessionCombatElite()) == MusicContext.BOSS

        class MockEnemyBoss:
            tier = EnemyTier.BOSS

        class MockCombatBoss:
            enemy = MockEnemyBoss()

        class SessionCombatBoss:
            current_mode = GameMode.COMBAT
            combat = MockCombatBoss()

        assert resolve_music_context(SessionCombatBoss()) == MusicContext.BOSS
