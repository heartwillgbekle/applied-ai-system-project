# Bug Pattern: Missing Range Validation

## Category
Input Validation

## Symptoms
- A player can type 999 in Easy mode (range 1–20) and the guess is accepted
- Out-of-range guesses consume an attempt without a useful error message
- The attempt counter goes up even when the input is clearly invalid
- Players can accidentally "cheat" by entering numbers outside the valid range

## Root Cause
The submit handler checks whether the input is a valid integer (via `parse_guess`)
but does not check whether the integer falls within `[low, high]`. Without a
range guard, any integer is accepted as a valid guess.

## Example from Game Glitch Investigator
```python
# BROKEN: only checks if it's a number, not if it's in range
ok, guess_int, err = parse_guess(raw_guess)
if not ok:
    st.error(err)
else:
    st.session_state.attempts += 1   # attempt consumed even for 999 in Easy

# FIXED: add range check before accepting the guess
ok, guess_int, err = parse_guess(raw_guess)
if not ok:
    st.error(err)
elif guess_int < low or guess_int > high:
    st.error(f"Please enter a number between {low} and {high}.")
else:
    st.session_state.attempts += 1   # only incremented for valid in-range guess
```

## Fix Approach
After parsing the integer, add an explicit bounds check using the dynamic
`low` and `high` values from `get_range_for_difficulty`. Do not increment
the attempt counter until the guess passes both the parse check and the
range check.

## Related Bugs
- hardcoded_values (range bounds must be dynamic, not hardcoded)
