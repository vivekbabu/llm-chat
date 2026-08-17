# ADR-001: Agent Runtime, Tooling, and Deployment Scope

**Status:** Accepted
**Date:** 2026-08-16

## Context

The rewrite brief called for evaluating LangGraph, OpenAI Agents SDK, Claude
Agent SDK, Pydantic AI, and Mastra/Vercel AI SDK as candidate agent runtimes,
plus a full production harness (MCP tool servers, Postgres+pgvector, Redis,
self-hosted Langfuse tracing, a Next.js/shadcn UI, an eval suite with
LLM-as-judge, a11y/perf CI gates, and a multi-service Docker Compose stack
with an offline local-model profile).

The app being replaced is a single ~150-line Streamlit script that lets a user
upload a CSV and ask an LLM (via a LangChain pandas-dataframe agent) to answer
questions or generate a Plotly chart from it. Before building, the user was
asked how much of the full brief to build now versus defer, and chose
**"Minimal agentic upgrade"**: a real agent runtime with typed/checkpointed
state and MCP-based tools, basic tracing, and a nicer single-page UI — with no
new backing services (no Postgres, Redis, or self-hosted Langfuse) and no
Next.js rewrite. Everything deferred under that decision is tracked in
`docs/FUTURE.md`, not silently dropped.

## Decision

### Runtime: LangGraph

Chosen over the alternatives because:
- **Explicit graph + typed state** matches the "typed state, not an untyped
  dict" hard requirement directly (`agent/state.py`'s `AgentState` TypedDict).
- **Built-in SQLite checkpointer** (`langgraph-checkpoint-sqlite`) gives
  durable, resumable, interruptible execution — a real requirement from the
  brief — without standing up Postgres or Redis. `agent/graph.py` checkpoints
  every step to `data/checkpoints.sqlite`, keyed by a `thread_id` carried in
  the URL query string, so reopening the same URL resumes the conversation
  even after a full process restart.
- Rejected **OpenAI Agents SDK** — model-agnostic requirement rules out a
  framework namespaced to one provider's shape, and moving to Claude was an
  explicit instruction.
- Rejected **Claude Agent SDK** — it's a harness for building coding-agent-like
  CLI/filesystem agents (subagents, hooks, permission prompts over a
  workspace); this app's job is answering questions about one uploaded CSV,
  not operating a filesystem, so its ceremony doesn't earn its place here.
- Rejected **Pydantic AI** — genuinely competitive on typed state, but
  LangGraph's checkpointing story is more direct for the durable/resumable
  requirement without extra plumbing.
- Rejected **Mastra / Vercel AI SDK agents** — TypeScript-native, which would
  have forced the Next.js rewrite the user explicitly deferred.

### Tools: MCP over stdio, not hardcoded functions

`agent/tools_server.py` is a local MCP server (using the official Python MCP
SDK's `FastMCP`) exposing two tools, `run_pandas_query` and `render_plot`,
each executing LLM-authored code in a restricted-builtins `exec()` sandbox (no
`import`, `open`, `os`, or `__import__`). `agent/graph.py` launches it as a
stdio subprocess per turn via `langchain-mcp-adapters`' `load_mcp_tools`, and
binds the returned tools onto the model with `bind_tools`. This satisfies "all
agent capabilities are exposed as MCP servers, no tool logic in the agent
loop" without needing a network-exposed MCP service — the subprocess never
listens on a port.

**Known tradeoff, accepted for this scope:** the MCP stdio session is opened
and closed once per turn rather than held open across a whole conversation.
Simpler and correctness-first; a persistent session is a cheap follow-up
(`docs/FUTURE.md`) that wouldn't change any user-visible behavior.

### Model provider: Anthropic Claude, swappable by config

`ChatAnthropic` from `langchain-anthropic` is constructed fresh per turn from
sidebar-selected `model`/`temperature`/`max_tokens`/`top_p` — swapping models
is a dropdown change, not a code change (`ui/sidebar.py::CLAUDE_MODELS`).
Provider swap (e.g. back to OpenAI, or to a local model) would mean swapping
the `ChatAnthropic(...)` construction for another LangChain chat-model class;
nothing else in the graph is Anthropic-specific. Full multi-provider
abstraction (env-var-driven provider selection, an OpenAI-compatible local
model path) was scoped out — see `docs/FUTURE.md`.

### Tracing: local JSONL spans, not a hosted service

`agent/tracing.py` writes one JSON line per model call to `data/traces.jsonl`
with GenAI-semantic-convention-shaped fields (model, tokens in/out, latency,
tool names requested), keyed by a `run_id`. The UI's "📊 Trace" expander under
each assistant message reads spans for that message's `run_id` directly — so
"a trace is reachable from the UI in one click" is genuinely true, just backed
by a flat file instead of self-hosted Langfuse/Phoenix/OpenTelemetry
Collector. The tool-call timeline itself needs no separate trace store: it's
reconstructed straight from the LangGraph message list (`AIMessage.tool_calls`
/ `ToolMessage` pairs), which is already durable via the checkpointer.

### UI: revamped Streamlit, not Next.js

Kept single-process Python/Streamlit rather than the brief's Next.js+shadcn
stack, per the chosen scope ("could stay Streamlit-adjacent"). What *did*
change: a genuine agent-transparency panel (collapsible plan → tool call →
result → answer, per assistant turn), a trace panel, a mode toggle folding in
the old app's unreachable generic-chat mode, one-click sample-dataset
loading, and light theming (`ui/theme.py`, `.streamlit/config.toml`). Full
design-system work, virtualized message lists, generative UI components, and
WCAG/perf CI gates are deferred (`docs/FUTURE.md`).

### Deployment: single-container Docker Compose

One `app` service building from the repo's `Dockerfile`, running
`streamlit run src/app.py`. No Postgres/Redis/tracing-viewer/local-model
services — those were explicitly deferred, not oversight. `data/` is a bind
mount so SQLite checkpoints and traces persist across container restarts.

## Consequences

- Feature parity with the old app is preserved per `docs/PARITY.md`, and
  several items become strictly better without adding scope: durable/resumable
  conversations (old app was in-memory-only per browser session), a visible
  agent-transparency/trace panel (old app had none), and a restricted-exec
  sandbox for LLM-authored code (old app used unrestricted `exec()` with
  `allow_dangerous_code=True`).
- The full brief's harness (evals with LLM-as-judge, adversarial set, CI
  scorecards), self-hosted tracing viewer, and Next.js UI are real gaps
  against the brief's "definition of done," tracked explicitly in
  `docs/FUTURE.md` rather than silently declared out of scope.
