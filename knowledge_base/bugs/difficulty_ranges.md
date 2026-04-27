# Bug Pattern: Swapped Difficulty Ranges

## Category
Logic Error / Configuration

## Symptoms
- Hard mode feels easier than Easy mode
- The secret number in Hard mode is sometimes smaller than in Easy mode
- "Easy" has a wider range (1–500) than "Hard" (1–20)
- Players report the difficulty labels feel backwards

## Root Cause
The range values in `get_range_for_difficulty` are assigned to the wrong
difficulty levels. Hard mode should have the widest range (hardest to guess)
and Easy mode the narrowest. When the mappings are swapped, difficulty labels
are misleading.

## Example from Game Glitch Investigator
```python
# BROKEN: Hard is smallest range, Easy is largest
def get_range_for_difficulty(difficulty):
    if difficulty == "Easy":
        return 1, 500   # too hard for Easy
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 20    # too easy for Hard

# FIXED:
def get_range_for_difficulty(difficulty):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 500
```

## Fix Approach
Decide on an intended difficulty scale (e.g., Easy=1–20, Normal=1–100,
Hard=1–500) and match the range values to the difficulty names. Add a
unit test that asserts `get_range_for_difficulty("Hard")[1] > get_range_for_difficulty("Easy")[1]`.

## Related Bugs
- hardcoded_values (if ranges are also hardcoded elsewhere they won't update)
