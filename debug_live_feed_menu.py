#!/usr/bin/env python3
"""
Debug script to test live feed menu integration
Identifies the race condition bug
"""

print("=" * 70)
print("LIVE FEED MENU DEBUG ANALYSIS")
print("=" * 70)

# Trace through the execution flow
print("\n📋 EXECUTION FLOW TRACE:")
print("-" * 70)

print("\n1. User clicks 'Connect to Live Feed' checkbox (OFF → ON)")
print("   Checkbox state: True")
print("   self.live_feed_connected: False")

print("\n2. Triggers: _toggle_live_feed_from_menu()")
print("   Line 1168: self.toggle_live_feed()")

print("\n3. toggle_live_feed() executes:")
print("   Line 611: if self.live_feed_connected:")
print("   self.live_feed_connected is False, so ELSE branch")
print("   Line 614: self.enable_live_feed()")

print("\n4. enable_live_feed() executes:")
print("   Line 523: self.live_feed = WebSocketFeed(log_level='WARN')")
print("   Lines 526-579: Setup event handlers (decorators)")
print("   Line 582: self.live_feed.connect()  <-- ASYNC CONNECTION STARTS")
print("   ⚠️  Connection is ASYNC - takes 100-2000ms to complete")

print("\n5. WebSocketFeed.connect() (websocket_feed.py line 421):")
print("   Calls self.sio.connect() with wait_timeout=20")
print("   ⚠️  This is SYNCHRONOUS but can take 100-2000ms")
print("   ⚠️  During this time, self.live_feed_connected is STILL False")

print("\n6. IF connection succeeds:")
print("   Socket.IO 'connect' event fires")
print("   Line 244 (websocket_feed.py): self.is_connected = True")
print("   Line 247: self._emit_event('connected', ...)")
print("   Line 549 (main_window.py): self.live_feed_connected = True")
print("   ✅ Connection successful")

print("\n7. Back to _toggle_live_feed_from_menu():")
print("   Line 1170: self.live_feed_var.set(self.live_feed_connected)")
print("   ⚠️  BUG: This line executes IMMEDIATELY after toggle_live_feed()")
print("   ⚠️  At this point, connection might STILL be in progress")
print("   ⚠️  self.live_feed_connected is probably STILL False")
print("   ⚠️  Checkbox gets UNCHECKED even though connection succeeded!")

print("\n" + "=" * 70)
print("🐛 IDENTIFIED BUGS:")
print("=" * 70)

bugs = [
    {
        "id": 1,
        "severity": "CRITICAL",
        "title": "Race condition in menu checkbox sync",
        "location": "main_window.py:1170",
        "description": "Checkbox state is synced BEFORE connection completes",
        "impact": "Checkbox unchecks itself even when connection succeeds",
        "fix": "Sync checkbox in the 'connected' event handler, not in menu callback"
    },
    {
        "id": 2,
        "severity": "MEDIUM",
        "title": "No visual feedback during connection",
        "description": "User doesn't know connection is in progress",
        "impact": "Confusing UX - appears broken",
        "fix": "Show toast 'Connecting...' before connection attempt"
    },
    {
        "id": 3,
        "severity": "LOW",
        "title": "Error case checkbox state not synced",
        "location": "main_window.py:587-589",
        "description": "On connection error, checkbox state not explicitly synced",
        "impact": "Checkbox might stay checked after failure",
        "fix": "Add self.live_feed_var.set(False) in exception handler"
    }
]

for bug in bugs:
    print(f"\n🐛 BUG #{bug['id']}: [{bug['severity']}] {bug['title']}")
    print(f"   Location: {bug.get('location', 'N/A')}")
    print(f"   Issue: {bug['description']}")
    print(f"   Impact: {bug['impact']}")
    print(f"   Fix: {bug['fix']}")

print("\n" + "=" * 70)
print("✅ RECOMMENDED FIXES:")
print("=" * 70)

print("""
FIX #1: Remove checkbox sync from _toggle_live_feed_from_menu()
--------
BEFORE (line 1166-1170):
    def _toggle_live_feed_from_menu(self):
        self.toggle_live_feed()
        # Sync menu checkbutton state with actual connection state
        self.live_feed_var.set(self.live_feed_connected)  # ❌ TOO EARLY!

AFTER:
    def _toggle_live_feed_from_menu(self):
        self.toggle_live_feed()
        # Checkbox will be synced in event handlers (connected/disconnected)
        # Don't sync here - connection is async!


FIX #2: Sync checkbox in event handlers
--------
Update handle_connected() (line 548-556):
    def handle_connected():
        self.live_feed_connected = True
        self.live_feed_var.set(True)  # ✅ ADD THIS
        self.log(f"✅ Live feed connected...")
        ...

Update handle_disconnected() (line 562-568):
    def handle_disconnected():
        self.live_feed_connected = False
        self.live_feed_var.set(False)  # ✅ ADD THIS
        self.log("❌ Live feed disconnected")
        ...

Update exception handler (line 584-589):
    except Exception as e:
        logger.error(f"Failed to enable live feed: {e}", exc_info=True)
        self.log(f"Failed to connect to live feed: {e}")
        self.toast.show(f"Live feed error: {e}", "error")
        self.live_feed = None
        self.live_feed_connected = False
        self.live_feed_var.set(False)  # ✅ ADD THIS


FIX #3: Add connection progress feedback
--------
In enable_live_feed(), BEFORE line 582:
    # Show connecting toast
    if self.toast:
        self.toast.show("Connecting to live feed...", "info")

    # Connect to feed
    self.live_feed.connect()
""")

print("\n" + "=" * 70)
print("📊 SUMMARY:")
print("=" * 70)
print("""
The bug is a classic RACE CONDITION:
• Menu callback syncs checkbox state BEFORE async connection completes
• self.live_feed_connected is still False when checkbox is synced
• Checkbox unchecks itself even though connection eventually succeeds

Solution:
• Don't sync checkbox in menu callback
• Sync checkbox in event handlers (connected/disconnected/error)
• Add visual feedback during connection
""")

print("=" * 70)
print("✅ Ready to apply fixes")
print("=" * 70)
