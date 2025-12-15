"""Tests for Debug Terminal UI."""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestDebugTerminal:
    """Test Debug Terminal window."""

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_creates_separate_window(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """Debug terminal creates separate Toplevel window."""
        from ui.debug_terminal import DebugTerminal

        parent = Mock()
        terminal = DebugTerminal(parent)

        mock_toplevel.assert_called_once_with(parent)

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_window_not_transient(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """Window is independent (not transient)."""
        from ui.debug_terminal import DebugTerminal

        mock_window = MagicMock()
        mock_toplevel.return_value = mock_window

        terminal = DebugTerminal(Mock())

        # Should NOT be transient (tied to parent)
        mock_window.transient.assert_not_called()

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_log_event_adds_to_display(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """Logging event adds to text display."""
        from ui.debug_terminal import DebugTerminal

        mock_window = MagicMock()
        mock_toplevel.return_value = mock_window

        terminal = DebugTerminal(Mock())
        terminal._log_text = MagicMock()

        event = {
            'event': 'gameStateUpdate',
            'data': {'price': 1.5},
            'timestamp': '2025-12-14T12:00:00'
        }
        terminal.log_event(event)

        terminal._log_text.insert.assert_called()

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_filter_by_event_type(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """Can filter events by type."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())
        terminal.set_filter('usernameStatus')

        assert terminal.current_filter == 'usernameStatus'

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_auth_only_filter(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """AUTH_ONLY filter shows only auth events."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())
        terminal.set_filter('AUTH_ONLY')

        assert terminal._is_filtered({'event': 'gameStateUpdate'}) is True
        assert terminal._is_filtered({'event': 'usernameStatus'}) is False
        assert terminal._is_filtered({'event': 'playerUpdate'}) is False

    @patch('ui.debug_terminal.ScrolledText')
    @patch('ui.debug_terminal.ttk')
    @patch('ui.debug_terminal.tk.StringVar')
    @patch('ui.debug_terminal.tk.Toplevel')
    def test_get_color_for_event(self, mock_toplevel, mock_stringvar, mock_ttk, mock_scrolled):
        """Events have correct colors."""
        from ui.debug_terminal import DebugTerminal

        terminal = DebugTerminal(Mock())

        assert terminal._get_event_color('gameStateUpdate') == '#888888'  # Gray
        assert terminal._get_event_color('usernameStatus') == '#00ff88'   # Green
        assert terminal._get_event_color('playerUpdate') == '#00ffff'     # Cyan
        assert terminal._get_event_color('unknownEvent') == '#ff4444'     # Red (novel)
