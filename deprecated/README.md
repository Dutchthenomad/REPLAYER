# Deprecated Code Archive

This directory contains code and documentation that has been superseded or is no longer actively maintained, but is preserved for reference.

**Created**: 2025-11-28
**Cleanup Session**: Repository cleanup before comprehensive audit

---

## 📁 Directory Structure

### `debug-scripts/` (7 files)

One-off debug scripts and utilities used during development. These are not part of the production codebase but may be useful for reference.

**Scripts**:
- `test_async_manager.py` - AsyncLoopManager integration test
- `diagnose_button_forwarding.py` - Button click debugging utility
- `extract_rugs_selectors.py` - XPath extraction tool for browser automation
- `extracted_selectors.py` - Generated output from XPath extraction
- `extracted_selectors.json` - JSON output of extracted selectors
- `test_cdp_connection.py` - CDP browser connection testing
- `test_reliable_connection.py` - Browser connection reliability testing

**Why Deprecated**: These were scratch pad scripts used during specific debugging sessions. The functionality has been integrated into the main codebase or is no longer needed.

**Safe to Delete?** Yes, after 3-6 months if not referenced.

---

### `documentation/` (15 files)

Outdated documentation from completed phases, audit reports, and session summaries that have been superseded by more recent documentation.

#### Audit Reports (6 files)
- `AUDIT_EXECUTIVE_SUMMARY.md`
- `AUDIT_FINDINGS_BY_FILE.md`
- `AUDIT_README.md`
- `BOT_SYSTEM_AUDIT_REPORT.md`
- `CODE_AUDIT_REPORT.md`
- `COMPREHENSIVE_AUDIT_REPORT.md`

**Status**: Multiple versions of audit reports created during different sessions. Latest audit results are in `docs/` (active).

#### Completion Reports (7 files)
- `BROWSER_CONNECTION_COMPLETE.md` - Phase 9 completion
- `BUTTON_CLICK_FIXES.md` - Button system fixes
- `BUTTON_FORWARDING_WIRED.md` - Button forwarding implementation
- `CRITICAL_BUGS_FIXED.md` - Bug fix summary
- `DEMO_INCREMENTAL_CLICKING.md` - Incremental clicking documentation
- `PHASE_1_READY_FOR_TESTING.md` - Phase 1 completion
- `PHASE_3_REFACTOR_PLAN.md` - Phase 3 refactor planning

**Status**: Historical phase completion docs. Information has been integrated into `CLAUDE.md` and `docs/` phase completion docs.

#### Session Summaries & Planning (4 files)
- `SESSION_SUMMARY_2025-11-18.md` - Session summary
- `SESSION_SUMMARY_CRITICAL_FIXES.md` - Critical fixes session
- `NEXT_SESSION_PLAN.md` - Planning document (outdated)
- `PRODUCTION_READINESS_PLAN.md` - Production readiness (superseded)

**Status**: Session summaries and planning docs that have been completed or superseded.

**Safe to Delete?** After 6 months, or when confirmed no longer referenced.

---

## 🔍 How to Use This Archive

### When to Reference Deprecated Code

1. **Historical Context**: Understanding how a feature evolved
2. **Bug Investigation**: Checking if an issue existed in earlier versions
3. **Code Archaeology**: Researching past implementation decisions
4. **Audit Trail**: Tracking what was changed and why

### When to Clean Up

Consider deleting deprecated files when:
- Files have been in `deprecated/` for 6+ months
- All references have been removed from active codebase
- No ongoing investigations require historical context
- Team has confirmed files are no longer needed

### Before Deletion Checklist

- [ ] Search codebase for any remaining references
- [ ] Check if any team members need the files
- [ ] Archive to external backup if uncertain
- [ ] Document deletion in cleanup log

---

## 📝 Deprecation Log

### 2025-11-28: Initial Cleanup
**Moved from root and src/**:
- 7 debug scripts
- 15 documentation files

**Reason**: Repository cleanup before comprehensive audit. Files were cluttering the repository and have been superseded by newer implementations or documentation.

**See**: `CLEANUP_SUMMARY.md` for full details

---

## ⚠️ Important Notes

- **DO NOT** re-introduce deprecated code to active codebase without review
- **DO** check `deprecated/` before creating similar functionality (avoid reinventing the wheel)
- **DO** update this README when adding new deprecated files
- **DO** add deprecation date and reason when moving files here

---

**Maintained By**: Development Team
**Last Updated**: 2025-11-28
