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

These are real outputs from the system.

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

## Reflection

Building this project changed the way I think about what it means to use AI responsibly in a real application. It is easy to wire up an API call and display whatever comes back. It is much harder to build a system that fails gracefully, tells the user when it is uncertain, and cannot be trivially manipulated into doing something it shouldn't.

The self-critique step surprised me most. I expected it to always return high confidence — after all, Claude is reading its own output. But when I gave it genuinely ambiguous symptoms, the confidence scores dropped meaningfully and the caveats were honest. That taught me that self-evaluation in language models is more useful than I expected, and that the way you prompt for it matters enormously — a separate call produces better signal than a combined prompt.

I also came to appreciate that guardrails are not just a safety checkbox. Writing the topic-relevance filter forced me to think carefully about what my system is actually for, and what it is not for. Every rejected input is a case I consciously decided to handle with a clear error message instead of an AI hallucination. That discipline — defining the boundaries of the system explicitly — is something I want to carry into every AI project I build in the future.

---

## Responsible AI Reflection

**What are the limitations or biases in your system?**

The most significant limitation is that the knowledge base is hand-curated and closed. It contains exactly ten bug patterns drawn from one project, which means the AI will retrieve confidently — and often incorrectly — for bugs that don't map to any of those ten documents. The retriever always returns its best match even when nothing is genuinely relevant, so a symptom the corpus has never seen will still produce a diagnosis that sounds authoritative. That is a real risk. I partially address it through the confidence score and the human-review flag, but a user who doesn't notice the low badge could still act on a bad diagnosis.

There is also a bias toward Streamlit-specific framing. Every document was written with Streamlit session state in mind, so symptoms described in different terms — even if they describe the same underlying bug — may retrieve the wrong document or score poorly. A user who writes "my variable resets" will score better than one who writes "my data disappears," even though they mean the same thing.

**Could your AI be misused, and how would you prevent that?**

The most realistic misuse is prompt injection — someone crafting a symptom description that attempts to override the system prompt or extract information it shouldn't reveal. I built two layers of defense against this: the input guardrails reject inputs containing phrases like "ignore previous instructions" or "ignore all prior" before they ever reach Claude, and the output guardrails scan the response for blocked patterns before it is displayed. Neither layer is foolproof, but together they make the most common injection patterns fail at the cheapest possible point in the pipeline — before any API call is made.

A subtler misuse is over-reliance. Someone could treat a high-confidence diagnosis as ground truth and apply the suggested fix without reading the code. I try to counter this by always showing the knowledge base sources alongside the answer, so the user can read the reasoning behind the diagnosis rather than just following the instruction. Transparency about where the answer came from is itself a form of misuse prevention.

**What surprised you while testing the AI's reliability?**

I expected the self-critique confidence scores to be uniformly high — I assumed Claude would rate its own answers generously. In practice, when I gave it genuinely ambiguous or underspecified symptoms, the confidence scores dropped noticeably and the caveats were specific and honest rather than generic boilerplate. A vague input like "something weird happens sometimes" produced scores in the 40–50 range with caveats that explained exactly what information was missing. That was more useful behavior than I anticipated, and it made me trust the flagging system more than I did when I first designed it.

I was also surprised by how brittle the self-critique JSON parsing was in early testing. A small change to the prompt wording — adding "respond in JSON" versus "respond with ONLY valid JSON" — changed whether Claude wrapped the output in a code fence. That kind of sensitivity to exact prompt wording is easy to underestimate, and it taught me to always write a fallback for any structured output I'm parsing from a language model.

**Collaboration with AI during this project**

I used Claude Code as my primary AI collaborator throughout the build. It wrote the first drafts of `retriever.py`, `guardrails.py`, and `agent.py`, and suggested the two-call self-critique architecture — separating diagnosis and confidence rating into sequential prompts rather than combining them. That suggestion turned out to be genuinely valuable. When I tested a combined prompt, confidence scores clustered around 85–90 regardless of input quality. The separate call produced a much wider range and caught low-quality diagnoses more reliably. I wouldn't have split them without the AI suggesting it.

The one instance where the AI's suggestion was flawed: in the first version of `agent.py`, the self-critique prompt instructed Claude to respond with JSON "inside a code fence." The AI wrote the parser to strip the fence, but also added a condition that assumed the fence would always be present. When I changed the prompt wording slightly in testing and Claude stopped adding the fence, the parser silently returned the raw string instead of a number, and confidence defaulted to 50 every time without any warning. The bug was subtle because the fallback value was valid — nothing crashed — but every response was being flagged at the 50-confidence threshold. I caught it by noticing the badge color never changed across very different inputs. The fix was to make the code-fence stripping optional rather than assumed, and to log a warning whenever the fallback was triggered. The AI wrote code that handled its own intended output format, but not its actual output under slightly different conditions — a good reminder that AI-generated code needs the same skeptical review as any other code.

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
