---
name: regression-testing
description: Test protocol for changes to simulation_engine/. Run pytest tests/ -v after every change under that package. For pure refactoring (no rule change), additionally run a seeded benchmark before and after and verify the outputs are bit-identical. Invoke whenever any file under simulation_engine/ is modified.
---

# Regression Testing Instructions

## When Any Change Touches `simulation_engine/`

After every change inside `simulation_engine/` (new feature, bug fix, or refactoring), run the full test suite:

```bash
pytest tests/ -v
```

Do not consider the task complete until all tests pass. If a test fails, inspect the failure, fix the issue, and re-run until the suite is green.

## Refactoring Changes - Benchmark Regression Gate

When the change is purely a refactoring (no new game rules, no intentional behavior change), you must additionally run a deterministic benchmark **before** and **after** the change and verify the statistics are identical.

### Benchmark procedure

1. **Before making any code changes**, run the benchmark and save the results:

```python
python -c "
from simulation_engine import run_scenario
records = run_scenario(player_count = 7, n_games = 200, base_seed = 42)
wins = sum(1 for r in records if r.outcome == 'win')
print(f'Win rate: {wins}/{len(records)} ({wins/len(records):.4f})')
print(f'Avg rounds: {sum(r.rounds_played for r in records)/len(records):.2f}')
print(f'Avg boat parts: {sum(r.boat_parts_built for r in records)/len(records):.2f}')
scores = {}
for r in records:
    for char, sc in r.final_scores.items():
        scores.setdefault(char, []).append(sc)
for char in sorted(scores, key = lambda c: c.name):
    vals = scores[char]
    print(f'  {char.name}: avg_score={sum(vals)/len(vals):.2f}')
"
```

2. **Apply the refactoring.**

3. **Run the same benchmark again** after the refactoring and compare:
   - Win rate must be identical.
   - Average rounds played must be identical.
   - Average boat parts built must be identical.
   - Per-character average scores must be identical.

   Because `base_seed` is fixed, all values must match exactly (not approximately). Any difference means the refactoring changed game behavior - treat this as a bug, investigate, and fix before continuing.

4. **Run the full test suite** (`pytest tests/ -v`) and ensure all tests pass.

### What counts as refactoring

A change is refactoring when the intent is to reorganize, rename, simplify, or restructure code without altering game rules or outcomes. Examples:
- Renaming variables, functions, or classes
- Extracting helper functions
- Reorganizing modules or moving code between files
- Simplifying logic without changing behavior
- Adding type annotations

### When tests need updating

- **New features or rule changes**: tests may need to be added or updated to reflect new behavior. The benchmark numbers are expected to change - no before/after comparison is needed.
- **Refactoring**: business logic tests must remain unchanged and pass as-is. If a refactoring causes a test to fail, the refactoring introduced a bug - fix the refactoring, not the test.