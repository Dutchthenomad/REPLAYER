"""
Tests for TkDispatcher
"""

from services.ui_dispatcher import TkDispatcher


class DummyRoot:
    """Minimal stub mimicking Tk's after scheduling."""

    def __init__(self):
        self.callbacks = []

    def after(self, _delay, callback):
        self.callbacks.append(callback)


def test_dispatcher_runs_tasks_on_main_thread_stub():
    root = DummyRoot()
    dispatcher = TkDispatcher(root, poll_interval=0)
    executed = []

    dispatcher.submit(lambda value: executed.append(value), 42)

    # Trigger scheduled drains manually
    while root.callbacks:
        callback = root.callbacks.pop(0)
        callback()
        if executed:
            dispatcher.stop()
            break

    assert executed == [42]
