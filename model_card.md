# Model Card — Game Glitch Investigator

**By Heartwill Gbekle**

---

## AI Collaboration

I used Claude Code as my primary AI collaborator throughout the build. It wrote the first drafts of `retriever.py`, `guardrails.py`, and `agent.py`, and suggested the two-call self-critique architecture — separating diagnosis and confidence rating into sequential prompts rather than combining them. That suggestion turned out to be genuinely valuable. When I tested a combined prompt, confidence scores clustered around 85–90 regardless of input quality. The separate call produced a much wider range and caught low-quality diagnoses more reliably. I wouldn't have split them without the AI suggesting it.

**One helpful suggestion:** The two-call self-critique design. Claude suggested keeping diagnosis and confidence rating in separate API calls so the model couldn't anchor on its own just-generated answer. Testing confirmed this produced more honest, variable confidence scores.

**One flawed suggestion:** In the first version of `agent.py`, the self-critique prompt instructed Claude to respond with JSON "inside a code fence." The AI wrote the parser to strip the fence, but also added a condition that assumed the fence would always be present. When I changed the prompt wording slightly in testing and Claude stopped adding the fence, the parser silently returned the raw string instead of a number, and confidence defaulted to 50 every time without any warning. The bug was subtle because the fallback value was valid — nothing crashed — but every response was being flagged at the 50-confidence threshold. I caught it by noticing the badge color never changed across very different inputs. The fix was to make code-fence stripping optional rather than assumed, and to log a warning whenever the fallback was triggered. AI-generated code needs the same skeptical review as any other code.

---

## Limitations and Biases

**Closed, hand-curated knowledge base.** The corpus contains 13 documents drawn from one project. The retriever always returns its best match even when nothing is genuinely relevant, so a symptom the corpus has never seen can still produce a confident-sounding but poorly-grounded diagnosis. I partially address this through the confidence score and the human-review flag below 60, but a user who ignores the badge could act on a bad answer.

**Streamlit-specific framing bias.** Every document was written with Streamlit session state in mind. Symptoms described in different terms — even if they describe the same underlying bug — may retrieve the wrong document. A user who writes "my variable resets" will score better than one who writes "my data disappears," even though they mean the same thing.

**No relevance threshold.** The retriever does not have a minimum score below which it refuses to return results. A query completely outside the corpus still returns three documents ranked by TF-IDF similarity, giving Claude misleading context to work from.

---

## Misuse and Prevention

**Prompt injection** is the most realistic misuse vector — someone crafting a symptom description to override the system prompt or extract information. Input guardrails reject phrases like "ignore previous instructions" before they reach Claude. Output guardrails scan the response for blocked patterns before it is shown to the user. Both layers are logged so every blocked attempt is recorded.

**Over-reliance** is a subtler risk. Someone could treat a high-confidence diagnosis as ground truth and apply the fix without reading the code. The system counters this by always showing the knowledge base sources alongside the answer, making the reasoning transparent and inviting the user to verify it.

---

## Testing Results

**35 out of 35 offline tests pass. 1 live API smoke test is skipped automatically when `ANTHROPIC_API_KEY` is not set. The standalone evaluation harness (`eval.py`) runs 29 predefined cases across all pipeline layers and prints a colour-coded pass/fail table.**

| Layer | Tests | Result |
|---|---|---|
| Input guardrails | 9 | 9/9 passed |
| Output guardrails | 5 | 5/5 passed |
| TF-IDF retriever | 10 | 10/10 correct top-document ranking |
| Agent contract (mocked Claude) | 7 | 7/7 passed |
| Live API smoke test | 1 | skipped without API key |
| Game logic (Module 1) | 3 | 3/3 passed |
| **Total** | **35 + 1 skipped** | **35 passed, 0 failed** |

**Eval harness summary (`python eval.py`):**
- Retrieval: 10/10 — avg top-doc score 0.299
- Guardrails: 14/14
- Agent contract: 5/5 — avg mocked confidence 45/100
- Total: 29/29 in 0.38s

**Confidence scoring:** Every diagnosis includes a self-rated confidence score from 0–100. The UI shows a green badge (≥ 80), yellow badge (60–79), or red badge with "human review recommended" (< 60). The system never silently returns a low-quality answer.

**Logging and error handling:** Every guardrail rejection, retrieval result, API error, and self-critique parse failure is logged with a timestamp and severity level. An API outage returns a structured error message rather than an unhandled exception. A JSON parse failure in self-critique falls back to confidence 50 with a caveat, keeping the app functional.

**What didn't work initially:**
My first self-critique prompt asked Claude to return JSON inside a markdown code fence. The parser broke whenever the model added ` ```json ``` ` wrapping. I added a code-fence stripper and a graceful fallback so a parse failure degrades to confidence 50 rather than crashing. The test `test_low_confidence_sets_flagged_true` now catches any regression in that path.

**What surprised me:**
I expected confidence scores to be uniformly high — Claude reading its own output. In practice, genuinely ambiguous symptoms produced scores in the 40–50 range with honest, specific caveats. That was more useful behavior than I anticipated and made me trust the flagging system more than I did when I first designed it. I was also surprised by how sensitive prompt wording was — "respond in JSON" vs "respond with ONLY valid JSON" changed whether Claude wrapped output in a code fence, which broke the parser. Exact wording matters more than expected.

---

## Reflection

Building this project changed the way I think about what it means to use AI responsibly in a real application. It is easy to wire up an API call and display whatever comes back. It is much harder to build a system that fails gracefully, tells the user when it is uncertain, and cannot be trivially manipulated into doing something it shouldn't.

The self-critique step taught me that self-evaluation in language models is more useful than I expected, and that the way you prompt for it matters enormously. Writing the topic-relevance filter in the guardrails forced me to define the boundaries of the system explicitly — every rejected input is a case I consciously decided to handle with a clear error message instead of an AI hallucination.

**Future improvements:**

1. Add a relevance threshold to the retriever so it can return "no match found" instead of always returning its best guess. Right now the system can mislead Claude with low-scoring, tangentially related documents.
2. Expand the knowledge base to cover Streamlit bugs beyond this one game, making the diagnostic scope genuinely broad rather than specific to thirteen patterns.
3. Add a user feedback loop — a thumbs-up/thumbs-down button after each diagnosis — so real ratings can accumulate and identify which retrievals and diagnoses are actually useful versus confidently wrong.
