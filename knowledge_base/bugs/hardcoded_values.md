# Bug Pattern: Hardcoded Values That Should Be Dynamic

## Category
Configuration / Hardcoding

## Symptoms
- The range banner always shows "1 to 100" regardless of selected difficulty
- New Game button generates a secret from 1–100 even in Hard mode
- Changing difficulty has no visible effect on the displayed range
- A player in Easy mode can enter 500 and the game accepts it

## Root Cause
Magic numbers are embedded directly in multiple places in the code instead of
being derived from a single source of truth. When the difficulty changes, some
places update correctly (via `get_range_for_difficulty`) but others still use
the hardcoded fallback.

## Example from Game Glitch Investigator
```python
# BROKEN: hardcoded in the info banner
st.info("Guess a number between 1 and 100.")

# BROKEN: hardcoded in the New Game reset
st.session_state.secret = random.randint(1, 100)

# FIXED: derive from the difficulty helper every time
low, high = get_range_for_difficulty(difficulty)
st.info(f"Guess a number between {low} and {high}.")
st.session_state.secret = random.randint(low, high)
```

## Fix Approach
Call `get_range_for_difficulty(difficulty)` once near the top of the script
and assign the result to `low, high`. Reference those variables everywhere
a range bound is needed. Search the file for literal `100`, `20`, `500` to
find all remaining hardcoded occurrences.

## Related Bugs
- difficulty_ranges (ranges themselves may also be wrong)
- range_validation (validation must also use the dynamic bounds)
