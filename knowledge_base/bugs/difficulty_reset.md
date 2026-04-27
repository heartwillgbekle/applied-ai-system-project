# Bug Pattern: No Game Reset When Difficulty Changes

## Category
State Management

## Symptoms
- Changing difficulty mid-game keeps the old secret number from the previous range
- A player switches from Easy (1–20) to Hard (1–500) but the secret is still 7
- The attempt counter and score carry over into the new difficulty
- History from the previous game still shows in the new game

## Root Cause
The app detects the new difficulty from the sidebar selectbox but never
checks whether it has *changed* since last rerun. Without a change-detection
guard, the existing session state (secret, attempts, score, history) is
unchanged even though the difficulty context has shifted entirely.

## Example from Game Glitch Investigator
```python
# BROKEN: difficulty updates but game state is stale
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"])
low, high = get_range_for_difficulty(difficulty)
# ... game continues with old secret from previous difficulty

# FIXED: detect change and reset
if "difficulty" not in st.session_state:
    st.session_state.difficulty = difficulty

if st.session_state.difficulty != difficulty:
    st.session_state.difficulty = difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.rerun()
```

## Fix Approach
Store the last-seen difficulty in session state. On each rerun, compare the
current selectbox value to the stored value. If they differ, reset all game
state and call `st.rerun()` to apply the changes immediately.

## Related Bugs
- state_reset (all reset fields must be stored in session state)
- hardcoded_values (new secret must use dynamic low/high, not hardcoded range)
