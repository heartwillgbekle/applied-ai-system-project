# Bug Pattern: Streamlit State Reset on Rerun

## Category
Session State

## Symptoms
- The secret number changes every time the player clicks Submit
- Score resets to zero on each button click
- Attempt counter resets unexpectedly
- Any variable that should persist across interactions keeps losing its value

## Root Cause
Streamlit re-executes the entire Python script from top to bottom on every user
interaction (button click, text input, selectbox change, etc.). Any variable
assigned with a plain Python statement (e.g. `secret = random.randint(1, 100)`)
is re-evaluated on every rerun, producing a fresh value each time.

## Example from Game Glitch Investigator
```python
# BROKEN: runs every rerun — secret changes on every click
secret = random.randint(low, high)

# FIXED: only runs once; subsequent reruns skip the assignment
if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)
```

## Fix Approach
Wrap one-time initialization in a `if "key" not in st.session_state:` guard.
Store all game state (secret, attempts, score, status, history) in
`st.session_state` so values survive reruns.

## Related Bugs
- off_by_one (attempts counter also resets if not in session state)
- difficulty_reset (difficulty change must explicitly reset session state)
