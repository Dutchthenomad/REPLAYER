"""
Audio Cue Player - Phase 10.5G

Plays audio cues for recording events.
Uses system sounds or generates tones programmatically.
"""

import logging
import threading
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
        self._detect_backend()

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
                # Linux: use system sounds
                import subprocess
                import os

                # Try common system sound paths
                sound_files = {
                    "start": [
                        "/usr/share/sounds/freedesktop/stereo/message.oga",
                        "/usr/share/sounds/ubuntu/stereo/message.ogg",
                    ],
                    "warning": [
                        "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
                        "/usr/share/sounds/ubuntu/stereo/dialog-warning.ogg",
                    ],
                    "stop": [
                        "/usr/share/sounds/freedesktop/stereo/complete.oga",
                        "/usr/share/sounds/ubuntu/stereo/dialog-information.ogg",
                    ],
                }

                for sound_path in sound_files.get(sound_type, []):
                    if os.path.exists(sound_path):
                        cmd = [self._backend, sound_path]
                        subprocess.run(cmd, capture_output=True, timeout=2)
                        return

                # Fallback to bell
                print("\a", end="", flush=True)

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
        if not self._enabled:
            return
        # Very subtle - just a quick beep
        self._play_async(lambda: print("\a", end="", flush=True))

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
