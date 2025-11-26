# Bulletproof Browser Connection Plan

## Executive Summary

After extensive research, the **most reliable method** for persistent wallet automation is:

**PRIMARY APPROACH: CDP (Chrome DevTools Protocol) Connection to Running Chrome**

This approach:
1. Launches Chrome manually (or via script) with `--remote-debugging-port`
2. REPLAYER connects via CDP to control the existing browser
3. Wallet/session persists because it's YOUR actual Chrome profile
4. Extensions work natively (no MV3 injection issues)

---

## Problem Analysis

### Why Current Approach Fails

| Issue | Root Cause |
|-------|------------|
| Extension visible but not working | Playwright's Chromium bundles don't properly activate MV3 service workers |
| Profile not persisting | Different browser binaries (Playwright Chromium vs Chrome) have incompatible profiles |
| `launch_persistent_context` unreliable | Known Playwright bug with MV3 extensions - service worker doesn't start |

### Research Findings

1. **MV3 Extensions in Playwright**: Documented issues with service worker lifecycle (GitHub #27670)
2. **CDP Connection**: Proven method for wallet automation (Selenium, Puppeteer, Playwright all support it)
3. **Profile Persistence**: Only guaranteed when using the SAME browser binary and profile directory consistently

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         REPLAYER UI                              │
│  [Connect Browser] → Launches Chrome OR connects to existing     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CDP Connection Manager                        │
│  - Checks if Chrome already running on port 9222                 │
│  - If not, launches Chrome with debug port + profile             │
│  - Connects via connect_over_cdp()                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Google Chrome (YOUR system Chrome)                  │
│  --remote-debugging-port=9222                                    │
│  --user-data-dir=~/.gamebot/chrome_profiles/rugs_bot             │
│                                                                  │
│  [Phantom Extension - Native Installation]                       │
│  [Rugs.fun Session - Persistent Cookies]                         │
│  [Wallet Connected - Persistent State]                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phased Development Plan

### Phase 1: CDP Connection Infrastructure (2-3 hours)
**Goal**: Connect REPLAYER to running Chrome via CDP

**Tasks**:
1. Create `CDPBrowserManager` class to replace/wrap `RugsBrowserManager`
2. Implement `check_chrome_running()` - check if Chrome is on port 9222
3. Implement `launch_chrome_with_debug()` - start Chrome with correct flags
4. Implement `connect_via_cdp()` - connect Playwright via CDP
5. Add Chrome binary detection (find `/usr/bin/google-chrome`)

**Deliverables**:
- `browser_automation/cdp_browser_manager.py` (new file)
- Tests for CDP connection

**Code Skeleton**:
```python
class CDPBrowserManager:
    CDP_PORT = 9222
    PROFILE_DIR = Path.home() / ".gamebot" / "chrome_profiles" / "rugs_bot"

    async def connect(self) -> bool:
        """Connect to Chrome via CDP (launch if needed)"""
        if not await self._is_chrome_running():
            await self._launch_chrome()

        self.browser = await self.playwright.chromium.connect_over_cdp(
            f"http://localhost:{self.CDP_PORT}"
        )
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        return True
```

### Phase 2: One-Time Setup Script (1-2 hours)
**Goal**: Interactive script to set up the dedicated Chrome profile with Phantom

**Tasks**:
1. Create `scripts/setup_chrome_profile.py`
2. Launch Chrome with new profile directory
3. User manually installs Phantom extension
4. User manually connects wallet to rugs.fun
5. Script verifies setup is complete
6. Profile is now ready for automation

**User Flow**:
```
$ python scripts/setup_chrome_profile.py

🔧 CHROME PROFILE SETUP FOR REPLAYER
====================================

1. Launching Chrome with dedicated profile...
   Profile: ~/.gamebot/chrome_profiles/rugs_bot

2. Please complete these steps in Chrome:
   [ ] Install Phantom wallet extension from Chrome Web Store
   [ ] Set up your wallet (import or create)
   [ ] Go to rugs.fun
   [ ] Click "Connect" and connect your Phantom wallet
   [ ] Verify you can see your balance

3. When done, press ENTER to verify setup...

✅ Setup verified! Phantom detected, wallet connected.
   Profile saved at: ~/.gamebot/chrome_profiles/rugs_bot

You can now use REPLAYER's Browser → Connect feature.
```

### Phase 3: UI Integration (2-3 hours)
**Goal**: Update REPLAYER UI to use CDP connection

**Tasks**:
1. Update `src/bot/browser_executor.py` to use `CDPBrowserManager`
2. Update `Browser → Connect Browser` menu to:
   - Check if profile exists (prompt setup if not)
   - Connect via CDP
   - Navigate to rugs.fun
3. Add `Browser → Launch Chrome (Manual)` option for debugging
4. Update status displays

**Menu Structure**:
```
Browser
├── Connect to Chrome        (CDP connection)
├── Launch Chrome Manually   (Opens Chrome for debugging)
├── Disconnect
├── ─────────────────
└── Setup Chrome Profile...  (Runs setup script)
```

### Phase 4: XPath Button Automation (2-3 hours)
**Goal**: Ensure button clicking works via CDP connection

**Tasks**:
1. Verify existing `BrowserExecutor` methods work with CDP page
2. Test each button selector (BUY, SELL, percentages, increments)
3. Add retry logic for button clicks
4. Add visual feedback in REPLAYER when bot clicks buttons

**Button Selectors** (from docs/XPATHS.txt):
```python
BUTTON_SELECTORS = {
    'buy': 'button:has-text("BUY")',
    'sell': 'button:has-text("SELL")',
    'clear': 'button:has-text("X"):near(input)',
    'increment_001': 'button:has-text("+0.001")',
    'increment_01': 'button:has-text("+0.01")',
    'increment_10': 'button:has-text("+0.1")',
    'increment_1': 'button:has-text("+1")',
    'half': 'button:has-text("1/2")',
    'double': 'button:has-text("X2")',
    'max': 'button:has-text("MAX")',
    'sell_10': 'button:has-text("10%")',
    'sell_25': 'button:has-text("25%")',
    'sell_50': 'button:has-text("50%")',
    'sell_100': 'button:has-text("100%")',
}
```

### Phase 5: Robustness & Recovery (2-3 hours)
**Goal**: Handle edge cases and failures gracefully

**Tasks**:
1. Auto-reconnect if CDP connection drops
2. Detect if Chrome crashes and prompt restart
3. Add health check pings to verify connection alive
4. Handle page navigation (reload, back, etc.)
5. Add timeout handling for button clicks

**Recovery Flow**:
```
[Connection Lost]
      │
      ▼
[Try Reconnect (3 attempts)]
      │
      ├── Success → Continue
      │
      └── Failure → [Check Chrome Running]
                          │
                          ├── Yes → Reconnect
                          │
                          └── No → [Prompt User]
                                      │
                                      └── "Chrome closed. Relaunch?"
```

### Phase 6: Documentation & Cleanup (1-2 hours)
**Goal**: Production-ready documentation

**Tasks**:
1. Update CLAUDE.md with new browser architecture
2. Create user guide for setup process
3. Update docs/XPATHS.txt if needed
4. Remove deprecated RugsBrowserManager code
5. Add troubleshooting guide

---

## Success Criteria

| Criteria | Requirement |
|----------|-------------|
| Profile Persistence | Phantom wallet stays connected across sessions |
| Manual Connect Option | User can always connect manually if needed |
| Button Automation | All trading buttons clickable via bot |
| Recovery | System recovers from disconnections gracefully |
| Setup Time | < 5 minutes for first-time setup |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Chrome update breaks CDP | CDP is stable protocol, unlikely; document Chrome version |
| Port 9222 in use | Allow configurable port, detect conflicts |
| Profile corruption | Backup profile option, fresh setup script |
| Slow button clicks | Add configurable delays, parallel-safe clicks |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: CDP Infrastructure | 2-3 hours | None |
| Phase 2: Setup Script | 1-2 hours | Phase 1 |
| Phase 3: UI Integration | 2-3 hours | Phase 1, 2 |
| Phase 4: Button Automation | 2-3 hours | Phase 3 |
| Phase 5: Robustness | 2-3 hours | Phase 4 |
| Phase 6: Documentation | 1-2 hours | All |

**Total: 10-16 hours**

---

## Alternative Approaches Considered

### 1. Selenium WebDriver
- **Pros**: More mature, better extension support
- **Cons**: Slower, different API, would require rewriting BrowserExecutor
- **Decision**: Not worth the migration cost

### 2. Puppeteer
- **Pros**: Good CDP support
- **Cons**: Node.js only, different language
- **Decision**: Rejected (Python codebase)

### 3. Synpress (DApp Testing Framework)
- **Pros**: Built for wallet automation
- **Cons**: Overkill for our needs, Cypress/Playwright wrapper
- **Decision**: Too heavyweight, CDP approach is simpler

### 4. Keep Playwright launch_persistent_context
- **Pros**: Current approach
- **Cons**: MV3 extension issues are fundamental Playwright bug
- **Decision**: Rejected - bug is not fixed

---

## Appendix: Key Code References

### CDP Connection (Official Playwright)
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0]
```

### Chrome Launch Command
```bash
google-chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="$HOME/.gamebot/chrome_profiles/rugs_bot" \
    --start-maximized \
    "https://rugs.fun"
```

### Verify CDP Available
```bash
curl http://localhost:9222/json/version
# Should return JSON with Chrome version info
```
