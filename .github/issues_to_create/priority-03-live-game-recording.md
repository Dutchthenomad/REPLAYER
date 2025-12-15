---
title: "[Priority 3] Live Game Recording Session (20-30 Games)"
labels: data-collection, priority-high, phase-12
assignees: ""
---

## Goal
Record 20-30 live games with authenticated CDP WebSocket data for RL training.

## Context
All recording infrastructure is complete (Phase 10). Need real gameplay data with server-authenticated events.

## Prerequisites
- [ ] Priority 2 complete (server state authority)
- [ ] Chrome connected via CDP
- [ ] Phantom wallet authenticated to rugs.fun

## Tasks
- [ ] Manual gameplay session: Play 20-30 games while recording
- [ ] Verify recordings capture complete price histories (500+ ticks/game)
- [ ] Verify recordings capture server-authenticated player updates
- [ ] Verify recordings capture game lifecycle events (START/END)
- [ ] Verify recordings capture all trade actions with server confirmations
- [ ] Export recordings to `/home/nomad/rugs_recordings/`
- [ ] Generate recording quality report (coverage, completeness, anomalies)

## Success Criteria
- 20-30 complete game recordings
- All recordings include authenticated server state
- No missing price data or lifecycle gaps
- Recordings validated for RL training compatibility
- Quality report shows >95% data completeness

## Dependencies
- Priority 2 complete (server state authority)

## Related Files
- `src/core/recorder_sink.py` - Recording engine
- `src/services/rag_ingester.py` - Event cataloging
- `src/sources/cdp_websocket_interceptor.py` - CDP interception

## Estimated Effort
2-3 hours of gameplay
