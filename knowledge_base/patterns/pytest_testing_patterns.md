# Pattern: Pytest Testing Strategies for Game Logic

## Category
Testing / Pytest

## Why Tests Matter for AI-Adjacent Code
Game logic functions are pure — they take inputs and return outputs with no
side effects. That makes them ideal for unit testing. Writing tests before
or alongside fixing bugs ensures you know when a fix is actually complete
and prevents regressions when you change other parts of the code.

## Basic Test Structure
```python
from logic_utils import check_guess, update_score, parse_guess

def test_winning_guess():
    assert check_guess(50, 50) == "Win"

def test_guess_too_high():
    assert check_guess(60, 50) == "Too High"

def test_guess_too_low():
    assert check_guess(40, 50) == "Too Low"
```

## Testing Edge Cases
Always test boundary conditions and type edge cases:
```python
def test_guess_at_lower_bound():
    assert check_guess(1, 1) == "Win"

def test_guess_at_upper_bound():
    assert check_guess(100, 100) == "Win"

def test_parse_guess_with_decimal_string():
    ok, val, err = parse_guess("42.7")
    assert ok and val == 42

def test_parse_guess_with_non_numeric():
    ok, val, err = parse_guess("abc")
    assert not ok
    assert err is not None
```

## Testing Score Logic
```python
def test_score_decreases_on_wrong_guess():
    score = update_score(100, "Too High", attempt_number=2)
    assert score == 95   # always -5 for wrong

def test_score_increases_on_win_first_attempt():
    score = update_score(0, "Win", attempt_number=1)
    assert score == 100  # 100 - 10*(1-1) = 100

def test_score_never_goes_negative_on_win():
    score = update_score(0, "Win", attempt_number=15)
    assert score >= 10   # minimum 10 points for a win
```

## Running Tests
```bash
pytest                    # run all tests
pytest -v                 # verbose output
pytest tests/test_game_logic.py   # specific file
pytest -k "score"         # run tests whose name contains "score"
```

## Interpreting Failures
- `AssertionError` with no message: add `assert result == expected, f"got {result}"` for context
- `NotImplementedError`: the function stub was never implemented — write the body
- `KeyError` on session_state: the key wasn't initialised — add a session_state guard

## Related Patterns
- Stub functions (stub_functions.md in bugs/)
- Off-by-one (off_by_one.md in bugs/)
