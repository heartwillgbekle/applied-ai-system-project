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

CONFIDENCE_THRESHOLD = 60
MODEL = "claude-haiku-4-5-20251001"

_retriever = BugPatternRetriever()

# ── Few-shot examples injected into every diagnosis prompt ───────────────────
# These two examples teach the model the expected output format and specificity
# level. Without them (zero-shot), Claude often adds a preamble sentence and
# uses inconsistent section labels. With them, it reliably produces the exact
# three-point structure with file/function references in the fix step.

_FEW_SHOT_EXAMPLES = """
EXAMPLE 1
Symptom: "The secret number keeps changing every time I click Submit."
1. Most likely bug: The secret is regenerated on every Streamlit rerun instead of being stored in session state.
2. Root cause: Streamlit re-executes the full script on each interaction. Without an `if "secret" not in st.session_state` guard, `random.randint()` runs again on every click and produces a new number.
3. Suggested fix: Replace the bare assignment with `if "secret" not in st.session_state: st.session_state.secret = random.randint(low, high)`. Do the same for all game variables (attempts, score, status, history).

EXAMPLE 2
Symptom: "The hints say go higher when I should go lower, and go lower when I should go higher."
1. Most likely bug: The return values in `check_guess` are swapped — "Too High" and "Too Low" are reversed.
2. Root cause: The comparison branches are inverted: the code returns "Too Low" when `guess > secret` and "Too High" when `guess < secret`, which is the opposite of the correct logic.
3. Suggested fix: In `logic_utils.py`, change `check_guess` so `if guess > secret: return "Too High"` and the else branch returns "Too Low"`. Verify with `assert check_guess(60, 50) == "Too High"`.
""".strip()


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
    Falls back to (50, caveat) on any parse failure.
    """
    text = raw.strip()
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


def _make_step(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def diagnose(symptom: str) -> dict:
    """
    Agentic loop with observable steps:
      1. Input guardrails
      2. Multi-source retrieval (RAG)
      3. Few-shot Claude diagnosis
      4. Output guardrails
      5. Self-critique (confidence 0-100)

    Returns a dict:
        diagnosis  : str | None
        confidence : int
        caveat     : str
        sources    : list[str]
        source_dirs: list[str]   — which corpus each source came from
        flagged    : bool
        error      : str | None
        steps      : list[dict]  — observable intermediate steps for the UI
    """
    t0 = time.monotonic()
    steps: list[dict] = []

    # ── Step 1: Input guardrails ──────────────────────────────────────────────
    valid, reason = validate_input(symptom)
    if not valid:
        logger.warning("Input rejected: %s", reason)
        steps.append(_make_step("Input validation", "blocked", reason))
        return {
            "diagnosis": None, "confidence": 0, "caveat": "",
            "sources": [], "source_dirs": [], "flagged": False,
            "error": reason, "steps": steps,
        }

    steps.append(_make_step("Input validation", "pass", "Input is on-topic and safe."))
    logger.info("Diagnosing: %s", symptom[:80])

    # ── Step 2: Multi-source retrieval ────────────────────────────────────────
    hits = _retriever.retrieve(symptom, top_k=3)
    context = (
        "\n\n---\n\n".join(h["content"] for h in hits)
        if hits
        else "No relevant patterns found in the knowledge base."
    )
    sources = [h["filename"] for h in hits]
    source_dirs = [h["source"] for h in hits]

    retrieval_detail = (
        f"Retrieved {len(hits)} document(s): "
        + ", ".join(f"{h['filename']} ({h['source']}, score {h['score']:.2f})" for h in hits)
        if hits else "No matching documents found."
    )
    steps.append(_make_step("Knowledge base retrieval", "pass", retrieval_detail))

    # ── Step 3: Few-shot Claude diagnosis ─────────────────────────────────────
    diagnosis_prompt = (
        "You are a Game Glitch Investigator — an expert at diagnosing bugs "
        "in Streamlit number-guessing games.\n\n"
        "Here are two examples of ideal diagnoses. Follow this exact format.\n\n"
        f"{_FEW_SHOT_EXAMPLES}\n\n"
        "---\n\n"
        "Now diagnose the following symptom using the retrieved patterns below.\n\n"
        f'Symptom: "{symptom}"\n\n'
        "Retrieved patterns:\n---\n"
        f"{context}\n"
        "---\n\n"
        "Provide exactly three numbered points:\n"
        "1. Most likely bug (one sentence)\n"
        "2. Root cause (one to two sentences)\n"
        "3. Suggested fix (specific, with file/function names where possible)\n\n"
        "Do not add a preamble. Do not repeat the symptom."
    )

    try:
        raw_diagnosis = _call_claude(
            [{"role": "user", "content": diagnosis_prompt}], max_tokens=512
        )
        steps.append(_make_step("Claude diagnosis", "pass", "Diagnosis generated using retrieved context."))
    except Exception as exc:
        logger.error("Claude API error (diagnosis): %s", exc)
        steps.append(_make_step("Claude diagnosis", "error", str(exc)))
        return {
            "diagnosis": None, "confidence": 0, "caveat": "",
            "sources": sources, "source_dirs": source_dirs, "flagged": False,
            "error": "AI service unavailable. Check your ANTHROPIC_API_KEY and try again.",
            "steps": steps,
        }

    # ── Step 4: Output guardrails ─────────────────────────────────────────────
    output_ok, filtered = validate_output(raw_diagnosis)
    if not output_ok:
        steps.append(_make_step("Output validation", "blocked", filtered))
        return {
            "diagnosis": None, "confidence": 0, "caveat": "",
            "sources": sources, "source_dirs": source_dirs, "flagged": True,
            "error": filtered, "steps": steps,
        }

    steps.append(_make_step("Output validation", "pass", "Response passed safety checks."))

    # ── Step 5: Self-critique ─────────────────────────────────────────────────
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
    flag_label = " — flagged for human review" if flagged else ""
    steps.append(_make_step(
        "Self-critique",
        "warn" if flagged else "pass",
        f"Confidence: {confidence}/100{flag_label}."
    ))

    if flagged:
        logger.info("Low confidence (%d) — flagging for human review.", confidence)

    elapsed = time.monotonic() - t0
    logger.info(
        "Diagnosis complete in %.2fs | confidence=%d | sources=%s",
        elapsed, confidence, sources,
    )

    return {
        "diagnosis": filtered,
        "confidence": confidence,
        "caveat": caveat,
        "sources": sources,
        "source_dirs": source_dirs,
        "flagged": flagged,
        "error": None,
        "steps": steps,
    }
