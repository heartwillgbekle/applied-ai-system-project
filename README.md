# Game Glitch Investigator — Applied AI System

**By Heartwill Gbekle**

---

## Original Project

This project extends my Module 1 work: **Game Glitch Investigator: The Impossible Guesser**. The original was a deliberately broken Streamlit number-guessing game where my goal was to find, understand, and fix ten hidden bugs — reversed hint logic, Streamlit session state resets, type comparison errors, swapped difficulty ranges, and more. It taught me how to read code skeptically, use AI as a debugging partner, and write pytest tests to verify my fixes. The fixed game is still playable here; what I added on top of it is the AI system described below.

---

## Title and Summary

**Game Glitch Investigator** is a two-tab Streamlit app. The first tab is the playable number-guessing game from Module 1. The second tab — the AI Glitch Detective — lets a user describe any bug symptom they notice in the game and receive a structured diagnosis powered by Claude.

I built this because debugging is genuinely hard, and most tools either give you the answer outright or leave you completely on your own. I wanted to explore a middle ground: a system that reasons from a curated knowledge base, explains its thinking, and tells you honestly when it isn't sure. The result is a small but complete applied AI pipeline that demonstrates retrieval, agentic reasoning, safety guardrails, self-evaluation, and structured testing — all integrated into a single working application.

---

## AI Features

| Feature | How it's used |
|---|---|
| **RAG** | TF-IDF retriever searches a 13-document knowledge base (bugs + patterns) before Claude generates a diagnosis |
| **Agentic loop** | 5-step pipeline with observable steps: validate → retrieve → diagnose → validate → self-critique |
| **Self-critique** | Claude rates its own confidence (0–100) and adds a caveat when below 60 |
| **Guardrails** | Input and output are validated for length, blocked patterns, prompt injection, and topic relevance |
| **Reliability testing** | 35 pytest tests + standalone `eval.py` harness: 29 cases, colour-coded table, exit code |

## Stretch Features

| Stretch | What I built |
|---|---|
| **RAG Enhancement** | Added `knowledge_base/patterns/` with 3 general docs (Streamlit state guide, Python type error patterns, pytest strategies). Retriever searches both corpora and tags each result with its source directory. Corpus grew from 10 to 13 documents. See impact comparison below. |
| **Agentic Enhancement** | Every `agent.diagnose()` call returns a `steps` list: one entry per pipeline stage with name, status (`pass`/`warn`/`blocked`/`error`), and a detail string. The app renders these in an expandable "Reasoning trace" section so the user can see exactly what happened at each step. |
| **Specialization** | Two few-shot examples are injected at the top of every diagnosis prompt, constraining tone and format. See measurable output difference below. |
| **Test Harness** | `eval.py` runs 29 predefined cases through retrieval, guardrails, and the mocked agent, prints a colour-coded pass/fail table with retrieval scores and confidence ratings, and exits with code 1 on any failure. Run with `python eval.py`. |

### RAG Enhancement — Impact on Output Quality

Query: `"how do I write a pytest test for my check_guess function"`

| | Top result | Score |
|---|---|---|
| **Before** (bugs corpus only) | `stub_functions.md` — describes unimplemented stubs, not how to write tests | 0.160 |
| **After** (bugs + patterns) | `pytest_testing_patterns.md` — directly covers pytest structure for game logic | 0.208 |

Without the patterns corpus, the retriever's best match was a document about stub functions — tangentially related but not helpful. With the expanded corpus, the correct document ranks first and Claude receives direct guidance on writing tests, producing a diagnosis that actually answers the question.

### Specialization — Measurable Output Difference

The two few-shot examples constrain Claude to a strict three-point format with file and function references in the fix step.

**Zero-shot output** (no examples in prompt):
> "That's a great question about your game! Based on what you've described, it sounds like there might be an issue with how Streamlit handles state. When a user interacts with your app, Streamlit re-runs the script. You might want to look into using session state to persist your values across reruns. Let me know if you need more help!"

**Few-shot output** (two examples in prompt):
> "1. **Most likely bug:** The secret number is regenerated on every rerun because it is not stored in `st.session_state`.
> 2. **Root cause:** Streamlit re-executes the full script on every button click. A bare `random.randint()` call outside a session state guard produces a new value on each interaction.
> 3. **Suggested fix:** In `app.py`, replace the bare assignment with `if "secret" not in st.session_state: st.session_state.secret = random.randint(low, high)`."

The few-shot version omits the preamble, uses consistent numbered section labels, names the specific file, and includes a code snippet. The zero-shot version is conversational and vague. This format consistency is verifiable across every response the system produces.

---

## Architecture Overview

![System architecture diagram](assets/system_architecture.png)

```mermaid
flowchart TD
    U([User]) -->|types bug symptom| GI

    subgraph GUARDRAILS_IN ["Input Guardrails  (guardrails.py)"]
        GI{Valid input?}
    end

    GI -->|blocked: off-topic /\ninjection / too long| ERR1([Error shown to user])
    GI -->|passes| RET

    subgraph RAG ["Retrieval  (retriever.py)"]
        RET["TF-IDF cosine search\nover knowledge_base/bugs/\n(10 bug-pattern documents)"]
        KB[("knowledge_base/\nbugs/*.md")]
        KB --> RET
    end

    RET -->|top-3 matching docs| LLM1

    subgraph AGENT ["Agentic Loop  (agent.py)"]
        LLM1["Claude Haiku\n— diagnosis —\n(RAG context injected)"]
        LLM1 --> GO
        GO{Output safe?}
        GO -->|blocked pattern\nin response| ERR2([Safety error shown])
        GO -->|passes| LLM2
        LLM2["Claude Haiku\n— self-critique —\nrates confidence 0–100"]
    end

    LLM2 -->|confidence + caveat| DISP

    subgraph UI ["Streamlit UI  (app.py)"]
        DISP["Display diagnosis\n+ colour-coded confidence badge\n+ knowledge base sources"]
    end

    DISP -->|confidence < 60| FLAG(["⚠ Flagged for\nhuman review"])
    DISP -->|confidence ≥ 60| DONE([Result shown to user])

    subgraph TESTS ["Reliability Tests  (tests/test_agent.py)"]
        T1["Guardrail tests\n(acceptance + rejection)"]
        T2["Retriever ranking tests\n(5 known bug symptoms)"]
        T3["Agent contract tests\n(mocked Claude)"]
        T4["Live API smoke test\n(skipped without key)"]
    end

    GUARDRAILS_IN -.->|pytest| T1
    RAG -.->|pytest| T2
    AGENT -.->|pytest| T3
    AGENT -.->|pytest| T4

    style GUARDRAILS_IN fill:#fef3c7,stroke:#d97706
    style RAG fill:#dbeafe,stroke:#2563eb
    style AGENT fill:#ede9fe,stroke:#7c3aed
    style UI fill:#dcfce7,stroke:#16a34a
    style TESTS fill:#f1f5f9,stroke:#64748b
```

The system has five layers. When a user submits a symptom, it first passes through **input guardrails** that reject off-topic questions, oversized inputs, prompt injection attempts, and blocked code patterns. Valid input goes to the **TF-IDF retriever**, which scores all ten knowledge base documents by cosine similarity and returns the top three matches. Those documents are injected into a prompt sent to **Claude Haiku**, which generates a structured diagnosis grounded in the retrieved context — that is the RAG step. The diagnosis is then checked again by the **output guardrails** before it ever reaches the user. Finally, a second Claude call performs **self-critique**: it reads its own diagnosis and returns a confidence score between 0 and 100, plus a one-sentence caveat if confidence is below 70. Answers below 60 are flagged for human review. The **test suite** probes each layer independently with mocked and live calls.

---

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/heartwillgbekle/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

The AI Glitch Detective tab requires a key. The game tab works without one.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### 4. Run the app

```bash
python -m streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`). Use the **Play the Game** tab to play, or the **AI Glitch Detective** tab to diagnose a bug.

### 5. Run the tests

```bash
pytest
```

All 35 offline tests pass without an API key. The one live API smoke test is automatically skipped when `ANTHROPIC_API_KEY` is not set.

---

## Sample Interactions

These are representative example outputs that reflect how the system behaves. The structure and sources shown match what the pipeline actually produces; exact wording will vary across runs because Claude generates responses dynamically.

---

**Example 1 — State reset bug**

> **Input:** "The secret number changes every time I click Submit. I can never win because the target keeps moving."

> **Diagnosis (Confidence: 92/100 — High):**
>
> 1. **Most likely bug:** The secret number is being regenerated on every Streamlit rerun instead of being stored persistently.
>
> 2. **Root cause:** Streamlit re-executes the entire script from top to bottom on every user interaction. If the secret is assigned with a plain `random.randint()` call outside of a session state guard, it gets a fresh value each time the Submit button triggers a rerun.
>
> 3. **Suggested fix:** Wrap the secret generation in `if "secret" not in st.session_state: st.session_state.secret = random.randint(low, high)`. This ensures the number is only generated once — on first load — and survives all subsequent reruns.
>
> *Sources used: `state_reset.md`, `difficulty_reset.md`*

---

**Example 2 — Reversed hints**

> **Input:** "The hints are backwards. When I guess too high it tells me to go higher, and when I guess too low it tells me to go lower. I can never win by following them."

> **Diagnosis (Confidence: 95/100 — High):**
>
> 1. **Most likely bug:** The return values in the hint comparison function are swapped.
>
> 2. **Root cause:** When `guess > secret` the player needs to go lower, but the function returns "Go HIGHER!" instead. The branches for "Too High" and "Too Low" have been reversed, likely a copy-paste mistake during initial scaffolding.
>
> 3. **Suggested fix:** In `check_guess`, change `if guess > secret: return "Too Low"` to `return "Too High"`, and flip the else branch accordingly. Verify with `assert check_guess(60, 50) == "Too High"`.
>
> *Sources used: `hint_reversal.md`, `type_comparison.md`*

---

**Example 3 — Guardrail rejection**

> **Input:** "What is the capital of France?"

> **Error shown:** "Please describe a bug related to the game (e.g. hints, score, secret number, state, range, difficulty)."

The system never calls the API. The guardrail catches the off-topic input before any cost is incurred and returns a specific, helpful error message explaining what kind of input it expects.

---

## Design Decisions

**Why TF-IDF instead of a vector database?**
I chose TF-IDF with scikit-learn because it has zero infrastructure overhead — no external API, no database to stand up, no embedding costs. For a corpus of ten documents it is more than accurate enough, and I could verify the ranking behaviour directly in my test suite. If this grew to hundreds of documents I would switch to a proper embedding model, but premature complexity would have obscured the core RAG concept I was trying to demonstrate.

**Why two separate Claude calls instead of one?**
I deliberately separated diagnosis and self-critique into two API calls rather than asking Claude to do both in a single prompt. A combined prompt tends to produce artificially high confidence because the model anchors on its own just-generated answer. Asking for a self-critique in a fresh call, with the diagnosis shown as input text, produces more honest confidence scores and surfaces genuine uncertainty.

**Why Claude Haiku?**
Speed and cost. For a bug diagnosis assistant, the bottleneck is retrieval quality and prompt design, not model scale. Haiku is fast enough that the spinner in the UI feels responsive, and it keeps API costs low for anyone running this on a student account. The prompts are explicit and structured enough that a smaller model handles them reliably.

**Why guardrails on both input and output?**
Input guardrails protect cost and safety before any API call is made. Output guardrails are a separate concern — they catch cases where the model might return something unexpected despite a well-formed input. Having both layers means each one has a single, clear responsibility and can be tested independently.

**Trade-offs I accepted:**
The knowledge base is hand-curated and static. It is highly accurate for the ten bugs in this project but would not generalise to arbitrary Streamlit bugs without adding new documents. I accepted this trade-off because a focused, well-documented corpus performs better for its intended scope than a larger, noisier one.

---

## Testing Summary

**35 out of 35 offline tests pass; 1 live API smoke test is skipped automatically when `ANTHROPIC_API_KEY` is not set. All tests run in under 2.5 seconds. The retriever correctly ranked the right document first for all 5 known bug symptoms. Confidence scoring is built into every AI response — answers below 60/100 are flagged for human review. Every error in the pipeline is caught, logged, and returned as a structured message rather than a crash.**

I wrote 36 tests across four classes in `tests/test_agent.py`, plus the three original game logic tests in `tests/test_game_logic.py`.

| Layer | Tests | Result |
|---|---|---|
| Input guardrails | 9 | 9/9 passed |
| Output guardrails | 5 | 5/5 passed |
| TF-IDF retriever | 10 | 10/10 passed — correct top doc for every known symptom |
| Agent contract (mocked) | 7 | 7/7 passed |
| Live API smoke test | 1 | skipped (no key) |
| Game logic (Module 1) | 3 | 3/3 passed |
| **Total** | **35 + 1 skipped** | **35 passed, 0 failed** |

**Confidence scoring:** Every diagnosis includes a self-rated confidence score from 0–100. The UI shows a green badge (≥ 80), yellow badge (60–79), or red badge with a "human review recommended" warning (< 60). This means the system never silently returns a low-quality answer — it always tells the user how much to trust it.

**Logging and error handling:** Every guardrail rejection, retrieval result, API error, and self-critique parse failure is logged with a timestamp and severity level. A blocked input logs the matched rule. An API outage returns `{"error": "AI service unavailable. Check your ANTHROPIC_API_KEY and try again."}` rather than an unhandled exception. A JSON parse failure in self-critique falls back to confidence 50 with a caveat, keeping the app functional.

**What didn't work initially:**
My first self-critique prompt asked Claude to return JSON inside a markdown code fence. The parser broke whenever the model added ` ```json ``` ` wrapping. I added a code-fence stripper and a graceful fallback so a parse failure degrades to confidence 50 rather than crashing. The test `test_low_confidence_sets_flagged_true` now catches any regression in that path.

**What I learned:**
Testing AI pipelines means testing the contract (shape, types, error handling) separately from content quality. Contract tests run offline in milliseconds and catch regressions without spending API credits. Content quality — whether the diagnosis is actually correct — needs a live call against a known input, which is why the smoke test exists as a separate gated step.

---

> Reflections on AI collaboration, system limitations, biases, misuse prevention, and testing results are documented in [model_card.md](model_card.md).

---

## Project Structure

```
applied-ai-system-final/
├── app.py                  # Streamlit UI — game tab + AI Glitch Detective tab
├── agent.py                # Agentic diagnosis loop (5-step pipeline)
├── retriever.py            # TF-IDF RAG retriever
├── guardrails.py           # Input/output validation and logging
├── logic_utils.py          # Core game logic (from Module 1)
├── knowledge_base/
│   └── bugs/               # 10 bug-pattern documents (RAG corpus)
├── tests/
│   ├── test_game_logic.py  # Original game logic tests
│   └── test_agent.py       # Reliability suite (36 tests)
├── assets/
│   └── system_architecture.png
├── requirements.txt
└── reflection.md           # Module 1 reflection
```

---

## Module 1 Bug Documentation

### Bugs Found

| # | Bug | Where |
|---|-----|--------|
| 1 | Hint messages reversed — "Go HIGHER!" when guess was too high | `logic_utils.py` → `check_guess` |
| 2 | Secret silently cast to `str` on even attempts, causing wrong lexicographic comparison | `app.py` submit block |
| 3 | Info banner always showed "1 to 100" regardless of difficulty | `app.py` `st.info` call |
| 4 | Hard mode range (1–50) was smaller than Normal (1–100); ranges swapped | `logic_utils.py` → `get_range_for_difficulty` |
| 5 | New Game button used hardcoded `random.randint(1, 100)` | `app.py` new_game block |
| 6 | All logic functions raised `NotImplementedError` | `logic_utils.py` |
| 7 | `attempts` initialized to `1` instead of `0` | `app.py` session state init |
| 8 | `update_score` added +5 on even-numbered wrong guesses | `logic_utils.py` → `update_score` |
| 9 | Difficulty change mid-game kept old secret from previous range | `app.py` — no change detection |
| 10 | Guesses outside the difficulty range were accepted | `app.py` — no range validation |

### Fixes Applied

- Swapped `check_guess` return values so `guess > secret` → "Too High"
- Removed even/odd secret-to-string conversion; always compare int to int
- Updated `st.info` to use `{low}` and `{high}` from `get_range_for_difficulty`
- Fixed difficulty ranges: Easy=1–20, Normal=1–100, Hard=1–500
- Changed hardcoded `randint(1, 100)` to `randint(low, high)` everywhere
- Implemented all four functions in `logic_utils.py`
- Changed `attempts` init from `1` to `0`
- `update_score` now always subtracts 5 for wrong guesses
- Added difficulty-change detection with full session state reset
- Added range validation before accepting a guess

![Winning game screenshot](gamewin.png)
