# Documentation - Rugs Replay Viewer

**Purpose**: Comprehensive knowledge base and project documentation
**Last Updated**: 2025-11-03

---

## 📚 Documentation Structure

### **⭐ Start Here**

**`CLAUDE.md`** - **Main project context file**
- Complete project overview
- Architecture and design
- File structure
- Development guidelines
- **Read this first for comprehensive understanding**

**`PROJECT_SUMMARY.md`** - **Quick reference**
- One-page summary
- Quick start guide
- Common commands
- Key metrics
- **Read this for quick context**

---

### 📋 Project Status

**`PHASE_1_COMPLETE.md`** - Phase 1 summary (Core Infrastructure)
- Data models, services, core logic
- Configuration system
- Testing results (50/50 passing)

**`PHASE_2_COMPLETE.md`** - Phase 2 summary (Bot & GUI)
- Bot system implementation
- GUI integration
- Complete feature list
- Architecture benefits

**`GUI_TEST_VERIFICATION.md`** - Test verification report
- Automated test results (6/6 passing)
- What was tested
- Success criteria

**`CHECKPOINT_1C_PROGRESS.md`** - Refactor progress notes
- Historical context
- Migration from monolithic script

---

### 🐛 Issue Tracking

**`KNOWN_ISSUES.md`** - Issue tracking
- All known bugs and problems
- Priority assignments
- Fix plans
- Resolution status
- **Update this as issues are found/fixed**

---

### 🗺️ Roadmap

**`NEXT_STEPS.md`** - Project roadmap
- Immediate actions
- Short-term goals (Phase 3)
- Medium-term goals (Phase 4)
- Long-term vision (Phase 5+)
- Decision points
- **Update this as priorities change**

---

### 🎮 Game Mechanics Knowledge

**`GAME_MECHANICS.md`** - Comprehensive game rules
- Critical data fields (price, balance, bet amount)
- Game phases (cooldown, presale, active, rugged)
- Side bet mechanics (5:1 payout, 40-tick window)
- Bot decision logic framework
- Socket.IO architecture notes

**`RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md`** - RAG-style knowledge system
- **Instant liquidation rule** (most important!)
- Presale mechanics
- Position & bankroll mechanics
- Side bet integration with training
- Meta-layer treasury management
- Rug event mechanics
- Success definitions
- Trading zones
- Volatility & probability analysis
- **Critical for bot strategy development**

**`side_bet_mechanics_v2.md`** - Side bet deep dive
- Detailed side bet rules
- Timing strategies
- Probability curves
- Expected value calculations

**`SIDEbET kNOWhOW.txt`** - Side bet probability analysis
- Historical data analysis
- Optimal timing recommendations
- Breakeven calculations
- Risk/reward profiles

---

## 📖 How to Use This Documentation

### For New Sessions (Assistant)

**Quick Context**:
1. Read `PROJECT_SUMMARY.md` (2 minutes)
2. Check `KNOWN_ISSUES.md` for current problems
3. Check `NEXT_STEPS.md` for priorities

**Comprehensive Context**:
1. Read `CLAUDE.md` (10 minutes)
2. Review relevant phase completion docs
3. Check game mechanics docs if working on bot strategies

### For Continuing Work

**Before Starting**:
- Check `KNOWN_ISSUES.md` for new issues
- Review `NEXT_STEPS.md` for current phase
- Read relevant test verification docs

**After Completing Work**:
- Update `KNOWN_ISSUES.md` (if issues resolved)
- Update `NEXT_STEPS.md` (if priorities changed)
- Create new completion doc (if phase finished)
- Update `CLAUDE.md` (if architecture changed)

### For Bot Strategy Development

**Required Reading**:
1. `GAME_MECHANICS.md` - Core rules and constraints
2. `RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md` - Critical mechanics and patterns
3. `side_bet_mechanics_v2.md` - Side bet strategies

**Key Concepts to Understand**:
- Instant liquidation on rug (positions lost)
- Side bets as hedges (5:1 payout)
- Presale vs active phase mechanics
- Trading zones (risk levels)
- Volatility spike warnings
- Meta-layer treasury patterns

---

## 🔄 Document Lifecycle

### When to Update Each Document

**`CLAUDE.md`** - Update when:
- Architecture changes significantly
- New major features added
- File structure changes
- Development guidelines change
- Major milestones reached

**`KNOWN_ISSUES.md`** - Update when:
- New issues discovered
- Issues resolved
- Priorities change
- Workarounds found

**`NEXT_STEPS.md`** - Update when:
- Priorities change
- Phases complete
- New features planned
- Roadmap adjusts

**`PROJECT_SUMMARY.md`** - Update when:
- Status changes
- Metrics change significantly
- Quick reference info outdated

**Phase docs** (PHASE_X_COMPLETE.md) - Created when:
- Major phase completes
- Significant milestone reached
- Architecture evolution documented

---

## 📊 Documentation Metrics

**Total Documents**: 11 markdown files

**By Category**:
- Context: 2 (CLAUDE.md, PROJECT_SUMMARY.md)
- Status: 4 (PHASE_1/2_COMPLETE.md, GUI_TEST_VERIFICATION.md, CHECKPOINT_1C_PROGRESS.md)
- Planning: 2 (KNOWN_ISSUES.md, NEXT_STEPS.md)
- Knowledge: 3 (GAME_MECHANICS.md, RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md, side_bet_mechanics_v2.md)

**Total Size**: ~140 KB of documentation

---

## 🎯 Documentation Goals

**Completeness**: ✅
- All aspects of project documented
- Historical context preserved
- Future plans outlined

**Clarity**: ✅
- Quick reference available
- Comprehensive details available
- Clear structure

**Maintainability**: ✅
- Easy to update
- Clear update guidelines
- Version tracking

**Discoverability**: ✅
- This README guides to right docs
- Clear naming
- Organized structure

---

## 📞 Quick Reference Links

**Start Here**:
- New to project? → `CLAUDE.md`
- Need quick facts? → `PROJECT_SUMMARY.md`
- Want to help? → `KNOWN_ISSUES.md` + `NEXT_STEPS.md`

**Development**:
- Architecture? → `CLAUDE.md` (Architecture section)
- Testing? → `GUI_TEST_VERIFICATION.md`
- Bot strategies? → `RUGS_GAME_MECHANICS_KNOWLEDGE_BASE.md`

**Planning**:
- What's broken? → `KNOWN_ISSUES.md`
- What's next? → `NEXT_STEPS.md`
- What's done? → `PHASE_X_COMPLETE.md`

---

**Last Updated**: 2025-11-03
**Status**: Complete and comprehensive
**Maintainer**: Update with each significant change

---

*This README serves as a guide to all project documentation. Keep it current as documentation evolves.*
