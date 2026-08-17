# Deliberately Deferred

Everything below was in the original rewrite brief and is a real gap against
its "definition of done." None of it was silently dropped — the build scope
("Minimal agentic upgrade") was chosen explicitly over the fuller options when
asked, and this list is the honest accounting of what that traded away.
Nothing here represents a *feature* users of the old app could do that the
new app can't (see `docs/PARITY.md`); this is scope the brief wanted beyond
parity.

## Harness

- **Eval suite** (`evals/` directory, LLM-as-judge with a checked-in rubric
  and calibration set, adversarial/prompt-injection set, CI-wired scorecard
  artifacts). Nothing currently regression-tests agent *behavior* — only the
  sandboxed tool functions have tests (`tests/test_tools_server.py`).
- **15–25 live behavioral fixtures** vs. the old app, never captured — no
  OpenAI key was available in this environment. If one becomes available,
  run the old app once against real transcripts and diff behavior against
  `docs/PARITY.md`'s assumptions.
- **Self-hosted tracing viewer** (Langfuse/Phoenix/Laminar). Tracing exists
  (`data/traces.jsonl`, surfaced in the UI's trace panel) but there's no
  queryable trace explorer across runs/conversations.
- **Guardrail middleware** as explicit, testable input/output filters —
  currently the only safety measures are the restricted-exec sandbox in
  `tools_server.py` and graceful exception handling in `app.py`.
- **Rate/cost caps per user or conversation.**
- **Retries with jitter, circuit breakers, automatic provider failover.** A
  Claude API error currently surfaces as a friendly chat message, not a retry.
- **Idempotency keys** on runs — a client retry could re-run a turn.
- **Prompt/semantic caching.**

## Conversational layer

- **Token-level streaming.** Responses currently arrive as one block (`await
  model.ainvoke(...)`) rather than streaming deltas into the UI as they
  generate. This is the single highest-leverage next improvement for "feel."
- **AG-UI-style typed event vocabulary** for the frontend.
- **Generative UI components** beyond a rendered Plotly chart (e.g. structured
  cards, forms).
- **Mid-stream interruption/steering** — no way to stop or redirect a turn
  once it's started.
- **Structured outputs / schema validation** on tool arguments beyond MCP's
  own JSON-schema tool definitions.

## UI

- **Next.js/shadcn/Motion rewrite.** Current UI is a revamped but still
  fundamentally Streamlit single-page app.
- **Virtualized message list**, tested at scale (5,000+ messages).
- **Full design system** (type scale, 8px grid, documented elevation model),
  dark mode audited as a first-class palette rather than Streamlit's built-in
  toggle.
- **Command palette (⌘K), keyboard-first composer shortcuts, per-message
  regenerate/edit-and-branch/fork/share/delete actions.**
- **WCAG 2.2 AA automated audit**, keyboard-only walkthrough.
- **Performance budgets enforced in CI** (LCP/INP/CLS/bundle size) — not
  meaningfully applicable to a server-rendered Streamlit app in its current
  form, but would apply directly if/when the Next.js rewrite happens.

## Infrastructure

- **Postgres + pgvector, Redis.** Current persistence is SQLite
  (conversation checkpoints) and a flat JSONL file (traces) — sufficient for
  single-instance local use, not for multi-instance or high-volume deployment.
- **Multi-service Docker Compose profiles** (`dev`/`local-models`/`full`).
  Current compose file is a single `app` service.
- **Offline/local-model profile** (Ollama/vLLM/LM Studio), proven with the
  network disabled. Currently the app hard-depends on the Anthropic API.
- **Multi-provider model abstraction** beyond "swap the `ChatAnthropic(...)`
  construction line." No env-var-driven provider switch exists yet.

## Architecture

- **Persistent MCP session** across a whole conversation instead of
  reconnect-per-turn (see `docs/ADR-001-agent-runtime.md`'s noted tradeoff).
- **Episodic/semantic memory tiers** (retrieved prior conversations, durable
  user facts/preferences editable in the UI). The old app never had these,
  so this is a genuine addition candidate, not a parity restoration.
- **Conversation browser** — resuming works if you keep the `?thread=...` URL,
  but there's no in-app list of past conversations to pick from.
