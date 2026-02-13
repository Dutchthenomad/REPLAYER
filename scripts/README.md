# Scripts Directory

Utility scripts for REPLAYER development and maintenance.

## Repository Management

### check_repo_status.py

**Purpose**: Check git status across REPLAYER and related repositories.

**Usage**:
```bash
# From project root
./check_repos.sh

# Direct execution
python3 scripts/check_repo_status.py
```

**What it checks**:
- ✓ Uncommitted changes (modified, untracked files)
- ✓ Unpushed commits (local ahead of remote)
- ✓ Unpulled commits (local behind remote)
- ✓ Branch tracking status

**Repositories checked**:
1. REPLAYER (current repo)
2. rugs-rl-bot (if exists at `~/Desktop/rugs-rl-bot/`)
3. CV-BOILER-PLATE-FORK (if exists at `~/Desktop/CV-BOILER-PLATE-FORK/`)

**Exit codes**:
- `0` - All repositories up to date
- `1` - One or more repositories need attention

**Example output**:
```
================================================================================
  Multi-Repository Status Checker
================================================================================

================================================================================
Repository: REPLAYER
Path: /home/runner/work/REPLAYER/REPLAYER
Branch: main
Remote: origin/main

Status:
  ⚠ 2 unpushed commit(s)
  ⚠ Uncommitted changes present

================================================================================
Summary
================================================================================
Repositories checked: 3

Repositories needing attention:
  • REPLAYER
================================================================================
```

---

## Chrome/Browser Tools

### setup_chrome_profile.py

Sets up Chrome profile with Phantom wallet for browser automation.

### test_cdp_connection.py

Tests Chrome DevTools Protocol connection.

---

## Analysis Tools

### analyze_raw_capture.py

Analyzes raw WebSocket capture files from the debug capture tool.

**Usage**:
```bash
python3 scripts/analyze_raw_capture.py <capture_file.jsonl>
```

---

## Testing

### test_check_repo_status.py

Basic smoke tests for the repository status checker.

**Usage**:
```bash
python3 scripts/test_check_repo_status.py
```
