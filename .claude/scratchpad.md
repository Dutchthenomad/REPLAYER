# REPLAYER Session Scratchpad

Last Updated: 2025-12-14 21:00

---

## Quick Start for Fresh Sessions

### PRIMARY: Technical Debt Audit (Parallel Track)

```
Read the following files to understand the current project state:
1. /home/nomad/Desktop/REPLAYER/docs/plans/2025-12-14-technical-debt-audit-design.md
2. /home/nomad/Desktop/REPLAYER/CLAUDE.md

Then check current issues:
gh issue list --repo Dutchthenomad/REPLAYER --milestone "Tech Debt Audit - Phase 1: Mapping"

I'm working on the Technical Debt Audit using the parallel track approach.
Methodology: "Working Effectively with Legacy Code" (Michael Feathers)

Current phase: Phase 1 - Mapping
- Create repair/technical-debt-audit branch
- Run automated analysis (vulture, pydeps, radon)
- Write characterization tests
- Create issues from findings

Key tracking issues:
- #17: Master tracking issue
- #18: Recording state mismatch (P0-critical) - logs "disabled", UI shows "enabled"
- #19: Venv migration from rugs-rl-bot to REPLAYER (P1-high)

Test command: /home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -m pytest src/tests/ -v --tb=short
```

---

## Technical Debt Audit Status

**Approach:** Parallel Track (repair branch alongside main, cherry-pick urgent fixes)

**GitHub Infrastructure:** COMPLETE
- Labels: `tech-debt/*`, `P0-P3`, `component/*`
- Milestones: Phases 1-4
- Tracking issues: #17, #18, #19

### Phase 1: Mapping (CURRENT)
- [x] Design document: `docs/plans/2025-12-14-technical-debt-audit-design.md`
- [x] GitHub labels created
- [x] Milestones created
- [x] Tracking issues created
- [ ] Create `repair/technical-debt-audit` branch
- [ ] Run automated analysis (vulture, pydeps, radon)
- [ ] Write characterization tests for event flow
- [ ] Write characterization tests for UI state
- [ ] Write characterization tests for recording
- [ ] Generate findings report
- [ ] Create individual issues from findings

### Phase 2: Foundation (PENDING)
- [ ] Fix WebSocket → EventBus → UI state conflicts
- [ ] Consolidate event handling

### Phase 3: Recording (PENDING)
- [ ] Fix recording state mismatch (#18)
- [ ] Consolidate recording services

### Phase 4: Infrastructure (PENDING)
- [ ] Migrate venv to REPLAYER (#19)
- [ ] Set up pre-commit hooks
- [ ] Set up GitHub Actions CI
- [ ] Enable branch protection

---

## Known Bugs

### Recording State Mismatch (#18) - P0-CRITICAL
- **Symptom:** Log shows `recording disabled` but UI shows enabled
- **Location:** `core/replay_engine.py:352`
- **Root cause:** Multiple sources of truth:
  - `replay_engine.auto_recording` (from config)
  - `main_window.recording_var` (UI checkbox)
  - `recorder_sink.is_recording()` (actual state)
  - `recording_controller` state

### External venv Dependency (#19) - P1-HIGH
- **Current:** `/home/nomad/Desktop/rugs-rl-bot/.venv`
- **Target:** `/home/nomad/Desktop/REPLAYER/.venv`

---

## Commands

```bash
# View audit issues
gh issue list --milestone "Tech Debt Audit - Phase 1: Mapping"

# Run tests (using rugs-rl-bot venv until #19 complete)
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/python -m pytest src/tests/ -v --tb=short

# Start repair branch (when ready)
git checkout -b repair/technical-debt-audit

# Run dead code analysis
pip install vulture pydeps radon
vulture src/ --min-confidence 80 > reports/dead_code.txt
pydeps src/ --max-bacon 3 -o reports/dependency_graph.svg
radon cc src/ -a -s > reports/complexity.txt

# View milestones
gh api repos/Dutchthenomad/REPLAYER/milestones
```

---

## Key Files for Audit

| File | Purpose | Issue |
|------|---------|-------|
| `docs/plans/2025-12-14-technical-debt-audit-design.md` | Full audit methodology | #17 |
| `src/core/replay_engine.py:352` | Recording state bug location | #18 |
| `src/ui/main_window.py:221` | recording_var initialization | #18 |
| `src/sources/websocket_feed.py` | Event flow entry point | Phase 2 |

---

## Previous Work (Reference)

### Issue #8 - WebSocket Server State Fix
- Hardcoded credentials approach implemented
- `HARDCODED_PLAYER_ID = "did:privy:cmaibr7rt0094jp0mc2mbpfu4"`
- `HARDCODED_USERNAME = "Dutch"`

### Phase 11 - CDP WebSocket Interception
- Complete and merged to main
- Debug Terminal wired to WebSocketFeed
- Events publishing to EventBus via `WS_RAW_EVENT`

### Raw Capture Tool
- Location: Developer Tools menu
- Output: `/home/nomad/rugs_recordings/raw_captures/`
- 554 events captured in test session

---

## Session History
- 2025-12-14: Technical Debt Audit design complete, GitHub infrastructure created
- 2025-12-14: Phase 11 merged, Debug Terminal wired to WebSocketFeed
- 2025-12-13: Issues #8, #9 design documents created
- 2025-12-12: Hardcoded credentials workaround implemented
- 2025-12-10: Raw Capture Tool implementation complete
