# Feature/Fix Planning Template

## Zero-Context Principle
This plan must be executable by someone with NO prior session context.

---

## Feature: [Name]

### Goal
[One sentence describing the outcome]

### Architecture Impact
- [ ] New module needed?
- [ ] Existing pattern to follow (check architect.yaml)?
- [ ] EventBus events needed?
- [ ] UI changes required?
- [ ] Thread safety considerations?

### Files to Modify
| File | Change Type | Description |
|------|-------------|-------------|
| src/core/... | New/Modify | ... |
| tests/test_core/... | New | Test for above |

### Tasks (TDD Order)

#### Task 1: [Description]

**Test First**:
```python
# tests/test_{module}/test_{feature}.py
def test_{function}_{scenario}():
    # Arrange
    # Act
    # Assert
```

**Implementation**:
```python
# src/{module}/{file}.py
def {function}():
    pass
```

**Verify**:
```bash
cd src && python3 -m pytest tests/test_{module}/test_{feature}.py -v
```

#### Task 2: [Description]
...

### Verification Criteria
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] Manual testing of feature
- [ ] Thread safety verified (if applicable)
- [ ] UI updates properly (if applicable)

### Risks
- [ ] Risk 1: [Description] -> Mitigation: [...]
- [ ] Risk 2: ...
