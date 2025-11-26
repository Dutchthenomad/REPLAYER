# AUDIT FINDINGS - ORGANIZED BY FILE

## Summary by File

| File | Total | Critical | High | Medium | Low |
|------|-------|----------|------|--------|-----|
| `ui_controller.py` | 4 | 2 | 1 | 1 | 0 |
| `browser_executor.py` | 4 | 0 | 3 | 1 | 0 |
| `async_executor.py` | 3 | 1 | 0 | 2 | 0 |
| `main_window.py` | 1 | 1 | 0 | 0 | 0 |
| `controller.py` | 2 | 0 | 2 | 0 | 0 |
| `foundational.py` | 1 | 0 | 1 | 0 | 0 |
| `strategies/*.py` | 2 | 0 | 2 | 0 | 0 |

---

## `/home/nomad/Desktop/REPLAYER/src/bot/ui_controller.py`

### Issue #1: UI Widget Reference Lifetime (CRITICAL)
**Lines**: 62-69, 170-196  
**Severity**: CRITICAL - Will crash bot  
**Problem**:
- Widget references stored at initialization are never validated for existence
- Widgets can be destroyed by UI refresh, widget replacement, or Tk cleanup
- Attempting to call `.invoke()`, `.cget()`, `.config()` on stale widget raises `TclError`

**Code Example**:
```python
# Line 62-69: Store widget references
self.clear_button = main_window.clear_button
self.increment_001_button = main_window.increment_001_button

# Line 170-196: Later usage without validation
def _click_button_with_visual_feedback(btn=button):
    original_relief = btn.cget('relief')  # ← CRASH if btn destroyed
    btn.config(relief=tk.SUNKEN)  # ← CRASH if btn destroyed
    btn.invoke()  # ← CRASH if btn destroyed
```

**Fix**:
```python
def _click_button_with_visual_feedback(btn=button):
    if not btn.winfo_exists():
        logger.error(f"Button {btn} has been destroyed")
        return False
    try:
        original_relief = btn.cget('relief')
        # ... rest of code ...
    except tk.TclError as e:
        logger.error(f"Widget operation failed: {e}")
        return False
```

---

### Issue #2: Button Click Timing Blocks Worker (CRITICAL)
**Lines**: 75-92, 134-210, 198-203  
**Severity**: CRITICAL - Bot systematically late  
**Problem**:
- Worker thread sleeps 100ms between button clicks (configurable in inter_click_pause_ms)
- Example: 5 button clicks = 500ms delay in worker thread
- Game ticks every 250ms, so bot is 2+ ticks behind while clicking
- By time BUY button fires, game has progressed 2-5 ticks
- Entry price changed, PnL calculations based on stale price

**Code Flow**:
```python
# Line 168-210
for i in range(times):  # e.g., 5 clicks
    def _click_button_with_visual_feedback():
        # ... press button ...
        btn.invoke()  # Scheduled to main thread
    
    self._schedule_ui_action(_click_button_with_visual_feedback)
    time.sleep(self.inter_click_pause_ms / 1000.0)  # ← BLOCKS WORKER 100ms
    # Next iteration doesn't start until sleep completes
```

**Impact**:
- Bot decides: BUY at tick 45
- Clicks buttons: ticks 45-50 (5 clicks × 100ms each)
- BUY button fires: tick 50+
- Price has moved from entry_price to new price
- All PnL calculations wrong

**Fix**:
```python
# Option 1: Reduce inter_click_pause_ms to 20ms (realistic)
# Option 2: Schedule all clicks upfront, sleep in main thread
# Option 3: Use async/await for proper non-blocking waits

# Recommended: Move sleep before scheduling
for i in range(times):
    if i > 0:  # Don't sleep before first click
        time.sleep(self.inter_click_pause_ms / 1000.0)
    
    # Then schedule the click (happens immediately)
    self._schedule_ui_action(_click_button_with_visual_feedback)
```

---

### Issue #3: Floating Point in Greedy Sequence (MEDIUM)
**Lines**: 328-355  
**Severity**: MEDIUM - Precision loss  
**Problem**:
- `_greedy_sequence()` uses float arithmetic instead of Decimal
- Float precision errors accumulate across multiple clicks
- Example: Trying to set 0.015 SOL might result in 0.0149999... or 0.0150000...
- Multiple trade button clicks can cause systematic bias

**Code**:
```python
def _greedy_sequence(self, target: float) -> list:  # ← float, not Decimal!
    remaining = target  # 0.015 as float
    sequence = []
    
    for increment_value, button_type in increments:
        count = int(remaining / increment_value)
        if count > 0:
            sequence.append((button_type, count))
            remaining -= count * increment_value  # ← Float arithmetic error
            remaining = round(remaining, 3)  # Imperfect rounding
```

**Example Accumulation**:
```
remaining = 0.015 (float) = 0.014999999999
remaining -= 0.01  = 0.004999999999 (not 0.005!)
remaining = round(remaining, 3) = 0.005 ✓
remaining -= 0.001 * 3 = 0.001999999999
# Bot places 0.002 instead of 0.003 SOL
```

**Fix**:
```python
def _greedy_sequence(self, target: Decimal) -> list:  # Accept Decimal
    remaining = target  # Exact decimal arithmetic
    sequence = []
    
    increments = [
        (Decimal('1.0'), '+1'),
        (Decimal('0.1'), '+0.1'),
        (Decimal('0.01'), '+0.01'),
        (Decimal('0.001'), '+0.001'),
    ]
    
    for increment_value, button_type in increments:
        count = int(remaining / increment_value)
        if count > 0:
            sequence.append((button_type, count))
            remaining -= count * increment_value  # ← Exact arithmetic
```

---

### Issue #4: No Feedback Loop on Amount Setting (MEDIUM)
**Lines**: 226-280, 547-596  
**Severity**: MEDIUM - Silent failure  
**Problem**:
- `build_amount_incrementally()` clicks buttons and returns True/False
- But doesn't verify that the actual entry field matches target amount
- If a button click doesn't register, entry field is wrong but function returns True
- Bot thinks it set 0.005 SOL, actually set 0.001 SOL

**Code**:
```python
# Line 547-564
def execute_buy_with_amount(self, amount: Decimal) -> bool:
    if not self.build_amount_incrementally(amount):  # ← Returns True if clicks succeeded
        return False
    
    return self.click_buy()  # ← No check that amount is actually set!
    # Bot might have 0.001 SOL in entry field instead of 0.005
```

**Fix**:
```python
def execute_buy_with_amount(self, amount: Decimal) -> bool:
    if not self.build_amount_incrementally(amount):
        return False
    
    # VERIFY the amount was actually set
    actual_amount = self.read_bet_amount()  # NEW METHOD
    if actual_amount != amount:
        logger.warning(f"Amount mismatch: expected {amount}, got {actual_amount}")
        # Could retry build_amount_incrementally() if you want
    
    return self.click_buy()
```

---

## `/home/nomad/Desktop/REPLAYER/src/bot/browser_executor.py`

### Issue #5: Missing Page Null Checks (HIGH)
**Lines**: 661, 698, 765, 789, 915, 964  
**Severity**: HIGH - AttributeError crash  
**Problem**:
- Methods retrieve `page = self.browser_manager.page`
- No null validation before using page object
- Page object can become None if browser disconnected
- Causes `AttributeError: 'NoneType' object has no attribute 'wait_for_selector'`

**Problem Areas**:
```python
# Line 661-678: _set_bet_amount_in_browser
page = self.browser_manager.page  # ← Could be None

for selector in self.BET_AMOUNT_INPUT_SELECTORS:
    try:
        input_field = await page.wait_for_selector(...)  # ← CRASH if page is None!
        # Exception is inside try, but won't catch AttributeError from None
    except Exception:
        continue
```

**Similar Issues at**:
- Line 698: `_set_sell_percentage_in_browser()`
- Line 765: `_click_increment_button_in_browser()`
- Line 789: `_click_increment_button_in_browser()` (recheck)
- Line 915: `read_balance_from_browser()`
- Line 964: `read_position_from_browser()`

**Fix** (use pattern from `click_buy()`):
```python
async def _set_bet_amount_in_browser(self, amount: Decimal) -> bool:
    try:
        # EXPLICIT NULL CHECK AT START
        if not self.browser_manager or not self.browser_manager.page:
            logger.error("Browser not initialized for bet amount setting")
            return False
        
        page = self.browser_manager.page
        
        for selector in self.BET_AMOUNT_INPUT_SELECTORS:
            try:
                input_field = await page.wait_for_selector(selector, timeout=...)
                # ... rest of code ...
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return False  # If we get here, couldn't find input
    
    except Exception as e:
        logger.error(f"Error setting bet amount: {e}")
        return False
```

---

### Issue #6: Async Task Cleanup Not Guaranteed (HIGH)
**Lines**: 302-352, 364-376  
**Severity**: HIGH - Resource leak  
**Problem**:
- `start_browser()` wraps operations in `asyncio.wait_for(..., timeout=...)`
- If timeout triggers, coroutine is cancelled
- But partial initialization (Chromium process started, but page not loaded) isn't cleaned up
- Next start attempt fails due to port already in use
- Repeated failures cause cascading crashes

**Code**:
```python
# Line 302-311
try:
    start_result = await asyncio.wait_for(
        self.browser_manager.start_browser(),
        timeout=self.browser_start_timeout  # 30 seconds
    )
except asyncio.TimeoutError:
    logger.error(f"Browser start timeout after {self.browser_start_timeout}s")
    return False
    # ← What about Chromium process started but page not loaded?
    # Next start attempt: "Port 9222 already in use"
```

**Fix**:
```python
async def start_browser(self) -> bool:
    try:
        logger.info("Starting browser...")
        
        # Create browser manager
        self.browser_manager = RugsBrowserManager(profile_name=self.profile_name)
        
        # ALWAYS cleanup if any step fails
        try:
            start_result = await asyncio.wait_for(
                self.browser_manager.start_browser(),
                timeout=self.browser_start_timeout
            )
            if not start_result:
                logger.error("Failed to start browser")
                await self.stop_browser()  # Cleanup on failure
                return False
        except asyncio.TimeoutError:
            logger.error(f"Browser start timeout after {self.browser_start_timeout}s")
            await self.stop_browser()  # CLEANUP on timeout
            return False
        finally:
            # Even if exception, ensure cleanup attempt
            pass
        
        # ... rest of code ...
        
    except Exception as e:
        logger.error(f"Error starting browser: {e}", exc_info=True)
        await self.stop_browser()  # CLEANUP on any exception
        return False
```

---

### Issue #7: Timeout Configuration Not Validated (HIGH)
**Lines**: 271-280  
**Severity**: HIGH - Bot systematically late  
**Problem**:
- Fixed timeout values with no relationship to game tick interval
- Game tick = 250ms (from CLAUDE.md)
- `click_timeout = 10.0` seconds = 40 game ticks!
- Bot could be 40+ ticks behind before timeout triggers

**Code**:
```python
# Line 271-280
self.max_retries = 3
self.retry_delay = 1.0  # seconds
self.action_timeout = 5.0  # seconds (20 ticks!)
self.validation_delay = 0.5  # seconds
self.browser_start_timeout = 30.0  # seconds (120 ticks!)
self.browser_stop_timeout = 10.0  # seconds (40 ticks!)
self.click_timeout = 10.0  # seconds (40 ticks!)
```

**Impact Example**:
```
tick 30: Bot decides to BUY
tick 31: Strategy sent to executor
tick 32: Executor calls _build_amount_incrementally_in_browser()
tick 32-37: Trying to find first button (5 tick search)
tick 37-42: Trying to find BET button (5 tick search)
tick 42: Finally clicks BUY button
tick 45+: BUY executes in browser
Entry price has moved significantly
```

**Fix**:
```python
def __init__(self, profile_name: str = "rugs_fun_phantom", game_tick_ms: int = 250):
    # Make timeouts configurable based on game tick
    max_ticks_to_wait = 3  # Max 3 ticks = 750ms for click_timeout
    self.click_timeout = max(3.0, min(10.0, (game_tick_ms * max_ticks_to_wait) / 1000))
    
    # Log warning if timeouts seem too long
    if self.click_timeout > 5.0:
        logger.warning(f"click_timeout is {self.click_timeout}s - bot will lag game")
```

---

### Issue #8: Selector Fallback Strategy (MEDIUM)
**Lines**: 146-222  
**Severity**: MEDIUM - Fragility  
**Problem**:
- Fallback selectors include brittle CSS classes
- CSS classes change on website update, breaking bot
- Text-based selectors are more resilient
- Inconsistent strategy across buttons

**Current Strategy**:
```python
# Line 182-186
MAX_BUTTON_SELECTORS = [
    'button:has-text("MAX")',  # Text - Good ✓
    'button._controlBtn_73g5s_23._uppercase_73g5s_230',  # CSS - Brittle ✗
    'xpath=//button[contains(text(), "MAX")]',  # XPath - Slow
]
```

**Fix**:
```python
# Remove CSS class selectors entirely
MAX_BUTTON_SELECTORS = [
    'button:has-text("MAX")',  # Text - Good ✓
    'xpath=//button[contains(text(), "MAX")]',  # XPath - Fallback
]

# Apply consistently across ALL buttons
# Remove all CSS class selectors
```

---

## `/home/nomad/Desktop/REPLAYER/src/bot/async_executor.py`

### Issue #9: Stop Method Race Condition (CRITICAL)
**Lines**: 85-110  
**Severity**: CRITICAL - Orphaned threads  
**Problem**:
- `stop()` sets stop_event and clears queue without synchronization
- Worker thread might be:
  1. Between getting tick and processing it
  2. Putting result back in queue
  3. In the middle of bot.controller.execute_step()
- No guarantee worker actually stops
- Timeout might expire while thread still running

**Code**:
```python
def stop(self):  # Line 85
    self.enabled = False
    self.stop_event.set()
    
    # Race: Worker might put item in queue here
    while not self.execution_queue.empty():  # Line 91 - Race condition!
        try:
            self.execution_queue.get_nowait()
        except queue.Empty:
            break
    
    # Send stop signal
    try:
        self.execution_queue.put(None, timeout=0.1)
    except queue.Full:
        pass
    
    # Wait with timeout - doesn't guarantee thread stopped
    if self.worker_thread:
        self.worker_thread.join(timeout=2.0)  # Line 105
        if self.worker_thread.is_alive():
            logger.warning("Bot executor thread did not stop cleanly")
            # ← But then what? Thread still running!
```

**Fix**:
```python
def stop(self):
    self.enabled = False
    self.stop_event.set()
    
    # Use Condition for proper synchronization
    with self._stop_condition:
        # Signal worker to check stop_event
        self._stop_condition.notify_all()
    
    # Clear queue (thread won't add more after stop_event set)
    while not self.execution_queue.empty():
        try:
            self.execution_queue.get_nowait()
        except queue.Empty:
            break
    
    # Wait for worker with proper notification
    if self.worker_thread:
        self.worker_thread.join(timeout=5.0)
        if self.worker_thread.is_alive():
            logger.error("Bot executor thread did not stop - may be hung!")
            # TODO: Implement thread killing or escalation
```

---

### Issue #10: No Heartbeat Monitoring (MEDIUM)
**Lines**: 42-215  
**Severity**: MEDIUM - Silent failure  
**Problem**:
- Worker thread has no liveness signal
- If thread hangs in bot.controller.execute_step(), main thread doesn't know
- Bot appears enabled but silently fails
- No timeout on individual bot execution

**Scenario**:
```
Worker thread gets stuck:
  - strategy.decide() hangs reading observation
  - TradeManager.execute_buy() deadlocks
  - OR asyncio.wait() never completes

Main thread:
  - Thinks bot is working
  - Keeps queuing ticks
  - No error detected
  
Result: Bot appears active but never executes anything
```

**Fix**:
```python
def __init__(self, bot_controller):
    # ... existing code ...
    self.last_heartbeat = time.time()
    self.heartbeat_timeout = 5.0  # Warn if > 5 seconds without heartbeat

def _worker_loop(self):
    while not self.stop_event.is_set():
        try:
            tick = self.execution_queue.get(timeout=0.5)
            self.last_heartbeat = time.time()  # Update heartbeat
            
            if tick is None:
                break
            
            # Add timeout to execute_step
            start = time.time()
            try:
                result = self.bot_controller.execute_step()
                elapsed = time.time() - start
                
                if elapsed > 2.0:  # Warn if took > 2 seconds
                    logger.warning(f"Bot execution took {elapsed:.2f}s (may lag game)")
                
            except Exception as e:
                self.failures += 1
                logger.error(f"Bot execution failed: {e}")
        
        except queue.Empty:
            continue

def check_heartbeat(self) -> bool:
    """Check if worker is alive"""
    elapsed_since_heartbeat = time.time() - self.last_heartbeat
    if elapsed_since_heartbeat > self.heartbeat_timeout:
        logger.warning(f"Bot worker heartbeat stale ({elapsed_since_heartbeat:.1f}s)")
        return False
    return True
```

---

### Issue #11: Type Hints Missing (LOW)
**Lines**: 42-215  
**Severity**: LOW - Maintainability  
**Problem**:
- No type hints on methods
- Hard to understand what types are expected/returned

**Fix**:
```python
from typing import Optional, Dict, Any

def __init__(self, bot_controller: 'BotController') -> None:

def start(self) -> None:

def stop(self) -> None:

def queue_execution(self, tick: GameTick) -> bool:

def get_latest_result(self) -> Optional[Dict[str, Any]]:

def get_stats(self) -> Dict[str, Any]:
```

---

## `/home/nomad/Desktop/REPLAYER/src/ui/main_window.py`

### Issue #12: Race Condition in bot_enabled Flag (CRITICAL)
**Lines**: 96, 1058-1101, 1237-1244  
**Severity**: CRITICAL - Bot doesn't stop  
**Problem**:
- `self.bot_enabled` boolean flag accessed from multiple threads without locks
- Main thread toggles flag while worker thread reads it
- No mutual exclusion between starting and stopping bot

**Code Flow**:
```python
# Main thread
def toggle_bot(self):  # Line 1056
    self.bot_enabled = not self.bot_enabled  # ← NO LOCK!
    
    if self.bot_enabled:
        self.bot_executor.start()  # Line 1062
        # ... set UI ...
    else:
        self.bot_executor.stop()  # Line 1079
        # ... set UI ...

# Worker thread (async_executor.py)
def _worker_loop(self):
    while not self.stop_event.is_set():  # ← Checking stop_event, not bot_enabled
        # ...
        if not self.enabled:  # ← Reading from another object
            # ...
```

**Problem Scenarios**:

Scenario 1: Toggle during startup
```
Main: bot_enabled = True
Main: bot_executor.start() → creates worker thread
      [some delay]
Main: bot_enabled = False (user clicks button immediately)
Main: bot_executor.stop()
Worker: Thread starts, reads enabled = False, exits immediately
Result: stop() thinks thread is stopping, but it never fully started
```

Scenario 2: Multiple state changes
```
Main: bot_enabled = True, start() 
Worker: Starting up...
Main: bot_enabled = False, stop()
Main: bot_enabled = True, start() → tries to start again
Worker: Still running from original start()
Result: Two worker threads now exist!
```

**Fix**:
```python
import threading

class MainWindow:
    def __init__(self, ...):
        # ... existing code ...
        self._bot_lock = threading.Lock()
        self._bot_state = 'DISABLED'  # States: DISABLED, STARTING, ENABLED, STOPPING
    
    def toggle_bot(self):
        with self._bot_lock:
            if self._bot_state == 'DISABLED':
                self._bot_state = 'STARTING'
                try:
                    self.bot_executor.start()
                    self._bot_state = 'ENABLED'
                    # ... update UI ...
                except Exception as e:
                    logger.error(f"Failed to start bot: {e}")
                    self._bot_state = 'DISABLED'
            
            elif self._bot_state == 'ENABLED':
                self._bot_state = 'STOPPING'
                try:
                    self.bot_executor.stop()
                    self._bot_state = 'DISABLED'
                    # ... update UI ...
                except Exception as e:
                    logger.error(f"Failed to stop bot: {e}")
                    self._bot_state = 'ENABLED'
```

---

## `/home/nomad/Desktop/REPLAYER/src/bot/controller.py`

### Issue #13: Missing Error Context (HIGH)
**Lines**: 129-131  
**Severity**: HIGH - Hard to debug  
**Problem**:
- Exception logging doesn't distinguish execution mode or which component failed
- Same error message for BACKEND vs UI_LAYER failures
- Hard to trace root cause

**Code**:
```python
try:
    # ... execute action ...
except Exception as e:
    logger.error(f"Bot execution error: {e}", exc_info=True)  # ← Generic message
    return self._error_result(f"Bot error: {e}")
```

**Example Log Output** (useless):
```
Bot execution error: NoneType object has no attribute 'invoke'
Traceback: ... (buried in logs)
```

**Fix**:
```python
def execute_step(self) -> Dict[str, Any]:
    try:
        # ... existing code ...
        
        # Step 4: Execute with mode-specific error handling
        if self.execution_mode == ExecutionMode.BACKEND:
            try:
                result = self._execute_action_backend(action_type, amount)
            except Exception as e:
                logger.error(f"BACKEND execution error: {e}", exc_info=True)
                logger.error(f"  Action: {action_type}, Amount: {amount}")
                logger.error(f"  This likely means TradeManager or GameState is broken")
                return self._error_result(f"BACKEND error: {e}")
        
        else:  # UI_LAYER
            try:
                result = self._execute_action_ui(action_type, amount)
            except Exception as e:
                logger.error(f"UI_LAYER execution error: {e}", exc_info=True)
                logger.error(f"  Action: {action_type}, Amount: {amount}")
                logger.error(f"  This likely means BotUIController or UI widgets are broken")
                return self._error_result(f"UI_LAYER error: {e}")
        
        return result
    
    except Exception as e:
        logger.error(f"Unexpected bot error (execution_mode={self.execution_mode.value}): {e}", exc_info=True)
        return self._error_result(f"Unexpected error: {e}")
```

---

### Issue #14: No Validation of Observation (MEDIUM)
**Lines**: 93-95  
**Severity**: MEDIUM - Strategy crashes  
**Problem**:
- Only checks if observation is None
- Doesn't validate required keys exist
- Strategy assumes all keys are present

**Code**:
```python
def execute_step(self) -> Dict[str, Any]:
    try:
        observation = self.bot.bot_get_observation()
        if not observation:  # ← Only checks for None
            return self._error_result("No game state available")
        
        info = self.bot.bot_get_info()
        
        # Pass to strategy without validation
        action_type, amount, reasoning = self.strategy.decide(observation, info)  # ← May crash
```

**Strategy Code**:
```python
# In conservative.py line 43-46
def decide(self, observation, info):
    state = observation['current_state']  # ← KeyError if missing!
    position = observation['position']
    sidebet = observation['sidebet']
    wallet = observation['wallet']
```

**Fix**:
```python
def execute_step(self) -> Dict[str, Any]:
    try:
        observation = self.bot.bot_get_observation()
        if not observation:
            return self._error_result("No game state available")
        
        # VALIDATE observation structure
        required_keys = ['current_state', 'position', 'sidebet', 'wallet']
        for key in required_keys:
            if key not in observation:
                logger.error(f"Malformed observation: missing '{key}' key")
                logger.error(f"  Observation keys: {list(observation.keys())}")
                return self._error_result(f"Invalid observation: missing {key}")
        
        # VALIDATE sub-keys
        current_state = observation['current_state']
        if not isinstance(current_state, dict) or 'price' not in current_state:
            logger.error(f"Malformed current_state: {current_state}")
            return self._error_result("Invalid current_state")
        
        # Now safe to pass to strategy
        info = self.bot.bot_get_info()
        action_type, amount, reasoning = self.strategy.decide(observation, info)
```

---

## `/home/nomad/Desktop/REPLAYER/src/bot/strategies/foundational.py`

### Issue #15: Entry Tick Not Reset Between Trades (HIGH)
**Lines**: 73, 150, 110, 175  
**Severity**: HIGH - Wrong hold time  
**Problem**:
- `self.entry_tick` initialized to None in `__init__`
- Set when entering position at line 150
- But if position closes and new position opens in same game, old entry_tick not cleared
- Second position uses wrong entry_tick for hold time calculation

**Code**:
```python
def __init__(self):
    # Line 73
    self.entry_tick = None  # Initialized once

def decide(self, observation, info):
    # Line 110
    if position is not None:
        ticks_held = tick - self.entry_tick if self.entry_tick else 0  # ← Uses old entry_tick!
    
    # Line 150 - When entering position
    if position is None and info['can_buy']:
        if self._should_enter(...):
            self.entry_tick = tick  # ← SET ONLY ON ENTRY
            return ("BUY", ...)
```

**Scenario**:
```
Tick 30: Entry price 2.0x, bot buys, entry_tick = 30
Tick 60: Exit at profit, position closed
        entry_tick is still 30 (NOT reset!)

Tick 80: Entry price 3.5x (in sweet spot), bot buys
        entry_tick is STILL 30 (WRONG!)
        ticks_held = 80 - 30 = 50 (should be 0!)
        
Tick 95: Price at 5.0x
        Profit = 43% (should hold more)
        But ticks_held = 65 (> MAX_HOLD_TICKS = 60)
        Bot sells prematurely!
```

**Fix**:
```python
def reset(self):
    """Reset strategy state (called on new game)"""
    super().reset()
    self.entry_tick = None  # ← Reset on new game ✓

def decide(self, observation, info):
    # ... existing code ...
    
    # When exiting position (ANY reason)
    if position is not None and should_exit:
        # ... return SELL ...
        # DON'T explicitly reset entry_tick here (let it be overwritten)
    
    # When entering position
    if position is None and info['can_buy']:
        if self._should_enter(...):
            self.entry_tick = tick  # ← Overwrites old value ✓
            return ("BUY", ...)

def _should_enter(self, price, tick, balance):
    # Line 207-237
    # ... existing checks ...
    return True
```

---

## `/home/nomad/Desktop/REPLAYER/src/bot/strategies/*.py` (All Strategies)

### Issue #16: Missing Decimal Validation (HIGH)
**Files**: conservative.py, aggressive.py, sidebet.py, foundational.py  
**Lines**: Conservative: 48-50, Aggressive: 46-48, Foundational: 100-102  
**Severity**: HIGH - Bot crashes  
**Problem**:
- All strategies convert observation values to Decimal without error handling
- If price is malformed (NaN, Infinity, invalid string), Decimal() raises exception
- No fallback to WAIT action
- Strategy crashes, controller gets None or exception

**Code**:
```python
# In conservative.py line 48-50
def decide(self, observation, info):
    state = observation['current_state']
    price = Decimal(str(state['price']))  # ← What if price is float('nan')?
    # InvalidOperation: [<class 'decimal.ConversionSyntax'>]
    
    tick = state['tick']
    balance = Decimal(str(wallet['balance']))  # ← Same risk
```

**Scenario**:
```
observation['current_state']['price'] = float('inf')
price = Decimal(str(float('inf'))) = Decimal('Infinity')
# This doesn't crash, but calculations with it will:
pnl_pct = ... * price  # NaN result
if pnl_pct > self.TAKE_PROFIT:  # ← Can't compare NaN
    # TypeError or unpredictable behavior
```

**Better Example** (causes immediate crash):
```
observation['current_state']['price'] = float('nan')
price = Decimal(str(float('nan'))) = Decimal('NaN')
if price < self.BUY_THRESHOLD:  # ← TypeError: '<' not supported for NaN
    # CRASH!
```

**Fix**:
```python
def decide(self, observation, info):
    try:
        state = observation['current_state']
        
        # Validate and convert price
        try:
            price = Decimal(str(state['price']))
            # Check for special values
            if not price.is_finite():
                logger.warning(f"Non-finite price: {price}")
                return ("WAIT", None, f"Invalid price data: {price}")
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            logger.error(f"Failed to parse price '{state['price']}': {e}")
            return ("WAIT", None, f"Price conversion error: {e}")
        
        # Similar validation for other Decimal conversions
        try:
            balance = Decimal(str(wallet['balance']))
            if not balance.is_finite() or balance < 0:
                logger.warning(f"Invalid balance: {balance}")
                return ("WAIT", None, "Invalid balance data")
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            logger.error(f"Failed to parse balance: {e}")
            return ("WAIT", None, "Balance conversion error")
        
        # ... rest of existing logic ...
        
    except KeyError as e:
        logger.error(f"Missing observation key: {e}")
        return ("WAIT", None, f"Malformed observation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in strategy: {e}", exc_info=True)
        return ("WAIT", None, f"Strategy error: {e}")
```

---

### Issue #17: No Strategy Decision Logging (LOW)
**Files**: All strategy files  
**Severity**: LOW - Debugging  
**Problem**:
- Strategy decisions logged after execution in bot_controller
- But strategy's internal logic not logged
- Hard to understand why strategy made particular decision

**Fix**:
Add to each strategy file:
```python
import logging

logger = logging.getLogger(__name__)

class ConservativeStrategy(TradingStrategy):
    def decide(self, observation, info):
        # ... validation ...
        
        state = observation['current_state']
        position = observation['position']
        # ...
        
        # Log decision rationale
        logger.debug(f"Conservative strategy: price={price:.2f}x, position={position is not None}, "
                   f"can_buy={info['can_buy']}, balance={balance:.4f}")
        
        # No position
        if position is None and info['can_buy']:
            if price < self.BUY_THRESHOLD and balance >= self.BUY_AMOUNT:
                logger.debug(f"  → Entry decision: price {price:.2f}x < threshold {self.BUY_THRESHOLD}x, "
                           f"balance {balance:.4f} >= min {self.BUY_AMOUNT}")
                return ("BUY", self.BUY_AMOUNT, f"Entry at {price:.2f}x")
        
        # ... rest of logic with similar logging ...
```

---

## Summary of Fixes by Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| P0 | Bot enable/disable race (main_window.py #12) | 2 hours | CRITICAL - Bot doesn't stop |
| P0 | Widget reference lifetime (ui_controller.py #1) | 2 hours | CRITICAL - Bot crashes |
| P0 | Button timing blocks worker (ui_controller.py #2) | 1 hour | CRITICAL - Bot late by ticks |
| P0 | AsyncBotExecutor stop race (async_executor.py #9) | 3 hours | CRITICAL - Orphaned threads |
| P1 | Entry tick reset (foundational.py #15) | 30 min | HIGH - Wrong hold time |
| P1 | Browser null checks (browser_executor.py #5) | 1.5 hours | HIGH - AttributeError |
| P1 | Browser cleanup (browser_executor.py #6) | 2 hours | HIGH - Resource leak |
| P1 | Decimal validation (strategies #16) | 2 hours | HIGH - Bot crash |
| P2 | Observation validation (controller.py #14) | 1 hour | MEDIUM - Better errors |
| P2 | Error context (controller.py #13) | 1 hour | MEDIUM - Easier debugging |
| P2 | Worker heartbeat (async_executor.py #10) | 2 hours | MEDIUM - Detect hangs |
| P2 | Feedback loop (ui_controller.py #4) | 1 hour | MEDIUM - Verify amounts |
| P3 | Floating point (ui_controller.py #3) | 1 hour | MEDIUM - Precision |
| P3 | Timeout validation (browser_executor.py #7) | 1 hour | HIGH - Config bot latency |
| P3 | Selector fallbacks (browser_executor.py #8) | 30 min | MEDIUM - Robustness |
| P4 | Type hints (async_executor.py #11) | 1 hour | LOW - Maintainability |
| P4 | Strategy logging (strategies #17) | 1 hour | LOW - Debugging |

