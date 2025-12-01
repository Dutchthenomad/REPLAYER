# PRODUCTION READINESS PLAN - REPLAYER

## Overview
This document outlines a phased approach to address all critical issues identified in the comprehensive audit and bring REPLAYER to production-ready status.

**Timeline**: 4 weeks (28 days)
**Priority**: Fix critical issues first, then high/medium priority
**Approach**: Incremental improvements with testing at each phase

---

## PHASE 10: CRITICAL FIXES (Days 1-5)
**Goal**: Fix showstopper bugs that prevent production deployment

### 10.1: Browser Automation Path Fix (Day 1)
**Problem**: Fragile path manipulation in browser_executor.py
**Solution**:
```python
# Create proper package structure
browser_automation/
├── __init__.py
├── cdp_browser_manager.py
└── rugs_browser.py

# Use relative imports
from ..browser_automation import CDPBrowserManager
```
**Files to modify**:
- `src/bot/browser_executor.py` - Remove sys.path manipulation
- `browser_automation/__init__.py` - Create with proper exports
- `setup.py` - Add browser_automation as package

**Validation**:
- Run `python -m pytest tests/test_bot/test_browser_executor.py`
- Verify imports work from any directory

### 10.2: Memory Management Fix (Days 2-3)
**Problem**: Unbounded memory growth in GameState
**Solution**:
```python
class GameState:
    def __init__(self):
        self._archival_thread = threading.Thread(target=self._archival_worker)
        self._archival_queue = queue.Queue()

    def _archival_worker(self):
        """Archive old data to disk periodically"""
        while self._running:
            if len(self._history) > MAX_HISTORY_SIZE * 0.9:
                # Archive oldest 50% to disk
                to_archive = self._history[:MAX_HISTORY_SIZE // 2]
                self._archive_to_disk(to_archive)
                self._history = self._history[MAX_HISTORY_SIZE // 2:]
```
**Files to modify**:
- `src/core/game_state.py` - Add archival mechanism
- `src/core/state_archiver.py` - New module for disk archival
- `src/config.py` - Add ARCHIVE_PATH configuration

**Validation**:
- Memory profiling with `memory_profiler`
- Run for 1 hour, verify memory stays bounded

### 10.3: WebSocket Decimal Conversion (Day 3)
**Problem**: Late conversion from float to Decimal
**Solution**:
```python
class GameSignal:
    def __post_init__(self):
        # Convert price to Decimal immediately
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))

    @classmethod
    def from_raw_data(cls, data: dict):
        """Factory method with immediate conversion"""
        data['price'] = Decimal(str(data.get('price', 0)))
        return cls(**data)
```
**Files to modify**:
- `src/sources/websocket_feed.py` - Add conversion at ingestion
- `src/models/game_tick.py` - Ensure Decimal consistency

**Validation**:
- Unit tests with edge cases (0.1 + 0.2 != 0.3 in float)
- Verify no precision loss in calculations

### 10.4: EventBus Shutdown Fix (Days 4-5)
**Problem**: Race condition during shutdown
**Solution**:
```python
class EventBus:
    def __init__(self):
        self._shutdown_event = threading.Event()

    def _process_events(self):
        while not self._shutdown_event.is_set():
            try:
                event = self._queue.get(timeout=0.1)
                if event is not None:
                    self._dispatch(event)
            except queue.Empty:
                continue

    def stop(self):
        self._shutdown_event.set()
        if self._thread:
            self._thread.join(timeout=2)
```
**Files to modify**:
- `src/services/event_bus.py` - Replace sentinel with Event

**Validation**:
- Stress test with rapid start/stop cycles
- Verify no deadlocks or hanging threads

---

## PHASE 11: HIGH PRIORITY FIXES (Days 6-12)

### 11.1: Browser Reconnection Logic (Days 6-7)
**Implementation**:
```python
class CDPBrowserManager:
    async def ensure_connected(self):
        """Auto-reconnect with exponential backoff"""
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            if await self._is_connected():
                return True

            wait_time = min(2 ** attempt, 30)  # Max 30s
            logger.info(f"Reconnecting in {wait_time}s...")
            await asyncio.sleep(wait_time)

            if await self.connect():
                return True
        return False
```
**Files to modify**:
- `browser_automation/cdp_browser_manager.py`
- Add health check loop
- Add reconnection on disconnect

### 11.2: Thread Safety Audit (Days 8-9)
**Process**:
1. Grep for all UI updates not using TkDispatcher
2. Wrap all direct UI calls in dispatcher.submit()
3. Add thread safety tests

**Files to audit**:
- `src/ui/main_window.py`
- `src/ui/panels.py`
- `src/ui/bot_config_panel.py`
- All UI components

### 11.3: File Handle Management (Days 10-11)
**Solution**: Use context managers everywhere
```python
# Before
file = open(path, 'w')
file.write(data)
file.close()

# After
with open(path, 'w') as file:
    file.write(data)
```
**Files to modify**:
- `src/core/recorder_sink.py`
- Any file I/O operations

### 11.4: Remove Backup Files (Day 12)
**Actions**:
```bash
# Remove backup files
rm src/ui/main_window.py.backup
rm src/ui/main_window.py.pre_optimization_backup
rm src/ui/main_window.py.old_ui

# Add to .gitignore
echo "*.backup" >> .gitignore
echo "*.old" >> .gitignore
```

---

## PHASE 12: MEDIUM PRIORITY IMPROVEMENTS (Days 13-19)

### 12.1: Async/Sync Architecture (Days 13-14)
**Decision**: Move to fully async architecture
- Convert BotController to async
- Use asyncio.run_in_executor for sync bridges
- Simplify error propagation

### 12.2: Configuration Centralization (Days 15-16)
**Implementation**:
```python
# src/config.py
class Config:
    # Queue sizes
    EVENT_BUS_QUEUE_SIZE = int(os.getenv('EVENT_BUS_QUEUE_SIZE', 5000))
    TK_DISPATCHER_QUEUE_SIZE = int(os.getenv('TK_DISPATCHER_QUEUE_SIZE', 1000))

    # Timeouts
    CDP_CONNECT_TIMEOUT = int(os.getenv('CDP_CONNECT_TIMEOUT', 30))

    # File limits
    MAX_RECORDING_SIZE = int(os.getenv('MAX_RECORDING_SIZE', 100_000_000))
```

### 12.3: Input Validation (Days 17-18)
**Create validation module**:
```python
# src/core/validators.py
def validate_bet_amount(amount: Decimal) -> bool:
    if amount < Decimal('0.001'):
        raise ValueError("Bet amount must be >= 0.001")
    if amount > Decimal('100'):
        raise ValueError("Bet amount must be <= 100")
    return True
```

### 12.4: Async File I/O (Day 19)
**Use aiofiles for non-blocking I/O**:
```python
import aiofiles

async def write_recording(self, data):
    async with aiofiles.open(self.path, 'a') as f:
        await f.write(json.dumps(data) + '\n')
```

---

## PHASE 13: PERFORMANCE OPTIMIZATION (Days 20-23)

### 13.1: WebSocket Latency Buffer (Day 20)
**Implement circular buffer**:
```python
class CircularBuffer:
    def __init__(self, size=1000):
        self._buffer = deque(maxlen=size)

    def add(self, value):
        self._buffer.append(value)  # Auto-drops oldest
```

### 13.2: Lock Optimization (Days 21-22)
**Implement read-write locks**:
```python
import threading

class GameState:
    def __init__(self):
        self._lock = threading.RWLock()  # Or use readerwriterlock package

    def get(self, key):
        with self._lock.read_lock():
            return self._state.get(key)

    def update(self, **kwargs):
        with self._lock.write_lock():
            self._state.update(kwargs)
```

### 13.3: Performance Profiling (Day 23)
- Profile with cProfile
- Identify bottlenecks
- Optimize hot paths

---

## PHASE 14: SECURITY & TESTING (Days 24-28)

### 14.1: Security Hardening (Days 24-25)
**Fix command injection**:
```python
# Use list format for subprocess
cmd = [chrome_binary, f'--remote-debugging-port={port}', '--user-data-dir', str(profile)]
subprocess.Popen(cmd)  # Not string concatenation
```

**Encrypt configuration**:
```python
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self._key = Fernet.generate_key()
        self._cipher = Fernet(self._key)

    def encrypt_config(self, config):
        return self._cipher.encrypt(json.dumps(config).encode())
```

### 14.2: Comprehensive Testing (Days 26-27)
**Test Suite Expansion**:
1. **Load Testing**:
   - Simulate 1000 ticks/second
   - Run for 24 hours
   - Monitor memory and CPU

2. **Failure Injection**:
   - Kill Chrome process
   - Disconnect network
   - Fill queues
   - Corrupt data

3. **Race Condition Testing**:
   - Use threading sanitizers
   - Stress test with many threads
   - Verify no deadlocks

### 14.3: Documentation & Deployment (Day 28)
**Final steps**:
1. Update all documentation
2. Create deployment guide
3. Set up monitoring
4. Create rollback plan
5. Production deployment checklist

---

## Implementation Tracking

### Daily Checklist Template
```markdown
## Day X - Phase Y.Z: [Task Name]

### Morning
- [ ] Review task requirements
- [ ] Set up test cases
- [ ] Create feature branch

### Implementation
- [ ] Code changes
- [ ] Unit tests
- [ ] Integration tests

### Evening
- [ ] Code review
- [ ] Documentation update
- [ ] Commit and push

### Blockers
- None / List any issues

### Notes
- Additional observations
```

---

## Success Criteria

### Phase 10 (Critical Fixes)
- [ ] No import errors regardless of working directory
- [ ] Memory stays under 500MB for 1-hour session
- [ ] All financial calculations use Decimal
- [ ] Clean shutdown without deadlocks

### Phase 11 (High Priority)
- [ ] Browser auto-reconnects on disconnect
- [ ] No UI freezes or crashes
- [ ] No file handle leaks
- [ ] Repository clean of backup files

### Phase 12 (Medium Priority)
- [ ] Consistent async architecture
- [ ] All configuration centralized
- [ ] Input validation on all user inputs
- [ ] Non-blocking file I/O

### Phase 13 (Performance)
- [ ] Latency buffer bounded to 1000 entries
- [ ] Read operations don't block writes
- [ ] <100ms response time for all operations

### Phase 14 (Security & Testing)
- [ ] No command injection vulnerabilities
- [ ] Sensitive data encrypted
- [ ] 24-hour stress test passes
- [ ] All tests passing (300+ tests)

---

## Risk Mitigation

### Rollback Plan
1. Tag current version before changes
2. Create backups of critical files
3. Test rollback procedure
4. Document rollback steps

### Monitoring Setup
1. Application logs to file
2. Performance metrics collection
3. Error rate monitoring
4. Alert thresholds

### Contingency Planning
- If Phase 10 takes longer: Extend timeline, focus on critical only
- If memory issues persist: Implement database backend
- If performance degrades: Consider microservices architecture

---

## Next Steps

1. Review this plan with stakeholders
2. Set up tracking dashboard
3. Create git branches for each phase
4. Begin Phase 10.1 immediately

**Estimated Completion**: 28 days from start
**Confidence Level**: 85% (with dedicated effort)

---

*Plan Created: November 24, 2025*
*Target Completion: December 22, 2025*