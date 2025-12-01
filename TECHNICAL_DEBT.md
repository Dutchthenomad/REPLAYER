# Technical Debt

This document tracks known technical debt and migration priorities for the REPLAYER project.

---

## 🔴 HIGH PRIORITY: ML Module Migration

**Status**: Pending Migration
**Created**: 2025-11-28
**Impact**: External dependency on rugs-rl-bot project

### Current State

The `src/ml/` directory currently uses **symlinks** to the rugs-rl-bot project:

```
src/ml/
├── data_processor.py -> /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/data_processor.py
├── feature_extractor.py -> /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/feature_extractor.py
├── __init__.py -> /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/__init__.py
├── model.py -> /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/model.py
└── predictor.py -> /home/nomad/Desktop/rugs-rl-bot/archive/rugs_bot/sidebet/predictor.py
```

### Issues

1. **External Dependency**: REPLAYER cannot run independently without rugs-rl-bot project
2. **Archive Path**: Symlinks point to `/archive/` subdirectory (not actively maintained)
3. **Deployment Complexity**: Symlinks don't work well in containerized/production environments
4. **Version Control**: Changes in rugs-rl-bot can break REPLAYER without notice
5. **Venv Dependency**: REPLAYER currently uses rugs-rl-bot's virtual environment (see `run.sh`)

### Migration Plan

**Option 1: Copy ML modules to REPLAYER (Recommended)**
- Copy the 5 ML files directly into `src/ml/`
- Remove symlinks
- Create independent REPLAYER venv with ML dependencies
- Update `run.sh` to use REPLAYER's venv
- Maintain independent version of sidebet predictor

**Option 2: Create shared Python package**
- Extract ML modules into separate pip-installable package
- Install package in both rugs-rl-bot and REPLAYER venvs
- Maintain single source of truth
- More complex but better for code reuse

### Action Items

- [ ] Audit ML module dependencies (which packages are needed?)
- [ ] Copy ML files to REPLAYER `src/ml/`
- [ ] Remove symlinks
- [ ] Create `requirements.txt` for REPLAYER-specific dependencies
- [ ] Create REPLAYER virtual environment
- [ ] Update `run.sh` to use REPLAYER venv
- [ ] Test ML functionality (sidebet predictor)
- [ ] Update documentation (CLAUDE.md, AGENTS.md)

### Estimated Effort

- **Time**: 2-3 hours
- **Risk**: Low (files are stable, well-tested)
- **Testing**: Run existing ML tests to verify migration

---

## 🟡 MEDIUM PRIORITY: Virtual Environment Independence

**Status**: Pending
**Related to**: ML Module Migration

### Current State

REPLAYER currently uses the rugs-rl-bot virtual environment via `run.sh`:

```bash
# run.sh (current)
VENV_PATH="/home/nomad/Desktop/rugs-rl-bot/.venv"
if [ -d "$VENV_PATH" ]; then
    "$VENV_PATH/bin/python3" src/main.py
else
    python3 src/main.py  # Fallback to system Python
fi
```

### Issues

1. **Tight Coupling**: REPLAYER depends on external project's environment
2. **Version Conflicts**: rugs-rl-bot dependencies may conflict with REPLAYER needs
3. **Deployment**: Cannot deploy REPLAYER independently

### Migration Plan

1. Create REPLAYER-specific `requirements.txt`
2. Create REPLAYER `.venv/` (add to `.gitignore`)
3. Update `run.sh` to use local venv
4. Document venv setup in README.md

---

## 📝 Future Considerations

### Code Duplication
After ML migration, some code may be duplicated between rugs-rl-bot and REPLAYER. Consider:
- Creating shared library package
- Identifying truly shared vs project-specific code
- Maintaining common game mechanics in single source

### Browser Automation
Both projects use Playwright browser automation. Consider:
- Extracting browser automation to shared package
- Standardizing CDP connection patterns
- Sharing XPath selectors and automation utilities

---

**Last Updated**: 2025-11-28
**Maintained By**: Development Team
