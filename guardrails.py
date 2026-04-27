import logging
import re

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 500

# Patterns that must never appear in user input or AI output
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bos\.system\b"),
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"drop\s+table", re.IGNORECASE),
    re.compile(r"delete\s+from", re.IGNORECASE),
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+prior", re.IGNORECASE),
]

# At least one of these words must be present for the input to be on-topic
_TOPIC_KEYWORDS: frozenset[str] = frozenset(
    [
        "bug", "glitch", "error", "guess", "hint", "score", "secret",
        "attempt", "session", "state", "streamlit", "higher", "lower",
        "range", "difficulty", "number", "game", "win", "lose", "random",
        "reset", "function", "code", "python", "type", "int", "string",
        "comparison", "off by one", "hardcoded", "variable", "fix", "wrong",
        "broken", "not working", "logic", "test", "pytest", "rerun",
        "session_state", "counter", "increment", "initialize",
    ]
)


def validate_input(text: str) -> tuple[bool, str]:
    """
    Check user input before it reaches the AI.

    Returns (is_valid, reason). reason is empty when valid.
    """
    if not text or not text.strip():
        return False, "Please describe a bug or symptom to investigate."

    stripped = text.strip()

    if len(stripped) > MAX_INPUT_LENGTH:
        return (
            False,
            f"Description too long ({len(stripped)} chars). "
            f"Please keep it under {MAX_INPUT_LENGTH} characters.",
        )

    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(stripped):
            logger.warning("Input blocked — matched disallowed pattern: %s", pattern.pattern)
            return False, "Input contains content that cannot be processed."

    lower = stripped.lower()
    if not any(kw in lower for kw in _TOPIC_KEYWORDS):
        return (
            False,
            "Please describe a bug related to the game "
            "(e.g. hints, score, secret number, state, range, difficulty).",
        )

    return True, ""


def validate_output(response: str) -> tuple[bool, str]:
    """
    Sanity-check AI output before showing it to the user.

    Returns (is_valid, filtered_text_or_error_reason).
    """
    if not response or len(response.strip()) < 10:
        logger.warning("AI output rejected — response too short or empty.")
        return False, "The AI returned an empty response. Please try again."

    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(response):
            logger.warning(
                "AI output blocked — contained disallowed pattern: %s",
                pattern.pattern,
            )
            return False, "AI response was filtered for safety reasons."

    return True, response.strip()
