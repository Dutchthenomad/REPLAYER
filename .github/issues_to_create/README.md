# GitHub Issues to Create

This directory contains polished issue templates ready to be published to the REPLAYER GitHub repository.

## Quick Publish (All Issues)

```bash
# Install gh CLI if not already installed
# Ubuntu/Debian: sudo apt install gh
# macOS: brew install gh

# Authenticate
gh auth login

# Publish all issues
./publish-issues.sh
```

## Manual Publish (Individual Issues)

To create a single issue:

```bash
gh issue create \
  --title "$(grep '^title:' priority-02-server-state-authority.md | cut -d'"' -f2)" \
  --body-file <(sed '1,/^---$/d; /^---$/d' priority-02-server-state-authority.md) \
  --label "$(grep '^labels:' priority-02-server-state-authority.md | cut -d: -f2 | tr -d ' ')"
```

## Issue Priority Order

| File | Priority | Title | Estimated Effort |
|------|----------|-------|------------------|
| `priority-02-server-state-authority.md` | P2 (High) | Server State Authority Migration | 2-3 hours |
| `priority-03-live-game-recording.md` | P3 (High) | Live Game Recording Session | 2-3 hours |
| `priority-04-rag-knowledge-base.md` | P4 (High) | RAG Knowledge Base | 6-8 hours |
| `priority-05-rl-model-integration.md` | P5 (High) | RL Model Integration | 8-10 hours |
| `priority-06-browser-live-trading.md` | P6 (High) | Browser Live Trading | 10-12 hours |
| `priority-07-portfolio-dashboard.md` | P7 (Medium) | Portfolio Dashboard | 8-10 hours |
| `priority-08-player-profile-ui.md` | P8 (Medium) | Player Profile UI | 6-8 hours |

## Dependencies

```
P1 (✅ Complete) → P2 → P3 → P4
                     ↓     ↓
                     P8    P5 → P6 → P7
```

## Notes

- All issues are structured with:
  - Clear goals and context
  - Actionable task checklists
  - Success criteria
  - Dependencies
  - Related files
  - Effort estimates

- Labels:
  - `priority-high`: P2-P6 (critical path)
  - `priority-medium`: P7-P8 (parallel work)
  - `enhancement`: New features
  - `phase-12`: Current phase
  - `ml`, `rl`, `ui`, etc.: Domain-specific

## Related Documents

- `ROADMAP.md` - Full development roadmap
- `docs/SESSION_HANDOFF.md` - Original priority stack
- `CLAUDE.md` - Production documentation
