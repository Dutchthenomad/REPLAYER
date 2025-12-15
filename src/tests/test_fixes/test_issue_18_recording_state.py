"""
Issue #18 Fix Tests - Recording State Consistency

These tests specify the CORRECT behavior after the fix.
They should FAIL before the fix is applied.

Fix: ReplayController should use RecordingController instead of
ReplayEngine for recording state management.
"""

import inspect
import tkinter as tk
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_replay_controller_deps():
    """Create mock dependencies for ReplayController."""
    root = MagicMock(spec=tk.Tk)
    root.after = lambda delay, fn: fn()  # Execute immediately

    parent_window = MagicMock()
    replay_engine = MagicMock()
    replay_engine.auto_recording = False

    chart = MagicMock()
    config = MagicMock()
    config.FILES = {'recordings_dir': '/tmp/recordings'}

    play_button = MagicMock(spec=tk.Button)
    step_button = MagicMock(spec=tk.Button)
    reset_button = MagicMock(spec=tk.Button)
    bot_toggle_button = MagicMock(spec=tk.Button)
    speed_label = MagicMock(spec=tk.Label)

    recording_var = MagicMock(spec=tk.BooleanVar)
    recording_var.get.return_value = False

    toast = MagicMock()

    return {
        'root': root,
        'parent_window': parent_window,
        'replay_engine': replay_engine,
        'chart': chart,
        'config': config,
        'play_button': play_button,
        'step_button': step_button,
        'reset_button': reset_button,
        'bot_toggle_button': bot_toggle_button,
        'speed_label': speed_label,
        'recording_var': recording_var,
        'toast': toast,
        'log_callback': MagicMock(),
    }


class TestRecordingStateConsistency:
    """Tests that recording state is consistent across all components."""

    def test_replay_controller_has_recording_controller_param(self):
        """
        ReplayController.__init__ should accept a recording_controller parameter.

        This test fails if recording_controller is not a parameter.
        """
        from ui.controllers.replay_controller import ReplayController

        sig = inspect.signature(ReplayController.__init__)
        params = list(sig.parameters.keys())

        assert 'recording_controller' in params, \
            "ReplayController.__init__ should have recording_controller parameter"

    def test_toggle_recording_does_not_call_replay_engine(self, mock_replay_controller_deps):
        """
        toggle_recording() should NOT call replay_engine.enable_recording()
        or replay_engine.disable_recording().

        After fix: it should use recording_controller instead.
        """
        from ui.controllers.replay_controller import ReplayController

        deps = mock_replay_controller_deps
        recording_controller = MagicMock()
        recording_controller.is_active = False

        controller = ReplayController(
            root=deps['root'],
            parent_window=deps['parent_window'],
            replay_engine=deps['replay_engine'],
            chart=deps['chart'],
            config=deps['config'],
            play_button=deps['play_button'],
            step_button=deps['step_button'],
            reset_button=deps['reset_button'],
            bot_toggle_button=deps['bot_toggle_button'],
            speed_label=deps['speed_label'],
            recording_var=deps['recording_var'],
            toast=deps['toast'],
            log_callback=deps['log_callback'],
            recording_controller=recording_controller,  # NEW PARAM
        )

        # Toggle recording
        controller.toggle_recording()

        # AFTER FIX: Should NOT call legacy methods
        assert not deps['replay_engine'].enable_recording.called, \
            "toggle_recording should not call replay_engine.enable_recording()"
        assert not deps['replay_engine'].disable_recording.called, \
            "toggle_recording should not call replay_engine.disable_recording()"

    def test_toggle_recording_uses_recording_controller(self, mock_replay_controller_deps):
        """
        toggle_recording() should call recording_controller methods.
        """
        from ui.controllers.replay_controller import ReplayController

        deps = mock_replay_controller_deps
        recording_controller = MagicMock()
        recording_controller.is_active = False

        controller = ReplayController(
            root=deps['root'],
            parent_window=deps['parent_window'],
            replay_engine=deps['replay_engine'],
            chart=deps['chart'],
            config=deps['config'],
            play_button=deps['play_button'],
            step_button=deps['step_button'],
            reset_button=deps['reset_button'],
            bot_toggle_button=deps['bot_toggle_button'],
            speed_label=deps['speed_label'],
            recording_var=deps['recording_var'],
            toast=deps['toast'],
            log_callback=deps['log_callback'],
            recording_controller=recording_controller,
        )

        # Toggle recording ON
        controller.toggle_recording()

        # AFTER FIX: Should call recording_controller
        assert recording_controller.show_config_dialog.called or \
               recording_controller.start_session.called, \
               "toggle_recording should use recording_controller"
