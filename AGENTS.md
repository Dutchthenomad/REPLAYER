# Repository Guidelines

**Last Updated**: 2025-12-05
**Project Status**: Phase 9 Complete, Phase 10 Planning
**Active Branch**: `main`
**Tests**: 275 passing

---

## Superpowers Workflow (REQUIRED)

This project uses **Superpowers** as the primary development methodology.

### Iron Laws
1. **TDD Required**: Every new feature/fix must have failing test first
2. **Verification Required**: Fresh test run before claiming complete
3. **Planning Required**: Use `.claude/templates/planning-template.md` for features
4. **Code Review**: Use `.claude/templates/code-review-checklist.md` before PR

### Quick Commands
| Command | Use For |
|---------|---------|
| `/tdd` | All new features, bug fixes, refactoring |
| `/debug` | Any technical failures (4-phase analysis) |
| `/verify` | Before claiming task complete |
| `/run-tests` | Run project test suite |

### Test Command
```bash
cd src && python3 -m pytest tests/ -v --tb=short
```

---

## Project Structure

```
src/
├── core/       # State, replay, trade management
├── bot/        # Controller, strategies, browser executor
├── ui/         # Main window, panels, widgets
├── services/   # EventBus, logger
├── models/     # GameTick, Position, SideBet
├── sources/    # WebSocket feed
├── ml/         # ML symlinks to rugs-rl-bot
└── tests/      # Test suite
```

---

## Commands

```bash
./run.sh                                    # Launch app
cd src && python3 -m pytest tests/ -v       # Run tests
cd src && black . && flake8                 # Format + lint
```

---

## Coding Standards

- **Format**: Black (88 cols, double quotes)
- **Naming**: snake_case functions, PascalCase classes
- **Money**: Always `Decimal`, never `float`
- **Threading**: UI updates via `TkDispatcher.submit()`

---

## Architecture References

- `CLAUDE.md` - Full project documentation
- `architect.yaml` - Design patterns
- `RULES.yaml` - Code standards
- `.claude/templates/` - Development checklists
