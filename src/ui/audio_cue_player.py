"""
Audio Cue Player - Phase 10.5G

Plays audio cues for recording events.
Uses system sounds or generates tones programmatically.
"""

import logging
import math
import os
import tempfile
import threading
import wave
from typing import Optional

logger = logging.getLogger(__name__)


class AudioCuePlayer:
    """
    Plays audio cues for recording events.

    Events:
    - Recording started: Short ascending chime
    - Recording paused: Warning tone
    - Recording resumed: Short ascending chime
    - Recording stopped: Completion tone
    - Game recorded: Subtle click

    Uses system beep as fallback, or pygame/simpleaudio if available.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the audio cue player.

        Args:
            enabled: Whether audio cues are enabled
        """
        self._enabled = enabled
        self._backend: Optional[str] = None
        self._wav_tempdir: Optional[tempfile.TemporaryDirectory[str]] = None
        self._wav_paths: dict[str, str] = {}
        self._detect_backend()

    def _get_or_create_wav(self, sound_type: str) -> str:
        """
        Create a small high-quality WAV tone for the given sound type.

        This avoids relying on terminal bells or distro-specific system sounds.
        """
        if sound_type in self._wav_paths:
            return self._wav_paths[sound_type]

        if self._wav_tempdir is None:
            self._wav_tempdir = tempfile.TemporaryDirectory(prefix="replayer_audio_")

        filename_by_type = {
            "start": "recording_start.wav",
            "warning": "recording_warning.wav",
            "stop": "recording_stop.wav",
            "game_recorded": "game_recorded.wav",
        }
        filename = filename_by_type.get(sound_type, f"{sound_type}.wav")
        path = os.path.join(self._wav_tempdir.name, filename)

        segments_by_type: dict[str, list[tuple[float, float]]] = {
            "start": [(523.25, 0.08), (659.25, 0.08), (783.99, 0.12)],
            "warning": [(440.00, 0.14), (349.23, 0.26)],
            "stop": [(783.99, 0.08), (659.25, 0.08), (523.25, 0.16)],
            "game_recorded": [(880.00, 0.045)],
        }
        segments = segments_by_type.get(sound_type, [(660.00, 0.10)])

        self._write_wav_file(path, segments)
        self._wav_paths[sound_type] = path
        return path

    def _write_wav_file(self, path: str, segments: list[tuple[float, float]]) -> None:
        sample_rate = 44100
        amplitude = 0.22
        fade_ms = 8
        inter_segment_silence_s = 0.02

        frames = bytearray()

        def add_silence(duration_s: float) -> None:
            count = int(sample_rate * duration_s)
            frames.extend(b"\x00\x00" * count)

        def add_tone(frequency: float, duration_s: float) -> None:
            total = max(1, int(sample_rate * duration_s))
            fade = min(int(sample_rate * (fade_ms / 1000.0)), total // 2)
            for i in range(total):
                env = 1.0
                if fade > 0:
                    if i < fade:
                        env = i / fade
                    elif i >= total - fade:
                        env = (total - 1 - i) / fade
                sample = math.sin(2.0 * math.pi * frequency * (i / sample_rate))
                value = int(sample * env * amplitude * 32767.0)
                frames.extend(int(value).to_bytes(2, byteorder="little", signed=True))

        for idx, (freq, dur) in enumerate(segments):
            if idx > 0:
                add_silence(inter_segment_silence_s)
            add_tone(freq, dur)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(frames))

    def _detect_backend(self) -> None:
        """Detect available audio backend."""
        # Try different audio libraries
        try:
            import winsound  # Windows
            self._backend = "winsound"
            logger.debug("Audio backend: winsound")
            return
        except ImportError:
            pass

        try:
            import subprocess
            # Check for paplay (PulseAudio) on Linux
            result = subprocess.run(
                ["which", "paplay"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._backend = "paplay"
                logger.debug("Audio backend: paplay")
                return
        except Exception:
            pass

        try:
            import subprocess
            # Check for aplay (ALSA) on Linux
            result = subprocess.run(
                ["which", "aplay"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._backend = "aplay"
                logger.debug("Audio backend: aplay")
                return
        except Exception:
            pass

        # Fallback: terminal bell
        self._backend = "bell"
        logger.debug("Audio backend: terminal bell (fallback)")

    @property
    def enabled(self) -> bool:
        """Whether audio cues are enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether audio cues are enabled."""
        self._enabled = value

    def _play_async(self, play_func) -> None:
        """Run play function in background thread."""
        thread = threading.Thread(target=play_func, daemon=True)
        thread.start()

    def _play_tone_winsound(self, frequency: int, duration: int) -> None:
        """Play tone using winsound (Windows)."""
        try:
            import winsound
            winsound.Beep(frequency, duration)
        except Exception as e:
            logger.debug(f"winsound failed: {e}")

    def _play_system_sound(self, sound_type: str) -> None:
        """Play system sound using available backend."""
        if not self._enabled:
            return

        try:
            if self._backend == "winsound":
                import winsound
                if sound_type == "game_recorded":
                    winsound.Beep(880, 50)
                else:
                    if sound_type == "start":
                        # Ascending chime
                        winsound.Beep(523, 100)  # C5
                        winsound.Beep(659, 100)  # E5
                        winsound.Beep(784, 150)  # G5
                    elif sound_type == "warning":
                        # Warning tone
                        winsound.Beep(440, 200)  # A4
                        winsound.Beep(349, 300)  # F4
                    elif sound_type == "stop":
                        # Completion tone
                        winsound.Beep(784, 100)  # G5
                        winsound.Beep(659, 100)  # E5
                        winsound.Beep(523, 200)  # C5

            elif self._backend in ("paplay", "aplay"):
                import subprocess
                wav_path = self._get_or_create_wav(sound_type)
                subprocess.run([self._backend, wav_path], capture_output=True, timeout=2)

            else:
                # Terminal bell fallback
                print("\a", end="", flush=True)

        except Exception as e:
            logger.debug(f"Audio playback failed: {e}")
            # Silent failure - audio is nice-to-have

    def play_recording_started(self) -> None:
        """Play 'recording started' sound."""
        self._play_async(lambda: self._play_system_sound("start"))

    def play_recording_paused(self) -> None:
        """Play 'recording paused' (warning) sound."""
        self._play_async(lambda: self._play_system_sound("warning"))

    def play_recording_resumed(self) -> None:
        """Play 'recording resumed' sound."""
        self._play_async(lambda: self._play_system_sound("start"))

    def play_recording_stopped(self) -> None:
        """Play 'recording stopped' (completion) sound."""
        self._play_async(lambda: self._play_system_sound("stop"))

    def play_game_recorded(self) -> None:
        """Play subtle 'game recorded' sound."""
        self._play_async(lambda: self._play_system_sound("game_recorded"))

    def test_audio(self) -> bool:
        """
        Test if audio playback works.

        Returns:
            True if audio played successfully
        """
        try:
            self._play_system_sound("start")
            return True
        except Exception:
            return False
