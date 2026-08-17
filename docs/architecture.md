# Architecture

## Topology: one agent, two tools, no swarm

Per the brief's own guidance ("use delegation only where it measurably
improves output... if the answer is 'one agent with good tools,' say so and
ship that"): there is exactly one agent. No router/triage agent, no
sub-agents, no critic pass — the task (answer a question about one uploaded
CSV, or plot from it) doesn't have distinct sub-domains that would benefit
from delegation, and adding one would only add latency and failure surface.

## Request flow

```
┌─────────────────┐        st.chat_input          ┌──────────────────────────┐
│   Streamlit UI   │ ─────────────────────────────▶│   agent.graph.run_turn   │
│   (src/app.py)   │                                │                          │
│                   │◀─── AgentState (messages,     │  1. opens stdio MCP      │
│  - sidebar        │      tool results, trace) ────│     session to           │
│  - message list   │                                │     tools_server.py     │
│  - transparency    │                                │  2. loads MCP tools as  │
│    panel           │                                │     LangChain tools     │
│  - trace panel      │                                │  3. builds a 2-node     │
└─────────────────┘                                │     LangGraph:           │
        │                                            │       agent ⇄ tools     │
        │ reads/writes                               │  4. runs to completion, │
        ▼                                            │     checkpointing every │
┌─────────────────┐                                │     step to SQLite       │
│ data/checkpoints │◀───────────────────────────────│  5. closes MCP session   │
│    .sqlite       │        SqliteSaver             └──────────────────────────┘
└─────────────────┘                                              │
        ▲                                                        │ stdio subprocess
        │ get_history(thread_id)                                 ▼
        │ (resume on reload)                          ┌──────────────────────────┐
        │                                              │  agent/tools_server.py  │
┌─────────────────┐                                  │  (MCP server, FastMCP)  │
│  URL: ?thread=…  │                                  │                          │
└─────────────────┘                                  │  run_pandas_query(code)  │
                                                       │  render_plot(code)      │
data/traces.jsonl ◀────── Tracer.record_model_call ── │  both: exec() in a      │
        │                  (one span per Claude call)  │  restricted-builtins    │
        ▼                                              │  sandbox against the    │
  read by render_trace_panel()                         │  uploaded CSV           │
                                                        └──────────────────────────┘
```

## The graph itself

Two nodes, conditionally looped:

```
        START
          │
          ▼
    ┌───────────┐   has pending    ┌───────────┐
    │   agent   │──tool_calls?────▶│   tools   │
    │ (Claude)  │                  │ (MCP-backed)
    └───────────┘◀─────────────────└───────────┘
          │  no tool_calls
          ▼
         END
```

- `agent` node (`agent/graph.py::_call_model`) builds the prompt from a
  mode-dependent system message + a windowed slice of prior turns (the
  "memory window" control), calls Claude, and records a trace span.
- `tools` node is LangGraph's prebuilt `ToolNode`, wired directly to the
  MCP-loaded tool objects — no custom dispatch code.
- In `general_chat` mode, no tools are bound at all, so the graph is just
  `agent → END`; there's nothing to route.

## State

`agent/state.py::AgentState` — a `TypedDict` with `messages` (reduced via
LangGraph's `add_messages`, so partial updates from each node merge instead of
overwrite), `csv_path`, `dataframe_columns`, `dataframe_shape`, and `mode`.
This is the full "working memory" tier from the brief's context-engineering
section; episodic/semantic memory tiers were out of scope for this app (there
was never a multi-conversation user-facing memory feature to preserve) — noted
in `docs/FUTURE.md` as a possible addition, not a parity gap.

## Why not more topology

A retrieval/RAG layer, generative UI components beyond a rendered chart, and
voice were all evaluated against the brief's explicit rule ("if the current
app has no voice, do not add it") and the old app's actual feature set — none
of the old app's features imply any of these, so none were added.
