# Data Explorer — Agentic Data Analyst Chat

An agentic chat app for exploring a CSV in natural language: upload a
dataset, ask questions, ask for charts. Backed by a [LangGraph](https://langchain-ai.github.io/langgraph/)
agent running on Anthropic's Claude API, calling tools over the
[Model Context Protocol](https://modelcontextprotocol.io), with durable,
resumable conversations checkpointed to SQLite.

This is a rewrite of an earlier OpenAI/LangChain-pandas-agent version of the
same app — feature parity with that version is tracked in
[`docs/PARITY.md`](docs/PARITY.md); architectural decisions in
[`docs/ADR-001-agent-runtime.md`](docs/ADR-001-agent-runtime.md); a topology
diagram in [`docs/architecture.md`](docs/architecture.md); and everything
deliberately left out of this pass in [`docs/FUTURE.md`](docs/FUTURE.md).

## 60-second quickstart

```bash
git clone <this-repo> && cd llm-chat
cp .env.example .env        # then paste your ANTHROPIC_API_KEY into .env
make install
make dev                    # opens http://localhost:8501
```

Or with Docker:

```bash
cp .env.example .env
export ANTHROPIC_API_KEY=<your-key>
docker compose up --build   # opens http://localhost:8501
```

Once it's open: pick **Data Explorer** mode in the sidebar, click **Load
sample data** (or upload your own CSV), and ask something like *"What are the
5 most populous countries in 2022?"* or *"Plot population growth rate by
continent."*

## How it works

- **Agent**: a 2-node LangGraph graph (`agent → tools → agent → ... → END`),
  typed state, checkpointed to `data/checkpoints.sqlite` per conversation
  thread. See `src/agent/graph.py`.
- **Tools**: a local MCP server (`src/agent/tools_server.py`) exposing
  `run_pandas_query` and `render_plot`, both executing LLM-authored code in a
  restricted-builtins sandbox — no filesystem/network/import access.
- **Model**: Claude, via `langchain-anthropic`. Swappable from the sidebar
  dropdown (`src/ui/sidebar.py::CLAUDE_MODELS`); swapping to a different
  provider means changing the `ChatAnthropic(...)` construction in
  `src/agent/graph.py::run_turn` — nothing else in the graph is
  provider-specific.
- **Tracing**: one JSON line per model call in `data/traces.jsonl`, viewable
  in-app via the "📊 Trace" expander under any assistant message.
- **UI**: Streamlit (`src/app.py`), with a mode toggle (Data Explorer /
  General Chat), an "🔎 Agent plan" expander showing tool calls the model made,
  and conversation resumability via the `?thread=...` URL query param.

## Adding an MCP tool

1. Add a plain Python function to `src/agent/tools_server.py`, register it
   with `mcp.tool()(your_function)`.
2. It's picked up automatically — `agent/graph.py` calls `load_mcp_tools`
   fresh each turn, so no wiring elsewhere is needed.
3. Add a test in `tests/test_tools_server.py` calling the function directly
   (no MCP/LLM round-trip needed for unit tests).

## Running tests

```bash
make test
```

Currently covers the sandboxed tool functions (`run_pandas_query`,
`render_plot`) directly — no API key required. An agent-behavior eval suite
is scoped out for now; see `docs/FUTURE.md`.

## Make targets

| Target | Does |
|---|---|
| `make install` | `pip3 install -r requirements.txt` |
| `make dev` | Runs the app (`streamlit run src/app.py`) |
| `make test` | Runs `tests/` |
| `make lint` | Runs `pyflakes` over `src/` |
| `make reset` | Deletes local checkpoints, traces, and uploaded CSVs |
| `make logs` | Tails `data/traces.jsonl` |
| `make trace` | Prints where/how to view traces |

## Troubleshooting

- **"ANTHROPIC_API_KEY is not set"** — copy `.env.example` to `.env` and fill
  in your key, or `export ANTHROPIC_API_KEY=<key>` before running.
- **Conversation didn't resume after a refresh** — resumability is tied to
  the `?thread=...` URL query parameter; make sure you're reopening the exact
  same URL Streamlit gave you, not a fresh tab.
- **"The dataframe is empty" warning in Data Explorer mode** — upload a CSV
  or click **Load sample data** before asking a question; switch to
  **General Chat** mode if you don't need a dataset.
- **Docker healthcheck failing** — give the container ~10–15s on first boot;
  `docker compose logs -f app` shows Streamlit's own startup log.

## Dependency versions

Pinned in `requirements.txt` as of August 2026: `streamlit` 1.37.1, `langgraph`
1.2.11, `langgraph-checkpoint-sqlite` 3.1.1, `langchain-anthropic` 1.5.6,
`mcp` 1.29.0, `langchain-mcp-adapters` 0.3.2. This ecosystem moves fast —
re-check for newer stable releases before assuming these are current.

## What this isn't (yet)

No token-level streaming, no eval/guardrail harness, no Postgres/Redis, no
Next.js UI, no offline/local-model profile. All deliberate, all tracked in
[`docs/FUTURE.md`](docs/FUTURE.md) — not oversights.
