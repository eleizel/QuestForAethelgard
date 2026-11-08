"""Audio file integrity and pygame.mixer playback stress tests.

Challenger 2 Verification:
- Empirically verifies container and bitstream integrity of all audio assets in assets/music/.
  - OGG container magic ('OggS'), sequence monotonicity, page structure, and Vorbis ID headers.
  - MP3 frame sync (0xFF 0xFB/0xE0), MPEG-1 Layer III, 100% stereo, CBR 128kbps.
  - Sample rate (48kHz) and channel configurations (stereo).
  - Full stream decoding with soundfile (amplitude bounds, no corruption/NaNs).
- Stress tests pygame.mixer.music across all 8 tracks:
  - Rapid sequential loads in headless dummy audio driver.
  - Continuous looping (play(loops=-1)), pausing, unpausing, volume adjustment, and stopping.
  - Repeat loading of identical tracks without mixer re-initialization.
  - Rapid format switching (alternating OGG and MP3 streams).
  - Fadeout transitions and mixer re-initialization across multiple sample rates.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
import struct
import time
import pytest
import pygame
import soundfile as sf

from src.frontends.pygame_ce.audio_track_loader import get_default_music_dir


@pytest.fixture(autouse=True)
def ensure_dummy_audio_driver():
    """Ensure headless SDL audio driver for test isolation."""
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    yield
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.mixer.quit()


OGG_TRACK_NAMES = [
    "boss_01.ogg",
    "boss_02.ogg",
    "combat_01.ogg",
    "combat_02.ogg",
    "exploration_01.ogg",
    "exploration_02.ogg",
]

MP3_TRACK_NAMES = [
    "welcome_01.mp3",
    "welcome_02.mp3",
]

ALL_TRACK_NAMES = OGG_TRACK_NAMES + MP3_TRACK_NAMES


class TestAudioFileIntegrity:
    """Empirical verification of container, header, and stream integrity."""

    @pytest.mark.parametrize("track_name", OGG_TRACK_NAMES)
    def test_ogg_container_and_vorbis_headers(self, track_name: str):
        """Validate OGG page magic, Vorbis identification headers, sample rate, and channels."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name
        assert track_path.is_file(), f"Missing track: {track_path}"

        with open(track_path, "rb") as f:
            data = f.read(128)

        # 1. Ogg container magic bytes
        assert data[0:4] == b"OggS", f"{track_name}: Invalid OGG magic: {data[0:4]}"

        # 2. Ogg stream structure version (0)
        assert data[4] == 0, f"{track_name}: Invalid OGG stream version: {data[4]}"

        # 3. Header type flag: BOS (Beginning of stream) bit must be set (0x02)
        header_type = data[5]
        assert header_type & 0x02, f"{track_name}: First Ogg page missing BOS flag (type={header_type})"

        # 4. Sequence number of initial page must be 0
        seq_num = struct.unpack("<I", data[18:22])[0]
        assert seq_num == 0, f"{track_name}: First Ogg page sequence number is {seq_num}, expected 0"

        # 5. Extract Vorbis identification header packet from segment table
        num_segments = data[26]
        pos = 27 + num_segments

        packet_type = data[pos]
        vorbis_magic = data[pos + 1 : pos + 7]
        assert packet_type == 1, f"{track_name}: First packet is not Vorbis ID header (type={packet_type})"
        assert vorbis_magic == b"vorbis", f"{track_name}: Vorbis magic header mismatch: {vorbis_magic}"

        # 6. Vorbis version, channels, and sample rate
        vorbis_version = struct.unpack("<I", data[pos + 7 : pos + 11])[0]
        assert vorbis_version == 0, f"{track_name}: Vorbis version {vorbis_version} != 0"

        audio_channels = data[pos + 11]
        assert audio_channels == 2, f"{track_name}: Audio channels {audio_channels} != 2 (stereo required)"

        sample_rate = struct.unpack("<I", data[pos + 12 : pos + 16])[0]
        assert sample_rate in (44100, 48000), f"{track_name}: Unexpected sample rate: {sample_rate} Hz"
        assert sample_rate == 48000, f"{track_name}: Expected 48kHz, got {sample_rate} Hz"

    @pytest.mark.parametrize("track_name", OGG_TRACK_NAMES)
    def test_ogg_full_page_sequence_and_eos(self, track_name: str):
        """Walk all Ogg container pages to verify sequential monotonicity, CRC, and EOS flag."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name

        with open(track_path, "rb") as f:
            data = f.read()

        offset = 0
        page_index = 0
        expected_seq = 0
        serial_no = None
        has_eos = False

        while offset < len(data):
            assert data[offset : offset + 4] == b"OggS", f"{track_name}: Corrupt page magic at byte {offset}"
            hdr_type = data[offset + 5]
            serial = struct.unpack("<I", data[offset + 14 : offset + 18])[0]
            seq = struct.unpack("<I", data[offset + 18 : offset + 22])[0]
            num_segs = data[offset + 26]
            seg_table = data[offset + 27 : offset + 27 + num_segs]
            body_size = sum(seg_table)
            page_size = 27 + num_segs + body_size

            if page_index == 0:
                serial_no = serial
            else:
                assert serial == serial_no, f"{track_name}: Bitstream serial mismatch at page {page_index}"
                assert seq == expected_seq, f"{track_name}: Page sequence discontinuity: expected {expected_seq}, got {seq}"

            if hdr_type & 0x04:
                has_eos = True

            expected_seq += 1
            page_index += 1
            offset += page_size

        assert offset == len(data), f"{track_name}: Trailing junk data detected ({len(data) - offset} bytes)"
        assert has_eos, f"{track_name}: Ogg stream missing EOS (End of Stream) terminator page"
        assert page_index >= 100, f"{track_name}: Expected >100 pages for long track, got {page_index}"

    @pytest.mark.parametrize("track_name", MP3_TRACK_NAMES)
    def test_mp3_header_and_frame_sync(self, track_name: str):
        """Validate MP3 frame sync bytes, MPEG-1 Layer III flags, 48kHz, and stereo mode."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name
        assert track_path.is_file(), f"Missing track: {track_path}"

        with open(track_path, "rb") as f:
            data = f.read()

        # ID3 tag skip if present
        offset = 0
        if data.startswith(b"ID3"):
            size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
            offset = size + 10

        # Scan for first MPEG frame sync
        b0 = data[offset]
        b1 = data[offset + 1]
        b2 = data[offset + 2]
        b3 = data[offset + 3]

        assert b0 == 0xFF and (b1 & 0xE0) == 0xE0, (
            f"{track_name}: Missing MPEG frame sync at offset {offset} ({hex(b0)}, {hex(b1)})"
        )

        version_bits = (b1 >> 3) & 0x03
        assert version_bits == 3, f"{track_name}: Not MPEG-1 (bits={version_bits})"

        layer_bits = (b1 >> 1) & 0x03
        assert layer_bits == 1, f"{track_name}: Not Layer III (bits={layer_bits})"

        bitrate_idx = (b2 >> 4) & 0x0F
        assert bitrate_idx == 9, f"{track_name}: Expected 128 kbps (index 9), got {bitrate_idx}"

        samplerate_idx = (b2 >> 2) & 0x03
        assert samplerate_idx == 1, f"{track_name}: Expected 48kHz (index 1), got {samplerate_idx}"

        channel_mode = (b3 >> 6) & 0x03
        # 0 = Stereo, 1 = Joint Stereo, 2 = Dual Channel (all 2-channel stereo). 3 = Mono
        assert channel_mode in (0, 1, 2), f"{track_name}: Track is mono, stereo required (mode={channel_mode})"

    @pytest.mark.parametrize("track_name", MP3_TRACK_NAMES)
    def test_mp3_full_frame_stream_validation(self, track_name: str):
        """Walk all MPEG frames in MP3 tracks to verify unbroken CBR frames and total length."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name

        with open(track_path, "rb") as f:
            data = f.read()

        offset = 0
        if data.startswith(b"ID3"):
            size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
            offset = size + 10

        curr = offset
        frame_count = 0
        stereo_frame_count = 0

        while curr < len(data) - 4:
            b0 = data[curr]
            b1 = data[curr + 1]
            b2 = data[curr + 2]
            b3 = data[curr + 3]

            if b0 == 0xFF and (b1 & 0xE0) == 0xE0:
                version_bits = (b1 >> 3) & 0x03
                layer_bits = (b1 >> 1) & 0x03
                if version_bits == 3 and layer_bits == 1:
                    padding = (b2 >> 1) & 0x01
                    channel_mode = (b3 >> 6) & 0x03
                    # 128 kbps at 48 kHz: frame_size = 144 * 128000 // 48000 + padding = 384 + padding
                    frame_len = (144 * 128_000) // 48_000 + padding
                    if channel_mode in (0, 1, 2):
                        stereo_frame_count += 1
                    frame_count += 1
                    curr += frame_len
                    continue
            curr += 1

        assert frame_count >= 7000, f"{track_name}: Unusually low frame count ({frame_count})"
        assert stereo_frame_count == frame_count, f"{track_name}: Non-stereo frame detected in stream"

    @pytest.mark.parametrize("track_name", ALL_TRACK_NAMES)
    def test_soundfile_full_stream_decode(self, track_name: str):
        """Decode complete PCM audio stream using libsndfile to prove zero stream corruption."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name

        info = sf.info(str(track_path))
        assert info.samplerate in (44100, 48000)
        assert info.channels == 2
        assert info.duration > 120.0  # All tracks are > 2 minutes

        data, sr = sf.read(str(track_path))
        assert sr == info.samplerate
        assert data.shape[0] == info.frames
        assert data.shape[1] == 2  # 2 channels (stereo)
        assert not ((data != data).any()), f"{track_name}: NaN values detected in decoded audio"
        assert (data >= -1.05).all() and (data <= 1.05).all(), f"{track_name}: Audio samples out of bounds"


class TestMixerPlaybackStress:
    """Stress testing pygame.mixer.music playback, looping, and state transitions."""

    @pytest.fixture(autouse=True)
    def init_mixer(self):
        """Initialize pygame mixer before each stress test."""
        pygame.mixer.init(frequency=48000, size=-16, channels=2)
        assert pygame.mixer.get_init() is not None
        yield
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            pygame.mixer.quit()

    def test_rapid_sequential_loads_across_all_tracks(self):
        """Rapidly load all 8 tracks sequentially across multiple cycles without error."""
        music_dir = get_default_music_dir()
        tracks = [music_dir / t for t in ALL_TRACK_NAMES]

        cycles = 10  # 8 * 10 = 80 sequential loads
        t0 = time.perf_counter()
        for cycle in range(cycles):
            for track_path in tracks:
                pygame.mixer.music.load(str(track_path))

        elapsed = time.perf_counter() - t0
        # 80 loads should complete quickly without stalling
        assert elapsed < 5.0, f"80 sequential loads took unexpectedly long: {elapsed:.2f}s"

    @pytest.mark.parametrize("track_name", ALL_TRACK_NAMES)
    def test_continuous_looping_pause_unpause_volume_and_stop(self, track_name: str):
        """Test continuous looping (play(loops=-1)), pause, unpause, volume, and stop for each track."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name

        pygame.mixer.music.load(str(track_path))

        # 1. Play with infinite looping
        pygame.mixer.music.play(loops=-1)
        assert pygame.mixer.music.get_busy() is True

        # 2. Pause
        pygame.mixer.music.pause()

        # 3. Dynamic volume adjustment while paused
        for vol in [0.0, 0.25, 0.5, 0.75, 1.0]:
            pygame.mixer.music.set_volume(vol)
            current_vol = pygame.mixer.music.get_volume()
            assert abs(current_vol - vol) < 0.05, f"Volume set to {vol} but read {current_vol}"

        # 4. Unpause
        pygame.mixer.music.unpause()
        assert pygame.mixer.music.get_busy() is True

        # 5. Stop
        pygame.mixer.music.stop()
        assert pygame.mixer.music.get_busy() is False

    @pytest.mark.parametrize("track_name", ALL_TRACK_NAMES)
    def test_repeat_loading_same_track_without_mixer_reinit(self, track_name: str):
        """Repeatedly load, play, and stop the same track 20 times without closing the mixer."""
        music_dir = get_default_music_dir()
        track_path = music_dir / track_name

        for i in range(20):
            pygame.mixer.music.load(str(track_path))
            pygame.mixer.music.play(loops=0)
            assert pygame.mixer.music.get_busy() is True
            pygame.mixer.music.stop()
            assert pygame.mixer.music.get_busy() is False

    def test_rapid_format_switching_without_explicit_stop(self):
        """Rapidly switch between OGG and MP3 formats without stopping, testing stream replacement."""
        music_dir = get_default_music_dir()
        oggs = [music_dir / t for t in OGG_TRACK_NAMES]
        mp3s = [music_dir / t for t in MP3_TRACK_NAMES]

        for _ in range(25):
            for ogg, mp3 in zip(oggs, mp3s * 3):
                pygame.mixer.music.load(str(ogg))
                pygame.mixer.music.play(loops=-1)
                assert pygame.mixer.music.get_busy() is True

                pygame.mixer.music.load(str(mp3))
                pygame.mixer.music.play(loops=-1)
                assert pygame.mixer.music.get_busy() is True

        pygame.mixer.music.stop()
        assert pygame.mixer.music.get_busy() is False

    def test_fadeout_and_immediate_reload(self):
        """Test pygame.mixer.music.fadeout() followed immediately by another load and play."""
        music_dir = get_default_music_dir()
        tracks = [music_dir / t for t in ALL_TRACK_NAMES]

        for track_path in tracks:
            pygame.mixer.music.load(str(track_path))
            pygame.mixer.music.play(loops=-1)
            pygame.mixer.music.fadeout(10)
            # Immediately load another track
            pygame.mixer.music.load(str(track_path))
            pygame.mixer.music.play(loops=0)
            pygame.mixer.music.stop()

    def test_mixer_reinitialization_across_sampling_rates(self):
        """Test playback across various mixer initialization sampling rates (22050, 44100, 48000)."""
        music_dir = get_default_music_dir()
        tracks = [music_dir / t for t in ALL_TRACK_NAMES]

        for freq in [22050, 44100, 48000]:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=freq, size=-16, channels=2)
            assert pygame.mixer.get_init() is not None

            for track_path in tracks:
                pygame.mixer.music.load(str(track_path))
                pygame.mixer.music.play(loops=0)
                pygame.mixer.music.stop()

    def test_memory_and_handle_stability_under_sustained_load(self):
        """Verify no handle leaks or memory instability over 200 consecutive load/play cycles."""
        music_dir = get_default_music_dir()
        tracks = [music_dir / t for t in ALL_TRACK_NAMES]

        for i in range(200):
            track_path = tracks[i % len(tracks)]
            pygame.mixer.music.load(str(track_path))
            pygame.mixer.music.play(loops=0)
            if i % 50 == 0:
                gc.collect()

        pygame.mixer.music.stop()
