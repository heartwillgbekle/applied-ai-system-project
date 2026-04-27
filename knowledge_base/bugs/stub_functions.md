# Bug Pattern: Stub Functions Raising NotImplementedError

## Category
Incomplete Implementation

## Symptoms
- All pytest tests fail immediately with `NotImplementedError`
- The app crashes as soon as any game logic function is called
- Functions exist and are importable, but calling them raises an exception
- The skeleton/starter code was never filled in

## Root Cause
The project was scaffolded with placeholder functions that raise
`NotImplementedError` as a signal to the developer to implement them.
If these stubs are never replaced with real logic, every code path that
calls them will crash.

## Example from Game Glitch Investigator
```python
# BROKEN: stub that crashes on any call
def check_guess(guess, secret):
    raise NotImplementedError("TODO: implement check_guess")

# FIXED: real implementation
def check_guess(guess, secret):
    if guess == secret:
        return "Win"
    if guess > secret:
        return "Too High"
    return "Too Low"
```

## Fix Approach
Search the codebase for `NotImplementedError` and `raise NotImplemented`.
Replace each stub with a correct implementation. Run `pytest` after each
function is implemented to confirm tests pass incrementally rather than
waiting to fix everything at once.

## Related Bugs
- hint_reversal (check_guess must be implemented correctly, not just non-raising)
- score_logic (update_score is another common stub target)
