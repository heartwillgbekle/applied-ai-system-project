# Bug Pattern: Off-By-One Error in Attempt Counter

## Category
Logic Error / Initialization

## Symptoms
- The "Attempts left" counter starts at one less than it should
- On the very first guess, the game says "7 attempts left" instead of 8
- The player appears to have already used an attempt before playing
- The win bonus is slightly wrong because attempt_number is one too high from the start

## Root Cause
The `attempts` counter in session state is initialized to `1` instead of `0`.
Since Streamlit increments the counter on each submission, starting at 1
means the first real guess is recorded as attempt #2.

## Example from Game Glitch Investigator
```python
# BROKEN: starts at 1 — player "loses" an attempt before the game begins
if "attempts" not in st.session_state:
    st.session_state.attempts = 1

# FIXED: starts at 0 — first submission increments to 1
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
```

## Fix Approach
Initialize all counters to their natural zero state. Check every session_state
initialization block for numeric variables. Off-by-one errors in counters
compound across the game: they affect attempts-left display, win bonus
calculation, and game-over detection.

## Related Bugs
- state_reset (counter must be in session state or it resets anyway)
- score_logic (attempt_number feeds into score calculation)
