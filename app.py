import random

import streamlit as st

from agent import CONFIDENCE_THRESHOLD, diagnose
from logic_utils import check_guess, get_range_for_difficulty, parse_guess, update_score

HINT_MESSAGES = {
    "Win": "Correct!",
    "Too High": "Go LOWER!",
    "Too Low": "Go HIGHER!",
}

st.set_page_config(page_title="Game Glitch Investigator", page_icon="🎮")
st.title("🎮 Game Glitch Investigator")

tab_game, tab_ai = st.tabs(["Play the Game", "AI Glitch Detective"])

# ── Shared sidebar (affects the game tab) ────────────────────────────────────

st.sidebar.header("Game Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limit_map[difficulty]
low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

# ── Session state initialisation ─────────────────────────────────────────────

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

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "status" not in st.session_state:
    st.session_state.status = "playing"
if "history" not in st.session_state:
    st.session_state.history = []

# ── Tab 1: Play the Game ──────────────────────────────────────────────────────

with tab_game:
    st.subheader("Make a guess")
    st.info(
        f"Guess a number between {low} and {high}. "
        f"Attempts left: {attempt_limit - st.session_state.attempts}"
    )

    with st.expander("Developer Debug Info"):
        st.write("Secret:", st.session_state.secret)
        st.write("Attempts:", st.session_state.attempts)
        st.write("Score:", st.session_state.score)
        st.write("Difficulty:", difficulty)
        st.write("History:", st.session_state.history)

    raw_guess = st.text_input("Enter your guess:", key=f"guess_input_{difficulty}")

    col1, col2, col3 = st.columns(3)
    with col1:
        submit = st.button("Submit Guess")
    with col2:
        new_game = st.button("New Game")
    with col3:
        show_hint = st.checkbox("Show hint", value=True)

    if new_game:
        st.session_state.attempts = 0
        st.session_state.secret = random.randint(low, high)
        st.session_state.status = "playing"
        st.session_state.history = []
        st.session_state.score = 0
        st.success("New game started.")
        st.rerun()

    if st.session_state.status != "playing":
        if st.session_state.status == "won":
            st.success("You already won. Start a new game to play again.")
        else:
            st.error("Game over. Start a new game to try again.")
    elif submit:
        ok, guess_int, err = parse_guess(raw_guess)

        if not ok:
            st.error(err)
        elif guess_int < low or guess_int > high:
            st.error(f"Please enter a number between {low} and {high}.")
        else:
            st.session_state.attempts += 1
            st.session_state.history.append(guess_int)

            outcome = check_guess(guess_int, st.session_state.secret)

            if show_hint:
                st.warning(HINT_MESSAGES[outcome])

            st.session_state.score = update_score(
                current_score=st.session_state.score,
                outcome=outcome,
                attempt_number=st.session_state.attempts,
            )

            if outcome == "Win":
                st.balloons()
                st.session_state.status = "won"
                st.success(
                    f"You won! The secret was {st.session_state.secret}. "
                    f"Final score: {st.session_state.score}"
                )
            elif st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! The secret was {st.session_state.secret}. "
                    f"Score: {st.session_state.score}"
                )

    st.divider()
    st.caption("Built by an AI that claims this code is production-ready.")

# ── Tab 2: AI Glitch Detective ────────────────────────────────────────────────

with tab_ai:
    st.subheader("AI Glitch Detective")
    st.write(
        "Describe a bug or weird behaviour you noticed in the game. "
        "The AI will retrieve relevant patterns from its knowledge base, "
        "diagnose the issue, and rate its own confidence."
    )

    symptom = st.text_area(
        "Describe the bug symptom:",
        placeholder="e.g. The secret number changes every time I click Submit.",
        max_chars=500,
        height=100,
        key="symptom_input",
    )

    if st.button("Investigate", key="investigate_btn"):
        if not symptom.strip():
            st.warning("Please describe a symptom first.")
        else:
            with st.spinner("Retrieving patterns and diagnosing..."):
                result = diagnose(symptom)

            if result["error"]:
                st.error(result["error"])
            else:
                # Confidence badge
                conf = result["confidence"]
                if conf >= 80:
                    badge = f"Confidence: {conf}/100 — High"
                    st.success(badge)
                elif conf >= CONFIDENCE_THRESHOLD:
                    badge = f"Confidence: {conf}/100 — Medium"
                    st.warning(badge)
                else:
                    badge = f"Confidence: {conf}/100 — Low (human review recommended)"
                    st.error(badge)

                st.markdown("### Diagnosis")
                st.markdown(result["diagnosis"])

                if result["caveat"]:
                    st.caption(f"Note: {result['caveat']}")

                if result["sources"]:
                    with st.expander("Knowledge base sources used"):
                        for src in result["sources"]:
                            st.markdown(f"- `{src}`")

    st.divider()
    st.caption(
        "The AI Glitch Detective uses Retrieval-Augmented Generation (RAG): "
        "it searches a bug-pattern knowledge base before generating its answer."
    )
