"""
Session State Persistence

Manages persistent balance and session data across app restarts.
Automatically saves to ~/.config/replayer/session_state.json

Key Features:
- Balance persists across sessions
- P&L tracking accumulates
- Manual balance override support
- Configurable default balance
"""

import json
import logging
import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SessionState:
    """Persistent session state manager."""

    def __init__(self, config_dir: Optional[Path] = None, default_balance: Decimal = Decimal('0.01')):
        """
        Initialize session state.

        Args:
            config_dir: Directory for session_state.json (default: ~/.config/replayer)
            default_balance: Default balance for new sessions (default: 0.01 SOL)
        """
        self.default_balance = default_balance

        # Determine config directory
        if config_dir is None:
            config_dir = Path.home() / '.config' / 'replayer'
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.config_dir / 'session_state.json'

        # Thread safety - RLock allows re-entrant locking from same thread
        self._lock = threading.RLock()

        # State fields (protected by _lock)
        self._balance_sol: Decimal = default_balance
        self._last_updated: str = ""
        self._total_pnl: Decimal = Decimal('0.0')
        self._games_played: int = 0
        self._manual_override: bool = False  # Track if balance manually set

        # Load existing state
        self.load()

    def load(self) -> bool:
        """
        Load session state from JSON file.

        Returns:
            True if loaded successfully, False if file doesn't exist (uses defaults)
        """
        with self._lock:
            if not self.state_file.exists():
                logger.info(f"No session state file found. Using defaults (balance={self.default_balance} SOL)")
                self._balance_sol = self.default_balance
                self._last_updated = datetime.now().isoformat()
                self._save_locked()  # Create initial file
                return False

            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)

                # Parse fields (convert strings to Decimal)
                self._balance_sol = Decimal(str(data.get('balance_sol', self.default_balance)))
                self._last_updated = data.get('last_updated', datetime.now().isoformat())
                self._total_pnl = Decimal(str(data.get('total_pnl', '0.0')))
                self._games_played = int(data.get('games_played', 0))
                self._manual_override = bool(data.get('manual_override', False))

                logger.info(f"Loaded session state: balance={self._balance_sol} SOL, "
                           f"total_pnl={self._total_pnl}, games={self._games_played}")
                return True

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load session state: {e}. Using defaults.")
                self._balance_sol = self.default_balance
                self._last_updated = datetime.now().isoformat()
                return False

    def save(self) -> bool:
        """
        Save session state to JSON file (thread-safe).

        Returns:
            True if saved successfully, False on error
        """
        with self._lock:
            return self._save_locked()

    def _save_locked(self) -> bool:
        """
        Internal save method - must be called with lock held.

        Returns:
            True if saved successfully, False on error
        """
        try:
            data = {
                'balance_sol': str(self._balance_sol),  # Convert Decimal to string
                'last_updated': datetime.now().isoformat(),
                'total_pnl': str(self._total_pnl),
                'games_played': self._games_played,
                'manual_override': self._manual_override
            }

            # Write atomically (write to temp file, then rename)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.state_file)

            logger.debug(f"Saved session state: balance={self._balance_sol} SOL")
            return True

        except (OSError, IOError) as e:
            logger.error(f"Failed to save session state: {e}")
            return False

    def update_balance(self, pnl_delta: Decimal) -> Decimal:
        """
        Update balance based on P&L delta (thread-safe).

        Args:
            pnl_delta: Profit/loss amount (positive for profit, negative for loss)

        Returns:
            New balance
        """
        with self._lock:
            self._balance_sol += pnl_delta
            self._total_pnl += pnl_delta
            self._last_updated = datetime.now().isoformat()
            self._manual_override = False  # Reset manual override flag (now tracking P&L)

            # Auto-save (already holds lock, use internal method)
            self._save_locked()

            logger.info(f"Balance updated: {pnl_delta:+.4f} SOL → {self._balance_sol:.4f} SOL "
                       f"(total P&L: {self._total_pnl:+.4f})")

            return self._balance_sol

    def set_balance_manual(self, new_balance: Decimal) -> Decimal:
        """
        Manually set balance (user override, thread-safe).

        Args:
            new_balance: New balance value

        Returns:
            New balance
        """
        with self._lock:
            old_balance = self._balance_sol
            self._balance_sol = new_balance
            self._last_updated = datetime.now().isoformat()
            self._manual_override = True

            # Auto-save (already holds lock, use internal method)
            self._save_locked()

            logger.warning(f"Balance manually set: {old_balance:.4f} → {new_balance:.4f} SOL")

            return self._balance_sol

    def reset_to_default(self) -> Decimal:
        """
        Reset session to default state (thread-safe).

        Returns:
            New balance (default_balance)
        """
        with self._lock:
            self._balance_sol = self.default_balance
            self._total_pnl = Decimal('0.0')
            self._games_played = 0
            self._manual_override = False
            self._last_updated = datetime.now().isoformat()

            # Auto-save (already holds lock, use internal method)
            self._save_locked()

            logger.info(f"Session reset to default: balance={self.default_balance} SOL")

            return self._balance_sol

    def increment_games_played(self) -> int:
        """
        Increment games played counter (thread-safe).

        Returns:
            New games played count
        """
        with self._lock:
            self._games_played += 1
            self._save_locked()
            return self._games_played

    def get_balance(self) -> Decimal:
        """Get current balance (thread-safe)."""
        with self._lock:
            return self._balance_sol

    def get_total_pnl(self) -> Decimal:
        """Get total P&L across all sessions (thread-safe)."""
        with self._lock:
            return self._total_pnl

    def is_manual_override(self) -> bool:
        """Check if balance was manually set (thread-safe)."""
        with self._lock:
            return self._manual_override

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get immutable snapshot of session state (thread-safe).

        Returns:
            Dict with all session state fields
        """
        with self._lock:
            return {
                'balance_sol': self._balance_sol,
                'last_updated': self._last_updated,
                'total_pnl': self._total_pnl,
                'games_played': self._games_played,
                'manual_override': self._manual_override,
                'default_balance': self.default_balance
            }

    # Property accessors for backward compatibility
    @property
    def balance_sol(self) -> Decimal:
        """Thread-safe balance accessor."""
        with self._lock:
            return self._balance_sol

    @balance_sol.setter
    def balance_sol(self, value: Decimal):
        """Thread-safe balance setter."""
        with self._lock:
            self._balance_sol = value

    @property
    def total_pnl(self) -> Decimal:
        """Thread-safe total_pnl accessor."""
        with self._lock:
            return self._total_pnl

    @property
    def games_played(self) -> int:
        """Thread-safe games_played accessor."""
        with self._lock:
            return self._games_played

    @property
    def manual_override(self) -> bool:
        """Thread-safe manual_override accessor."""
        with self._lock:
            return self._manual_override

    @property
    def last_updated(self) -> str:
        """Thread-safe last_updated accessor."""
        with self._lock:
            return self._last_updated
