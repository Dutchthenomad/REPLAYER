"""
Helpers for launching Chromium with a persistent profile and extensions.

These utilities are built in the Codex Side Quests workspace so they can be
ported into the core project once validated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from pathlib import Path
from typing import Iterable, List, Optional

# Chromium arguments for light-weight ad blocking (mirrors existing controller)
AD_BLOCK_ARGS: List[str] = [
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-extensions",
    "--no-first-run",
]


@dataclass
class PersistentProfileConfig:
    """
    Configuration for launching Chromium with a persistent profile.
    """

    user_data_dir: Path
    extension_dirs: List[Path] = field(default_factory=list)
    headless: bool = False
    block_ads: bool = False
    extra_args: List[str] = field(default_factory=list)
    channel: Optional[str] = None
    executable_path: Optional[Path] = None

    def validate(self) -> None:
        """
        Ensure directories exist and configuration is sane.
        """
        # Normalise user data directory and ensure it exists
        self.user_data_dir = Path(self.user_data_dir).expanduser().resolve()
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        # Normalise extension directories and ensure they exist
        normalised_extensions: List[Path] = []
        for ext_dir in self.extension_dirs:
            path = Path(ext_dir).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(
                    f"Extension directory not found: {path}"
                )
            normalised_extensions.append(path)
        self.extension_dirs = normalised_extensions

        # Ensure extra args are strings
        self.extra_args = [str(arg) for arg in self.extra_args]

        if self.executable_path:
            self.executable_path = Path(self.executable_path).expanduser().resolve()
            if not self.executable_path.exists():
                raise FileNotFoundError(
                    f"Executable path not found: {self.executable_path}"
                )


def _merge_args(base: Iterable[str], extra: Iterable[str]) -> List[str]:
    """
    Merge argument lists while preserving order and avoiding duplicates.
    """
    seen = set()
    merged: List[str] = []
    for arg in list(base) + list(extra):
        if arg in seen:
            continue
        merged.append(arg)
        seen.add(arg)
    return merged


def build_launch_options(config: PersistentProfileConfig) -> dict:
    """
    Build kwargs for Playwright's `launch_persistent_context`.
    """
    import os

    # Validation normalises directories
    config.validate()

    args: List[str] = []

    if config.extension_dirs:
        ext_paths = [str(path) for path in config.extension_dirs]
        ext_arg = ",".join(ext_paths)
        args.extend([
            f"--disable-extensions-except={ext_arg}",
            f"--load-extension={ext_arg}",
        ])

    if config.block_ads:
        args = _merge_args(args, AD_BLOCK_ARGS)
        if config.extension_dirs:
            args = [arg for arg in args if arg != "--disable-extensions"]

    if config.extra_args:
        args = _merge_args(args, config.extra_args)

    # CRITICAL: Inherit environment variables for browser launching
    # This fixes the "browser didn't launch" issue by ensuring DISPLAY variable
    # is available for GUI subprocess (proven fix from previous sessions)
    env = os.environ.copy()

    # AUDIT FIX: Explicitly set PLAYWRIGHT_BROWSERS_PATH to avoid /root/.cache/ issue
    # Use per-user cache path unless overridden via environment variable
    env['PLAYWRIGHT_BROWSERS_PATH'] = str(
        Path(
            os.getenv(
                "PLAYWRIGHT_BROWSERS_PATH",
                Path.home() / ".cache" / "ms-playwright"
            )
        ).expanduser()
    )

    options = {
        "user_data_dir": str(config.user_data_dir),
        "headless": config.headless,
        "args": args,
        "env": env,  # Pass environment variables to browser process
    }
    if config.channel:
        options["channel"] = config.channel
    if config.executable_path:
        options["executable_path"] = str(config.executable_path)
    return options


@dataclass
class PersistentBrowserSession:
    """
    Wrapper for persistent Chromium sessions to simplify cleanup handling.
    """

    context: object
    browser: Optional[object]
    page: Optional[object] = None

    async def close(self) -> None:
        """
        Close context and browser if available.
        """
        if self.context:
            await _maybe_await(self.context.close)
        if self.browser:
            await _maybe_await(self.browser.close)


async def _maybe_await(close_callable):
    """
    Execute a callable that may return an awaitable.
    """
    result = close_callable()
    if inspect.isawaitable(result):
        await result
