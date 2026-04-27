# Bug Pattern: String vs Integer Type Comparison

## Category
Type Error / Silent Bug

## Symptoms
- Hints are wrong on some turns but correct on others (intermittent)
- The game behaves differently on even-numbered vs odd-numbered attempts
- A guess of 50 against a secret of 9 says "Too Low" instead of "Too High"
- No Python error is raised — the bug is completely silent

## Root Cause
Python allows comparison between an integer and a string without raising an
exception in Python 2, or raises a TypeError in Python 3. In some versions of
the broken game, the secret number is silently cast to a string on every
even-numbered attempt. This causes lexicographic (alphabetical) comparison:
`50 > "9"` evaluates to `False` because "5" < "9" alphabetically, so a guess
of 50 against a secret of "9" incorrectly returns "Too Low".

## Example from Game Glitch Investigator
```python
# BROKEN: secret silently becomes a string on even attempts
if st.session_state.attempts % 2 == 0:
    st.session_state.secret = str(st.session_state.secret)

# This means check_guess receives: guess=50 (int), secret="9" (str)
# Python 3: raises TypeError
# Python 2: lexicographic comparison produces wrong result

# FIXED: always keep secret as int; compare int to int
st.session_state.secret = random.randint(low, high)  # always int
```

## Fix Approach
Ensure both values passed to the comparison function are always integers.
Add `int()` coercion defensively, or validate types at assignment time.
A unit test like `assert type(st.session_state.secret) == int` after each
state update can catch this early.

## Related Bugs
- hint_reversal (type bugs can mimic reversed hints)
