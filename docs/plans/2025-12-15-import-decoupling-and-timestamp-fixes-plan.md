# Feature/Fix Planning Template

## Zero-Context Principle
This plan must be executable by someone with NO prior session context.

---

## Feature: Unblock tests by removing import-time coupling + fix CDP timestamp semantics

### Goal
Make `src/` modules safe to import in tests (no hard dependency explosions or noisy import side effects), and fix CDP timestamp handling to avoid bogus wall-clock times.

### Architecture Impact
- [ ] New module needed? No (keep changes surgical).
- [ ] Existing pattern to follow (check architect.yaml)? Prefer explicit initialization in `src/main.py` over import-time side effects.
- [ ] EventBus events needed? No.
- [ ] UI changes required? No.
- [ ] Thread safety considerations? CDP interceptor changes must remain thread-safe.

### Files to Modify
| File | Change Type | Description |
|------|-------------|-------------|
| `src/tests/test_integration/test_import_side_effects.py` | New | Subprocess-based tests ensuring imports are quiet and don’t require optional deps. |
| `src/config.py` | Modify | Remove import-time validation/logging/exit; add explicit runtime init hooks. |
| `src/sources/websocket_feed.py` | Modify | Make `python-socketio` import optional at module import time to allow mocking in tests. |
| `src/services/__init__.py` | Modify | Avoid heavy imports at package import time (keep stable exports but lazy where needed). |
| `src/sources/__init__.py` | Modify | Avoid heavy imports at package import time (or ensure imports are safe). |
| `src/sources/cdp_websocket_interceptor.py` | Modify | Make `connect`/`disconnect` async; fix timestamp mapping. |
| `src/tests/test_sources/test_cdp_websocket_interceptor.py` | Modify | Add timestamp-mapping test (keep existing tests passing). |
| `src/main.py` | Modify | Ensure runtime initialization (config validation + directory creation) occurs at startup. |

### Tasks (TDD Order)

#### Task 1: Import side-effects are eliminated

**Test First**:
```python
# src/tests/test_integration/test_import_side_effects.py
def test_import_config_is_quiet():
    ...

def test_import_services_and_sources_is_quiet():
    ...
```

**Implementation**:
```python
# src/config.py, src/services/__init__.py, src/sources/__init__.py
```

**Verify**:
```bash
cd src && python3 -m pytest tests/test_integration/test_import_side_effects.py -v
```

#### Task 2: CDP timestamps are not treated as epoch time

**Test First**:
```python
# src/tests/test_sources/test_cdp_websocket_interceptor.py
def test_cdp_timestamp_is_mapped_to_wall_clock_when_monotonic(...):
    ...
```

**Implementation**:
```python
# src/sources/cdp_websocket_interceptor.py
```

**Verify**:
```bash
cd src && python3 -m pytest tests/test_sources/test_cdp_websocket_interceptor.py -v
```

### Verification Criteria
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] No import-time `sys.exit()` from library modules
- [ ] `import config` does not print “Configuration validated successfully”
- [ ] CDP events emit reasonable timestamps

### Risks
- [ ] Startup behavior drift (directories/logging no longer configured by importing `config`) -> Mitigation: move explicit init into `src/main.py`.
- [ ] Subtle dependency on previous import-time side effects -> Mitigation: run full test suite and keep changes minimal/surgical.

