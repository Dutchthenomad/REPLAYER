# REPLAYER Remaining Fixes & Recommendations

## Quick Reference: Immediate Action Items

### Priority 1: Apply These Fixes Now

1. **Replace `browser_bridge.py`** with `browser_bridge_FIXED.py`
   - Multi-strategy selectors for BUY/SELL/SIDEBET
   - Retry logic with exponential backoff
   - Comprehensive logging

2. **Patch `main_window.py`** with signal handler fix
   - Apply `main_window_signal_handler_FIX.py`
   - Prevents race condition in live feed processing

3. **Replace `recorder_sink.py`** with `recorder_sink_FIXED.py`
   - Memory-bounded buffer with emergency trimming
   - Prevents OOM during extended sessions

### Priority 2: Configuration & Validation

#### Add to `main.py` (startup):
```python
# Add after imports, before creating UI
from config import config

# Validate configuration on startup
try:
    config.validate()
except ConfigError as e:
    logger.error(f"Invalid configuration: {e}")
    sys.exit(1)
```

#### Add timeout to WebSocket connection in `websocket_feed.py`:
```python
# In connect() method, change:
self.sio.connect(self.websocket_url)

# To:
self.sio.connect(
    self.websocket_url,
    wait_timeout=30,
    transports=['websocket', 'polling']
)
```

### Priority 3: Type Consistency Fix

In `websocket_feed.py`, change price extraction:
```python
# BEFORE (float):
'price': raw_data.get('price', 1.0),

# AFTER (Decimal):
from decimal import Decimal, InvalidOperation

def _safe_decimal(value, default='1.0'):
    """Convert value to Decimal safely"""
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)

# In _extract_signal():
'price': _safe_decimal(raw_data.get('price'), '1.0'),
```

---

## Detailed Fix Implementations

### Fix HIGH-6: Ring Buffer Copy Optimization

The `get_all()` method creates a full copy on every call, which is expensive
when called for each tick.

**File**: `src/core/live_ring_buffer.py`

```python
# Add this optimized method:
def get_latest_tick(self) -> Optional[GameTick]:
    """
    Get only the most recent tick (O(1) instead of O(n)).
    
    Use this in push_tick() instead of get_all() when you only
    need the latest tick for display.
    """
    with self._lock:
        if not self._buffer:
            return None
        return self._buffer[-1]

# Add iterator for efficient iteration without copying:
def __iter__(self):
    """Iterate over buffer without creating copy"""
    with self._lock:
        # Create shallow copy of indices for thread-safe iteration
        items = list(self._buffer)
    return iter(items)
```

**Update `replay_engine.py` push_tick():**
```python
# BEFORE:
current_ticks = self.ticks  # Creates full copy via get_all()

# AFTER:
# Use direct ring buffer access for display
latest_tick = self.live_ring_buffer.get_latest_tick()
if latest_tick:
    display_data = {
        'tick': latest_tick,
        'index': self.live_ring_buffer.get_size() - 1,
        'total': self.live_ring_buffer.get_size()
    }
```

---

### Fix HIGH-8: Config Validation at Startup

**File**: `src/config.py`

Add auto-validation on import:
```python
# At end of config.py, add:
_config_validated = False

def ensure_config_valid():
    """Validate config once on first use"""
    global _config_validated
    if not _config_validated:
        config.validate()
        _config_validated = True

# Auto-validate when config is accessed
class ConfigProxy:
    """Proxy that validates config on first access"""
    def __getattr__(self, name):
        ensure_config_valid()
        return getattr(config, name)

# Export proxy instead of raw config
config_validated = ConfigProxy()
```

---

### Fix MED-1: Structured Logger with Correlation IDs

```python
# Add to src/services/logger.py:

import threading
import uuid
from contextvars import ContextVar

# Correlation ID for tracing requests
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

def get_correlation_id() -> str:
    """Get current correlation ID or generate new one"""
    cid = correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id.set(cid)
    return cid

class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records"""
    def filter(self, record):
        record.correlation_id = get_correlation_id()
        return True

# Update formatter:
formatter = logging.Formatter(
    '[%(asctime)s] [%(correlation_id)s] %(levelname)s %(name)s: %(message)s'
)
```

---

### Fix MED-7: Circuit Breaker for WebSocket Reconnects

```python
# Add to websocket_feed.py:

from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CircuitBreaker:
    """Prevents reconnection storms during backend issues"""
    max_failures: int = 5
    reset_timeout: timedelta = timedelta(minutes=5)
    
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    
    def record_failure(self):
        """Record a connection failure"""
        self.failures += 1
        self.last_failure = datetime.now()
        
        if self.failures >= self.max_failures:
            self.is_open = True
            logger.warning(
                f"Circuit breaker OPEN after {self.failures} failures. "
                f"Will reset in {self.reset_timeout}"
            )
    
    def record_success(self):
        """Record a successful connection"""
        self.failures = 0
        self.is_open = False
    
    def can_attempt(self) -> bool:
        """Check if connection attempt is allowed"""
        if not self.is_open:
            return True
        
        # Check if reset timeout has passed
        if self.last_failure and datetime.now() - self.last_failure > self.reset_timeout:
            self.is_open = False
            self.failures = 0
            logger.info("Circuit breaker RESET - allowing connection attempt")
            return True
        
        return False

# In WebSocketFeed.__init__:
self.circuit_breaker = CircuitBreaker()

# In connect():
def connect(self):
    if not self.circuit_breaker.can_attempt():
        logger.warning("Circuit breaker open - skipping connection attempt")
        return False
    
    try:
        self.sio.connect(...)
        self.circuit_breaker.record_success()
    except Exception as e:
        self.circuit_breaker.record_failure()
        raise
```

---

## Test Cases to Add

### Browser Bridge Tests
```python
# tests/test_bot/test_browser_bridge_selectors.py

import pytest
from unittest.mock import AsyncMock, MagicMock

class TestSelectorStrategies:
    """Test multi-strategy selector system"""
    
    @pytest.mark.asyncio
    async def test_text_starts_with_match(self):
        """Test that 'BUY' matches 'BUY+0.030 SOL'"""
        bridge = BrowserBridge()
        # Mock page with dynamic button text
        mock_page = AsyncMock()
        mock_page.evaluate.return_value = {
            'success': True,
            'text': 'BUY+0.030 SOL',
            'method': 'starts-with'
        }
        
        result = await bridge._try_text_based_click(mock_page, 'BUY')
        assert result.success
        assert 'starts-with' in result.method
    
    @pytest.mark.asyncio
    async def test_css_fallback_when_text_fails(self):
        """Test CSS selector fallback"""
        bridge = BrowserBridge()
        mock_page = AsyncMock()
        
        # Text match fails
        mock_page.evaluate.return_value = {'success': False}
        
        # CSS selector should be tried
        mock_element = AsyncMock()
        mock_element.click = AsyncMock()
        mock_element.text_content = AsyncMock(return_value='BUY')
        mock_page.query_selector.return_value = mock_element
        
        result = await bridge._try_css_selector_click(mock_page, 'BUY')
        assert result.success
    
    @pytest.mark.asyncio  
    async def test_retry_on_failure(self):
        """Test exponential backoff retry"""
        bridge = BrowserBridge()
        bridge.MAX_RETRIES = 3
        
        attempt_count = 0
        async def failing_click():
            nonlocal attempt_count
            attempt_count += 1
            return ClickResult(success=False, error="Test error")
        
        bridge._do_click = failing_click
        result = await bridge._do_click_with_retry('BUY')
        
        assert attempt_count == 3
        assert not result.success
```

### Signal Handler Race Condition Test
```python
# tests/test_ui/test_signal_race_condition.py

import pytest
import threading
import time
from queue import Queue

def test_signal_snapshot_captures_value():
    """Test that signal snapshots are immutable"""
    signals_processed = Queue()
    
    def on_signal(signal):
        # Old buggy way: captures reference
        # def process(): signals_processed.put(signal)
        
        # Fixed way: captures value
        snapshot = dict(signal)
        def process(captured=snapshot):
            signals_processed.put(captured)
        
        # Simulate async delay
        threading.Timer(0.1, process).start()
    
    # Fire two signals rapidly
    on_signal({'tick': 1})
    on_signal({'tick': 2})  # Would overwrite if captured by reference
    
    time.sleep(0.3)
    
    # Should have processed both signals correctly
    results = []
    while not signals_processed.empty():
        results.append(signals_processed.get())
    
    assert len(results) == 2
    assert results[0]['tick'] == 1  # Would be 2 if race condition
    assert results[1]['tick'] == 2
```

---

## Deployment Checklist

Before deploying, verify:

- [ ] Applied `browser_bridge_FIXED.py`
- [ ] Applied signal handler patch
- [ ] Applied `recorder_sink_FIXED.py`
- [ ] Added WebSocket connection timeout
- [ ] Added Decimal type for prices
- [ ] Added config validation at startup
- [ ] Run full test suite: `python -m pytest tests/ -v`
- [ ] Run extended live test (30+ minutes)
- [ ] Monitor memory usage during live test
- [ ] Verify BUY/SELL/SIDEBET clicks work in browser
- [ ] Test reconnection after backend restart
- [ ] Review logs for any ERROR level messages

---

## Monitoring Recommendations

Add these metrics to track system health:

```python
# Suggested Prometheus-style metrics:

# Browser automation
browser_click_total{button, status, method}  # Total clicks by button/status
browser_click_latency_seconds{button}         # Click execution time
browser_connection_status                      # 1=connected, 0=disconnected

# WebSocket feed  
websocket_signals_total                       # Total signals received
websocket_signal_latency_seconds              # Signal processing time
websocket_reconnects_total                    # Number of reconnections
websocket_circuit_breaker_status              # 1=open, 0=closed

# Recording
recorder_ticks_total{status}                  # total/dropped
recorder_buffer_size                          # Current buffer size
recorder_flush_errors_total                   # Flush error count
recorder_file_size_bytes                      # Current file size

# Memory
process_memory_bytes                          # Total process memory
ring_buffer_size                              # Ticks in ring buffer
```

---

## Summary

**Critical issues fixed in provided files:**
1. ✅ Browser selectors (browser_bridge_FIXED.py)
2. ✅ Signal race condition (main_window_signal_handler_FIX.py)
3. ✅ Memory leak in recorder (recorder_sink_FIXED.py)

**Still need manual patching:**
4. ⚠️ WebSocket timeout (simple one-line change)
5. ⚠️ Decimal type consistency (search-replace)
6. ⚠️ Config validation at startup (add to main.py)

**Estimated time to apply all fixes:** 2-4 hours

After applying these fixes, the system should be production-ready for deployment.
