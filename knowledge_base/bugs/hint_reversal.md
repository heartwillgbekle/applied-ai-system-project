# Bug Pattern: Reversed Hint Logic

## Category
Logic Error

## Symptoms
- The game says "Go HIGHER!" when the player's guess is already above the secret
- The game says "Go LOWER!" when the player's guess is below the secret
- Hints consistently point the player in the wrong direction
- Players can never win by following the hints

## Root Cause
The comparison branches in the hint function are swapped. When `guess > secret`
the player needs to go *lower*, but the code returns "Go HIGHER!" instead.
This is a classic copy-paste or logic inversion mistake.

## Example from Game Glitch Investigator
```python
# BROKEN: branches are swapped
def check_guess(guess, secret):
    if guess == secret:
        return "Win"
    if guess > secret:
        return "Too Low"   # wrong — should be "Too High"
    return "Too High"      # wrong — should be "Too Low"

# FIXED:
def check_guess(guess, secret):
    if guess == secret:
        return "Win"
    if guess > secret:
        return "Too High"
    return "Too Low"
```

## Fix Approach
Read the function aloud: "If my guess is greater than the secret, I need to go
*lower*." Make sure the return value reflects that. Write a unit test:
`assert check_guess(60, 50) == "Too High"`.

## Related Bugs
- type_comparison (wrong type can make the comparison produce the wrong branch)
