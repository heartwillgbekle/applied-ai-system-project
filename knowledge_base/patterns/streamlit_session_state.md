# Pattern: Streamlit Session State — General Guide

## Category
Streamlit / State Management

## What Session State Is
`st.session_state` is a dictionary-like object that persists across reruns for
a single user session. Streamlit re-executes the full Python script on every
user interaction (button click, text input, selectbox change). Any plain Python
variable gets reset on each rerun. Session state is the only mechanism for
keeping values alive between reruns.

## Initialisation Pattern
Always initialise each key with a guard before reading it:

```python
if "counter" not in st.session_state:
    st.session_state.counter = 0
```

Never read `st.session_state.counter` before the guard — it will raise a
`KeyError` on the first load.

## Resetting State Intentionally
To reset game state when a condition changes (e.g., difficulty switch), assign
new values directly and call `st.rerun()`:

```python
if st.session_state.difficulty != new_difficulty:
    st.session_state.difficulty = new_difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.rerun()
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| No `if key not in` guard | Value resets on every click | Wrap init in guard |
| Initializing to wrong default | Counter off by one from start | Use 0 not 1 for counters |
| Forgetting to reset on mode change | Stale state after difficulty switch | Detect change and reset + rerun |
| Using plain variable instead of session_state | Score resets mid-game | Store in st.session_state |

## Debugging Tips
- Use `st.write(st.session_state)` or an expander to inspect all state keys live
- Add logging at each state mutation to trace unexpected resets
- If a value changes when you didn't expect it to, check whether it has a guard

## Related Patterns
- Difficulty reset (difficulty_reset.md in bugs/)
- State reset (state_reset.md in bugs/)
