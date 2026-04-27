import json
import logging
import os
import time

import anthropic

from guardrails import validate_input, validate_output
from retriever import BugPatternRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Confidence below this threshold causes the answer to be flagged for review
CONFIDENCE_THRESHOLD = 60
MODEL = "claude-haiku-4-5-20251001"

_retriever = BugPatternRetriever()


def _call_claude(messages: list[dict], max_tokens: int = 512) -> str:
    """Single Claude API call. Returns the text of the first content block."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.content[0].text


def _parse_confidence(raw: str) -> tuple[int, str]:
    """
    Extract confidence and caveat from the self-critique JSON response.
    Falls back to (50, 'Confidence unavailable') on any parse failure.
    """
    text = raw.strip()
    # Strip optional markdown code fences
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) >= 2 else text

    try:
        data = json.loads(text)
        confidence = max(0, min(100, int(data.get("confidence", 50))))
        caveat = str(data.get("caveat", ""))
        return confidence, caveat
    except Exception as exc:
        logger.warning("Self-critique parse error: %s | raw=%r", exc, raw[:120])
        return 50, "Confidence score could not be determined."


def diagnose(symptom: str) -> dict:
    """
    Agentic loop: validate → retrieve → diagnose → self-critique.

    Returns a dict:
        diagnosis  : str | None   — the AI's answer
        confidence : int          — 0-100 self-rated confidence
        caveat     : str          — disclaimer when confidence < threshold
        sources    : list[str]    — knowledge-base filenames used
        flagged    : bool         — True when confidence < CONFIDENCE_THRESHOLD
        error      : str | None   — set only when the pipeline could not complete
    """
    t0 = time.monotonic()

    # ── Step 1: Guardrails — validate input ──────────────────────────────────
    valid, reason = validate_input(symptom)
    if not valid:
        logger.warning("Input rejected: %s", reason)
        return {
            "diagnosis": None,
            "confidence": 0,
            "caveat": "",
            "sources": [],
            "flagged": False,
            "error": reason,
        }

    logger.info("Diagnosing: %s", symptom[:80])

    # ── Step 2: Retrieve relevant bug patterns ────────────────────────────────
    hits = _retriever.retrieve(symptom, top_k=3)
    context = (
        "\n\n---\n\n".join(h["content"] for h in hits)
        if hits
        else "No relevant patterns found in the knowledge base."
    )
    sources = [h["filename"] for h in hits]

    # ── Step 3: Diagnose with Claude ──────────────────────────────────────────
    diagnosis_prompt = (
        "You are a Game Glitch Investigator — an expert at diagnosing bugs "
        "in Streamlit number-guessing games.\n\n"
        f'A player has reported this symptom:\n"{symptom}"\n\n'
        "Here are the most relevant bug patterns from your knowledge base:\n"
        "---\n"
        f"{context}\n"
        "---\n\n"
        "Provide a concise structured diagnosis:\n"
        "1. Most likely bug (one sentence)\n"
        "2. Root cause (one to two sentences)\n"
        "3. Suggested fix (specific and actionable)\n\n"
        "Do not repeat the symptom back. Do not add a preamble."
    )

    try:
        raw_diagnosis = _call_claude(
            [{"role": "user", "content": diagnosis_prompt}], max_tokens=512
        )
    except Exception as exc:
        logger.error("Claude API error (diagnosis): %s", exc)
        return {
            "diagnosis": None,
            "confidence": 0,
            "caveat": "",
            "sources": sources,
            "flagged": False,
            "error": "AI service unavailable. Check your ANTHROPIC_API_KEY and try again.",
        }

    # ── Step 4: Guardrails — validate output ─────────────────────────────────
    output_ok, filtered = validate_output(raw_diagnosis)
    if not output_ok:
        return {
            "diagnosis": None,
            "confidence": 0,
            "caveat": "",
            "sources": sources,
            "flagged": True,
            "error": filtered,
        }

    # ── Step 5: Self-critique — ask Claude to rate its confidence ─────────────
    critique_prompt = (
        f'You just produced this diagnosis for the symptom "{symptom}":\n\n'
        f"{filtered}\n\n"
        "Rate your confidence in this diagnosis on a scale of 0 to 100.\n"
        "Respond with ONLY valid JSON — no prose, no code fences:\n"
        '{"confidence": <integer 0-100>, "caveat": "<one sentence if confidence < 70, else empty string>"}'
    )

    try:
        raw_critique = _call_claude(
            [{"role": "user", "content": critique_prompt}], max_tokens=120
        )
        confidence, caveat = _parse_confidence(raw_critique)
    except Exception as exc:
        logger.warning("Claude API error (self-critique): %s", exc)
        confidence, caveat = 50, "Confidence score could not be determined."

    flagged = confidence < CONFIDENCE_THRESHOLD
    if flagged:
        logger.info("Low confidence (%d) — flagging for human review.", confidence)

    elapsed = time.monotonic() - t0
    logger.info(
        "Diagnosis complete in %.2fs | confidence=%d | sources=%s",
        elapsed,
        confidence,
        sources,
    )

    return {
        "diagnosis": filtered,
        "confidence": confidence,
        "caveat": caveat,
        "sources": sources,
        "flagged": flagged,
        "error": None,
    }
