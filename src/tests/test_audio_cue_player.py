"""Tests for AudioCuePlayer."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

from ui.audio_cue_player import AudioCuePlayer


class _InlineThread:
    def __init__(self, *, target: Callable[[], None], daemon: bool = False):
        self._target = target
        self._daemon = daemon

    def start(self) -> None:
        self._target()


def _subprocess_run_side_effect(cmd: list[str], **_kwargs: Any) -> Any:
    if cmd[:2] == ["which", "paplay"]:
        return SimpleNamespace(returncode=0, stdout="/usr/bin/paplay\n", stderr="")
    if cmd[:2] == ["which", "aplay"]:
        return SimpleNamespace(returncode=1, stdout="", stderr="")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


class TestAudioCuePlayer:
    """Audio cue playback should prefer bundled WAV cues on Linux."""

    def test_paplay_backend_uses_custom_wav_for_start(self) -> None:
        with (
            patch("subprocess.run", side_effect=_subprocess_run_side_effect) as mock_run,
            patch("ui.audio_cue_player.threading.Thread", _InlineThread),
        ):
            player = AudioCuePlayer(enabled=True)
            player.play_recording_started()

        play_calls = [
            call for call in mock_run.call_args_list if call.args[0][0] == "paplay"
        ]
        assert play_calls, "expected a paplay playback call"
        assert play_calls[-1].args[0][1].endswith("recording_start.wav")

    def test_paplay_backend_uses_custom_wav_for_game_recorded(self) -> None:
        with (
            patch("subprocess.run", side_effect=_subprocess_run_side_effect) as mock_run,
            patch("ui.audio_cue_player.threading.Thread", _InlineThread),
        ):
            player = AudioCuePlayer(enabled=True)
            player.play_game_recorded()

        play_calls = [
            call for call in mock_run.call_args_list if call.args[0][0] == "paplay"
        ]
        assert play_calls, "expected a paplay playback call"
        assert play_calls[-1].args[0][1].endswith("game_recorded.wav")
