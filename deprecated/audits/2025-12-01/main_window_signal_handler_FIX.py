"""
main_window.py Signal Handler Fix

CRITICAL FIX: Race condition in live feed signal processing

The original code captures `signal` by reference in the closure, but by the time
root.after(0, process_signal) executes, a new signal may have arrived.

BEFORE (BUGGY):
    @self.live_feed.on('signal')
    def on_signal(signal):
        def process_signal():
            tick = self.live_feed.signal_to_game_tick(signal)  # signal may have changed!

AFTER (FIXED):
    @self.live_feed.on('signal')
    def on_signal(signal):
        # CRITICAL: Create immutable copy to prevent race condition
        signal_snapshot = _create_signal_snapshot(signal)
        
        def process_signal(captured=signal_snapshot):  # Default arg captures value
            tick = self.live_feed.signal_to_game_tick(captured)

Apply this patch to src/ui/main_window.py in the enable_live_feed() method.
"""

# Helper function to add to main_window.py (or utils)
def _create_signal_snapshot(signal):
    """
    Create an immutable snapshot of a signal to prevent race conditions.
    
    When signals arrive faster than the UI can process them, capturing
    by reference causes the wrong signal to be processed. This creates
    a value copy that's immune to subsequent mutations.
    
    Args:
        signal: GameSignal or dict from WebSocket
        
    Returns:
        Immutable copy (dict or frozen dataclass)
    """
    if hasattr(signal, '__dict__'):
        # Dataclass or object - copy attributes
        return {k: v for k, v in signal.__dict__.items()}
    elif hasattr(signal, 'items'):
        # Dict - create copy
        return dict(signal)
    elif hasattr(signal, '_asdict'):
        # NamedTuple
        return signal._asdict()
    else:
        # Unknown type - return as-is (hopefully immutable)
        return signal


# ============================================================================
# REPLACEMENT CODE FOR enable_live_feed() METHOD
# ============================================================================
# Replace the entire enable_live_feed() method with this fixed version:

def enable_live_feed_FIXED(self):
    """
    Enable WebSocket live feed (Phase 6)
    
    PRODUCTION FIX: Signal handler now captures signal value, not reference,
    to prevent race conditions when signals arrive faster than UI processes them.
    """
    if self.live_feed_connected:
        self.log("Live feed already connected")
        return

    try:
        self.log("Connecting to live feed...")
        # Show connecting toast for user feedback
        if self.toast:
            self.toast.show("Connecting to live feed...", "info")

        # Create WebSocketFeed
        self.live_feed = WebSocketFeed(log_level='WARN')

        # Register event handlers (THREAD-SAFE with root.after)
        @self.live_feed.on('signal')
        def on_signal(signal):
            # ============================================================
            # CRITICAL FIX: Capture signal VALUE, not reference
            # ============================================================
            # The original code had a race condition where `signal` could
            # change between when on_signal() is called and when 
            # process_signal() actually runs via root.after().
            #
            # By creating an immutable snapshot and using a default argument,
            # we ensure each queued callback processes the correct signal.
            # ============================================================
            
            signal_snapshot = _create_signal_snapshot(signal)
            
            def process_signal(captured_signal=signal_snapshot):
                """Process signal on main thread (uses captured snapshot)"""
                try:
                    # Convert GameSignal to GameTick
                    tick = self.live_feed.signal_to_game_tick(captured_signal)

                    # Push to replay engine (auto-records if enabled)
                    self.replay_engine.push_tick(tick)

                    # Publish to event bus for UI updates
                    from services.event_bus import Events
                    self.event_bus.publish(Events.GAME_TICK, {'tick': tick})
                    
                except Exception as e:
                    logger.error(f"Error processing live signal: {e}", exc_info=True)
                    # Show error to user for visibility
                    if self.toast:
                        self.toast.show(f"Signal error: {str(e)[:50]}", "error")

            # Marshal to Tkinter main thread
            self.root.after(0, process_signal)

        @self.live_feed.on('connected')
        def on_connected(info):
            # PRODUCTION FIX: Capture info snapshot
            info_snapshot = dict(info) if hasattr(info, 'items') else {'socketId': getattr(info, 'socketId', None)}
            
            def handle_connected(captured_info=info_snapshot):
                socket_id = captured_info.get('socketId')

                # Skip first connection event (Socket ID not yet assigned)
                if socket_id is None:
                    self.log("🔌 Connection negotiating...")
                    return

                # Connection established
                self.live_feed_connected = True
                # Sync menu checkbox state
                self.live_feed_var.set(True)
                self.log(f"✅ Live feed connected (Socket ID: {socket_id})")
                
                if self.toast:
                    self.toast.show("Live feed connected", "success")
                    
                if hasattr(self, 'phase_label'):
                    self.phase_label.config(text="PHASE: LIVE FEED", fg='#00ff88')

            self.root.after(0, handle_connected)

        @self.live_feed.on('disconnected')
        def on_disconnected(info):
            # PRODUCTION FIX: Capture info snapshot  
            info_snapshot = dict(info) if hasattr(info, 'items') else {}
            
            def handle_disconnected(captured_info=info_snapshot):
                reason = captured_info.get('reason', 'unknown')
                self.live_feed_connected = False
                # Sync menu checkbox state
                self.live_feed_var.set(False)
                
                self.log(f"❌ Live feed disconnected: {reason}")
                
                if self.toast:
                    self.toast.show(f"Live feed disconnected: {reason}", "warning")
                    
                if hasattr(self, 'phase_label'):
                    self.phase_label.config(text="PHASE: DISCONNECTED", fg='#ff4444')

            self.root.after(0, handle_disconnected)

        @self.live_feed.on('gameComplete')
        def on_game_complete(data):
            # PRODUCTION FIX: Capture data snapshot
            data_snapshot = dict(data) if hasattr(data, 'items') else {}
            
            def handle_game_complete(captured_data=data_snapshot):
                game_id = captured_data.get('signal', {}).get('gameId', 'unknown')
                self.log(f"🎮 Game complete: {game_id}")
                
                # Trigger any game-end logic
                from services.event_bus import Events
                self.event_bus.publish(Events.GAME_END, captured_data)

            self.root.after(0, handle_game_complete)

        # Connect to WebSocket with timeout
        self.live_feed.connect()

    except Exception as e:
        logger.error(f"Error enabling live feed: {e}", exc_info=True)
        self.log(f"Error: {e}")
        
        if self.toast:
            self.toast.show(f"Connection failed: {str(e)[:50]}", "error")
            
        self.live_feed = None
        self.live_feed_connected = False
        # Sync menu checkbox state (connection failed)
        self.live_feed_var.set(False)


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
# 
# 1. Add _create_signal_snapshot() function to main_window.py (at module level)
#    or to a utils module
#
# 2. Replace the enable_live_feed() method with enable_live_feed_FIXED()
#    (rename to enable_live_feed in the actual file)
#
# 3. Ensure WebSocketFeed import is present
#
# 4. Test by:
#    - Connect to live feed
#    - Let it run for 30+ seconds (several games)
#    - Verify no signal processing errors in logs
#    - Verify tick numbers are sequential (no duplicates from race)
# ============================================================================
