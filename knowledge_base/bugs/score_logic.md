# Bug Pattern: Incorrect Score Update Logic

## Category
Logic Error

## Symptoms
- Score increases on some wrong guesses and decreases on others unpredictably
- Players are rewarded for wrong answers on even-numbered attempts
- The scoring system feels inconsistent or random
- Final score does not reflect skill level

## Root Cause
The `update_score` function contains a conditional that adds points on
even-numbered wrong guesses instead of always subtracting. This is usually
caused by a stray `if attempt % 2 == 0: return current_score + 5` branch
that was introduced as a bug.

## Example from Game Glitch Investigator
```python
# BROKEN: adds +5 on even-numbered wrong attempts
def update_score(current_score, outcome, attempt_number):
    if outcome == "Win":
        return current_score + max(10, 100 - 10 * (attempt_number - 1))
    if attempt_number % 2 == 0:
        return current_score + 5   # wrong — should always subtract
    return current_score - 5

# FIXED: always subtract on wrong guesses
def update_score(current_score, outcome, attempt_number):
    if outcome == "Win":
        points = 100 - 10 * (attempt_number - 1)
        return current_score + max(10, points)
    return current_score - 5
```

## Fix Approach
Remove any attempt-number-based branching for wrong guesses. Wrong is wrong —
the penalty should be flat. Keep the attempt number relevant only to the
winning bonus calculation.

## Related Bugs
- off_by_one (attempt_number must be accurate for win bonus to be fair)
