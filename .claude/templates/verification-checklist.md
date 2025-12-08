# Verification Before Completion

## The 5-Step Gate

1. **Identify** proof command:
   ```bash
   cd src && python3 -m pytest tests/ -v --tb=short
   ```

2. **Execute** FRESH (not "it passed before")

3. **Read** complete output:
   - [ ] Exit code is 0
   - [ ] 0 failures, 0 errors
   - [ ] No warnings about skipped tests

4. **Confirm** original issue is fixed:
   - [ ] Reproduce original bug -> now works
   - [ ] Feature works as specified
   - [ ] No regressions introduced

5. **State** result with evidence:
   - [ ] Screenshot or paste test output
   - [ ] Reference specific test names

## Red Flags (STOP if any apply)
- [ ] Using words: "should," "probably," "seems to"
- [ ] Relying on partial evidence
- [ ] Feeling tired and wanting to be done
- [ ] Tests pass but original symptom not verified
