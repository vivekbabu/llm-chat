# Parity Baseline — LLM Chat App

Captured from static analysis of `src/data_explorer_chat.py`, `src/initialize_chat_bot.py`,
and `src/large_language_model_utilities.py` as of the current `main` branch.

**Live-transcript capture (15–25 real interactions) and screenshots are PENDING.** No
`OPENAI_API_KEY` is configured in this environment, and the current app is hardcoded to
OpenAI, so it cannot be driven live right now. The scope decision for this rewrite is to
move straight to Claude — once the new app is running against `ANTHROPIC_API_KEY`, the
regression fixtures in `evals/fixtures/` (added in this rewrite) should be run manually
against a copy of the *old* app (temporarily supplied an OpenAI key) at least once to
confirm this table, or the table should be marked "verified by code-reading only" if that
step is explicitly waived. This is called out again in `docs/FUTURE.md`.

## User-facing features

| # | Feature | Where it lives today | Observable behaviour | How to verify in new app |
|---|---|---|---|---|
| 1 | CSV upload | `data_explorer_chat.py:27-29` (`st.file_uploader`, type=csv) | User picks a `.csv` file; it's parsed into a `pandas.DataFrame`. No upload → empty df. | Upload same file, confirm dataframe is available to the agent |
| 2 | System prompt seeding | `data_explorer_chat.py:31-33` | On first upload, a system message is created: *"You are a python expert... available columns are: `{df.columns}`"* | New agent's system/identity prompt must reference the actual uploaded columns |
| 3 | Model picker | `initialize_chat_bot.py:26-31` | Dropdown of `gpt-3.5-turbo`, `gpt-4`, `gpt-3.5-turbo-16k`. Note: the LLM call layer actually defaults to `gpt-4o`, which isn't even in this dropdown — a pre-existing inconsistency in the old app. | New picker lists the actual Claude models the app supports; default matches what's wired in code |
| 4 | Temperature control | `initialize_chat_bot.py:33-44` | Slider 0.0–2.0, default 0.05 | Same range/default semantics, passed through to model calls |
| 5 | Max tokens control | `initialize_chat_bot.py:45-55` | Slider 0–`MAX_LENGTH_MODEL_DICT[model]`, default 4096 | Same bound-by-model-limit behaviour |
| 6 | Top-P control | `initialize_chat_bot.py:56-68` | Slider 0.0–1.0, default 0.5 | Same |
| 7 | Memory window | `data_explorer_chat.py:16-25, 43-48` | Slider 1–10 "past chat interactions retained." Once history exceeds `2*window` messages, truncates to `[system] + last (2*window-2)` messages. | Same truncation math, or an explicit compaction strategy that documents the replacement (per rewrite brief §2.4) |
| 8 | Chat input | `initialize_chat_bot.py:14-20` (`get_text`) | `st.chat_input` box with placeholder text | Composer accepts free text |
| 9 | Duplicate-submit guard | `data_explorer_chat.py:56-58` | If the new input equals the immediately-previous input (Streamlit rerun artifact), it's silently dropped | Preserve — don't re-send identical consecutive input due to framework re-render |
| 10 | Empty-dataframe guard | `data_explorer_chat.py:61-62` | If user submits a question with no file uploaded, shows a `st.warning` ("The dataframe is empty...") and does not call the LLM | Same guard, same non-blocking warning UX |
| 11 | Data Q&A via pandas agent | `large_language_model_utilities.py:130-149` | Non-plot questions run a LangChain `create_pandas_dataframe_agent` (OPENAI_FUNCTIONS type, `allow_dangerous_code=True`) against the full message history. Streams intermediate "thoughts" via `StreamlitCallbackHandler`. Shows the last executed pandas query in a `st.status("Code executed successfully.")` box, then the final answer text. | New agent must: accept NL question, generate+execute pandas code against the df, show the code it ran, show the final answer, stream intermediate reasoning |
| 12 | Plot/chart generation | `large_language_model_utilities.py:39-47, 92-121` | If the message contains "plot"/"graph"/"draw"/"chart" (case-insensitive), a code-gen prompt is appended asking for Plotly-only code in a fenced ```python block. Code is regex-extracted, `fig.show()` stripped, `st.plotly_chart(...)` appended, the code text is shown, then `exec()`'d in-app to render the chart. | New app must render an inline chart when asked, and show the generating code for transparency |
| 13 | Plot failure handling | `large_language_model_utilities.py:110-115` | If no fenced code block is found in the LLM response, shows a `st.warning` ("No data found to plot...") and returns "Couldn't plot the data" instead of crashing | Same graceful no-op-with-message behaviour |
| 14 | Agent error handling | `large_language_model_utilities.py:150-156` | `OutputParserException` → friendly "please refine your query" message; any other exception → generic "unknown error, please refine your query" message. Never crashes the app. | Preserve graceful-degradation guarantee — the rewrite brief's adversarial-set requirement (§3.2) formalizes this further |
| 15 | Response persistence | `data_explorer_chat.py:64-71` | User + assistant turns appended to `st.session_state["messages"]`, `["past"]`, `["generated"]` for re-render on Streamlit rerun | New app persists conversation turns so a refresh doesn't lose history (a real upgrade — old app's persistence is in-memory-only per browser session) |
| 16 | Alternate generic chatbot | `initialize_chat_bot.py:78-136` (`chatbot()`) | A second, **not wired to `__main__`**, dead/alternate entry point: generic Q&A + plot-if-asked, rendered with `streamlit_chat.message()` bubbles instead of `st.chat_message`. Not reachable via the documented `streamlit run src/data_analyst_chat.py` command (which itself doesn't even match either actual filename — README is stale). | **Flagged for confirmation, not silently dropped** — see "Open questions" below |
| 17 | Auth via env/`.env` | `large_language_model_utilities.py:14-18` | Reads `OPENAI_API_KEY` from process env, else loads `src/.env` | New app reads `ANTHROPIC_API_KEY` (per explicit instruction to move to Claude) the same way — env var first, `.env` fallback |
| 18 | Sample dataset | `data/world_population.csv` | Present in repo but **not auto-loaded anywhere in code** — purely a suggested demo file the user can manually upload | Keep available as a suggested/seed dataset; new app may offer it as a one-click sample load (quality improvement, not scope creep, since "let user use a sample dataset" is arguably already implied by the file's presence) |

## API / integration surface

- **Single external integration**: OpenAI Chat Completions API (`openai` SDK), called two ways:
  - Direct `openai.chat.completions.create(...)` for the plot-code-gen path
  - Via `langchain_experimental.agents.create_pandas_dataframe_agent` for the data-Q&A path
- No REST/HTTP API of the app's own — Streamlit is a monolithic server-rendered app, no separate frontend/backend contract to preserve.
- No streaming protocol beyond LangChain's internal `StreamlitCallbackHandler` (renders intermediate agent "thought" text into a container as it's produced; not token-level SSE).
- No persisted database — all state lives in Streamlit `session_state` (server-side, per-browser-session, lost on process restart).

## Persisted entities (all in-memory only, today)

| Entity | Shape | Notes |
|---|---|---|
| `messages` | `list[{"role": str, "content": str}]` | OpenAI chat-message format; index 0 is always the system prompt |
| `past` | `list[str]` | User inputs, parallel array to `generated` |
| `generated` | `list[str]` | Assistant outputs, parallel array to `past` |
| Uploaded dataframe | in-process `pandas.DataFrame`, never written to disk | Re-uploaded every session; not persisted across runs |

## Edge cases that look intentional (must carry forward or explicitly supersede)

- Truncating history to system + last N pairs rather than dropping the system prompt.
- Silently ignoring an exact-duplicate consecutive submission (Streamlit double-fire protection).
- Never letting a parser/agent exception propagate to a crash — always a friendly chat message.
- Stripping `fig.show()` from generated Plotly code before exec (since it's Streamlit, not a notebook).
- Only firing the plot-code path on keyword match, not on every turn (keeps normal Q&A cheap and un-diverted).

## Open questions for sign-off

1. **Item #16 (the dead `chatbot()` alternate entry point)** — this is unreachable in the current app (never called from `__main__`, and the README's documented run command doesn't match either real filename). Per "ask before you drop": should the rewrite (a) preserve it as a genuinely reachable second mode, (b) treat it as unreachable dead code and drop it, or (c) fold its one distinguishing feature (generic non-dataframe chat) into the main app as a mode toggle? **Assumed (c)** for planning purposes — flag if wrong.
2. **README mismatch** — README says `streamlit run src/data_analyst_chat.py`; the real file is `src/data_explorer_chat.py`. New README will be accurate; noting this isn't "scope creep," it's a pre-existing bug being fixed incidentally.
3. **Live-transcript verification** — flagged above as pending; proceeding on the explicit instruction to move to Claude rather than sourcing an OpenAI key for the old app.

## Provider change (explicit instruction, not a parity break)

The rewrite uses the **Anthropic Claude API** instead of OpenAI. This is an explicit instruction, not a feature drop — see `docs/ADR-001-agent-runtime.md` for how this is made swappable rather than hardcoded a second time.
