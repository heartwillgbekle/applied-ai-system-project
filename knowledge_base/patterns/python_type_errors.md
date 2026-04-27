# Pattern: Python Type Errors in Game Logic

## Category
Python / Types / Silent Bugs

## Why Type Errors Are Dangerous in Games
Python will not always raise an exception when you compare incompatible types.
In Python 2, comparing an int to a string uses an arbitrary but stable
ordering. In Python 3, most comparisons between incompatible types raise
`TypeError` — but string-to-string comparisons always succeed, meaning a
number accidentally stored as a string will compare lexicographically without
any warning.

## Common Type Bug: int vs str in Comparisons
```python
# DANGEROUS: if secret is ever stored as a string
guess = 50       # int
secret = "9"     # str — stored wrongly somewhere upstream

# Python 3 raises TypeError here, but only at runtime
if guess > secret:
    ...
```

Lexicographic comparison trap:
- `"50" > "9"` → False (because "5" < "9" alphabetically)
- `50 > 9`     → True  (correct integer comparison)

## How to Detect This
1. Use `type()` or `isinstance()` assertions at comparison points:
   ```python
   assert isinstance(secret, int), f"secret must be int, got {type(secret)}"
   ```
2. Add a unit test that passes a string secret:
   ```python
   def test_secret_is_always_int():
       assert isinstance(st.session_state.secret, int)
   ```
3. Log the type alongside the value when debugging intermittent wrong hints

## How to Prevent This
- Always coerce values to the correct type at assignment, not at comparison:
  ```python
  st.session_state.secret = int(random.randint(low, high))  # explicit
  ```
- Never reassign session state variables with transformed types mid-game
- Add type hints to functions that handle game values:
  ```python
  def check_guess(guess: int, secret: int) -> str: ...
  ```

## Symptoms in a Number-Guessing Game
- Hints correct on odd attempts, wrong on even attempts (or vice versa)
- Hint direction inverts for certain number pairs (e.g., 50 vs 9)
- Game becomes impossible to win on some runs but not others

## Related Patterns
- Type comparison bug (type_comparison.md in bugs/)
- Hint reversal bug (hint_reversal.md in bugs/)
