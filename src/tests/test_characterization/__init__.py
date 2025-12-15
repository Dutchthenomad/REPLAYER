"""
Characterization Tests - Technical Debt Audit Phase 1

These tests document CURRENT behavior (even if buggy).
They serve as a safety net during refactoring.

DO NOT "fix" failing tests by changing expected values.
If a test fails after a change, that change broke existing behavior.

Categories:
- test_event_flow.py: WebSocket → EventBus → Controllers → UI
- test_ui_state.py: State management, widget sync
- test_recording_system.py: Recording state conflicts (Issue #18)
"""
