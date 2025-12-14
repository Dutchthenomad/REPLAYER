# Rugs Replay Viewer - Quick Reference

**One-Page Summary for Quick Context**

---

## 🎯 What Is This?

A **modular replay viewer** for Rugs.fun game recordings that lets you:
- Load game recordings (JSONL format)
- Watch games play back
- Run automated bots with different strategies
- See bot decisions in real-time
- Analyze bot performance

**Origin**: Complete refactor of crashing 2400-line monolithic script → 31 stable modules

---

## 📊 Current Status

**Phase**: 2B Complete ✅
**Next**: Issue identification & resolution
**Test Status**: 100% passing (6/6 automated checks, zero crashes)

**What Works**:
✅ Game loading & playback
✅ Bot system (3 strategies)
✅ Real-time visualization
✅ Event-driven updates
✅ Thread-safe state management

**What's Next**:
⏳ User testing & issue identification
⏳ Critical fixes
⏳ Feature enhancements

---

## 🚀 Quick Start

```bash
# Navigate to project
cd /home/nomad/Desktop/REPLAYER/rugs_replay_viewer

# Launch GUI
./RUN_GUI.sh

# OR run tests
python3 test_gui_automated.py  # Automated test (6 checks)
python3 main_cli.py            # CLI test (full game)
```

**GUI Usage**:
1. Load Game → Select JSONL file
2. Select Strategy → conservative/aggressive/sidebet
3. Enable Bot → Click button
4. Play → Watch bot play

---

## 📁 Key Files

**Entry Points**:
- `main.py` - GUI launcher
- `main_cli.py` - CLI test tool
- `RUN_GUI.sh` - Quick launcher

**Core Components**:
- `core/game_state.py` - Centralized state (thread-safe)
- `core/trade_manager.py` - Trade execution
- `bot/controller.py` - Bot decision cycle
- `ui/main_window.py` - GUI

**Configuration**:
- `config.py` - All settings

**Tests**:
- `test_gui_automated.py` - Automated GUI test
- `tests/test_core_integration.py` - Core tests
- `tests/test_bot_system.py` - Bot tests

---

## 🏗️ Architecture

```
UI (Tkinter)
  ↓ subscribes to
EventBus (pub/sub)
  ↑ publishes
GameState ← TradeManager ← BotController
  ↑               ↑              ↑
  └───────────────┴──────────────┘
         BotInterface
```

**Key Patterns**:
- Event-driven (no polling)
- Strategy pattern (pluggable bots)
- Thread-safe (RLock)
- Dependency injection

---

## 📚 Documentation

**In DOCS** (`/home/nomad/Desktop/REPLAYER/DOCS/`):
- `CLAUDE.md` ⭐ - **Main context** (this project)
- `KNOWN_ISSUES.md` - Issue tracking
- `NEXT_STEPS.md` - Roadmap
- `GAME_MECHANICS.md` - Rugs.fun rules
- `RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md` - Deep game knowledge

**In Project**:
- `PHASE_1_COMPLETE.md` - Core infrastructure summary
- `PHASE_2_COMPLETE.md` - Bot & GUI summary
- `GUI_TEST_VERIFICATION.md` - Test results

---

## 🎯 Phase Timeline

| Phase | Status | Duration | What |
|-------|--------|----------|------|
| Phase 1 | ✅ Done | 2h | Core infrastructure |
| Phase 2A | ✅ Done | 1.5h | Bot system |
| Phase 2B | ✅ Done | 1.5h | GUI integration |
| Phase 3A | ⏳ Next | 4-8h | Issue resolution |
| Phase 3B | 📋 Planned | 6-10h | Feature enhancement |
| Phase 4 | 🔮 Future | TBD | Advanced features |

**Total Time Invested**: 5 hours (monolith → working modular system)

---

## 💡 Key Decisions

**Architectural**:
- Event-driven (not polling) ✅
- Modular (not monolithic) ✅
- Thread-safe from start ✅
- Strategy pattern for bots ✅
- Decimal precision for money ✅

**Technical**:
- Tkinter for GUI (stdlib, no deps)
- JSONL for game files
- Python 3.8+ (type hints)
- No external deps yet

---

## 🔧 Common Commands

```bash
# Run GUI
./RUN_GUI.sh

# Test core
python3 tests/test_core_integration.py

# Test bot
python3 tests/test_bot_system.py

# Test GUI
python3 test_gui_automated.py

# CLI test
python3 main_cli.py
```

---

## 🐛 Troubleshooting

**GUI won't start**:
- Check Tkinter: `python3 -c "import tkinter"`
- Check errors: `python3 main.py 2>&1`

**Bot doesn't work**:
- Check console for errors
- Try different strategy
- Verify game file is valid

**No updates**:
- Check event bus subscriptions
- Verify playback thread running

---

## 📈 Metrics

**Code**:
- Files: 31
- Lines: ~3,200
- Max file: 450 lines (was 2400)
- Modules: 5 (models, services, core, bot, ui)

**Tests**:
- Core: 50/50 passing
- Bot: All passing
- GUI: 6/6 passing
- Crashes: 0

**Performance**:
- Playback: 10 ticks/sec default
- Memory: Bounded (deques with maxlen)
- Thread-safe: Yes (RLock)

---

## 🎯 Success Criteria

**Foundation** (✅ Complete):
- [x] Stable architecture
- [x] No crashes
- [x] Event-driven
- [x] Testable
- [x] Documented

**Next Milestones**:
- [ ] All critical issues fixed
- [ ] Chart visualization added
- [ ] Bot strategies refined
- [ ] User satisfied with features

---

## 📞 Quick Links

**Project Location**: `/home/nomad/Desktop/REPLAYER/rugs_replay_viewer/`
**Documentation**: `/home/nomad/Desktop/REPLAYER/DOCS/`
**Game Recordings**: `~/rugs_recordings/`

**Key Docs**:
- Main Context: `DOCS/CLAUDE.md`
- Issues: `DOCS/KNOWN_ISSUES.md`
- Roadmap: `DOCS/NEXT_STEPS.md`
- Game Rules: `DOCS/GAME_MECHANICS.md`

---

## 🚦 For Next Session

**Read First**: `DOCS/CLAUDE.md` (comprehensive context)

**User Tasks**:
1. Test GUI with real games
2. Document issues in `KNOWN_ISSUES.md`
3. Prioritize features

**Assistant Tasks**:
1. Fix critical issues
2. Add prioritized features
3. Update documentation

---

**Last Updated**: 2025-11-03
**Status**: Foundation complete, awaiting user feedback
**Version**: 1.0.0

---

*This is a quick reference. See `CLAUDE.md` for comprehensive context.*
