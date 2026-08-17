"""LangGraph agent: routes each turn through Claude, executing MCP-backed
pandas/plot tools as needed, with SQLite checkpointing for durable, resumable runs.

Each turn opens a fresh stdio connection to `tools_server.py`, loads its tools,
runs the graph to completion inside that connection, then closes it. Keeping a
long-lived MCP session across Streamlit reruns would be a nice follow-up (see
docs/FUTURE.md) but reconnecting per turn is simpler and correctness-first for
this scope.
"""
import os
import sys
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent.state import AgentState
from agent.tracing import Tracer

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_AGENT_DIR)
_REPO_ROOT = os.path.dirname(_SRC_DIR)
CHECKPOINT_DB = os.path.join(_REPO_ROOT, "data", "checkpoints.sqlite")

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "agent.tools_server"],
    cwd=_SRC_DIR,
)


def _system_prompt(state: AgentState) -> str:
    if state["mode"] == "data_explorer" and state.get("dataframe_columns"):
        return (
            "You are a careful data analyst. A CSV is loaded with columns: "
            f"{state['dataframe_columns']} and shape {state['dataframe_shape']}. "
            f"Its file path is `{state['csv_path']}`. "
            "Use the `run_pandas_query` tool to answer questions about the data "
            "(write pandas code that assigns its answer to a variable named "
            "`result`), and the `render_plot` tool whenever the user asks for a "
            "plot, chart, graph, or visualization (write plotly code using `px`/"
            "`go` that assigns a Figure to a variable named `fig`). Never "
            "fabricate numbers you have not computed with a tool call."
        )
    return (
        "You are a helpful, concise chat assistant. No dataset is loaded right "
        "now, so you have no data-query or plotting tools available — if asked "
        "to analyze or plot data, say a CSV needs to be uploaded first."
    )


def _has_pending_tool_calls(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


# The claude-*-5 flagship models run with extended thinking always on and
# reject `temperature`/`top_p` entirely (HTTP 400 "deprecated for this
# model"); claude-haiku-4-5 accepts one or the other but not both at once.
# Confirmed live against the Anthropic API on 2026-08-17 — see
# docs/PARITY.md item #4/#6 and README troubleshooting.
_NO_SAMPLING_PARAMS_MODELS = {"claude-sonnet-5", "claude-opus-5", "claude-fable-5"}


def _sampling_kwargs(model_name: str, temperature: float) -> dict:
    if model_name in _NO_SAMPLING_PARAMS_MODELS:
        return {}
    return {"temperature": temperature}


async def _call_model(state: AgentState, model, tracer: Tracer, memory_window: int) -> dict:
    system = SystemMessage(content=_system_prompt(state))
    history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    window = history[-(2 * memory_window):] if memory_window else history
    start = time.time()
    response = await model.ainvoke([system] + window)
    tracer.record_model_call(response, latency_ms=(time.time() - start) * 1000)
    return {"messages": [response]}


async def run_turn(
    state: AgentState,
    *,
    model_name: str,
    temperature: float,
    max_tokens: int,
    thread_id: str,
    tracer: Tracer,
    memory_window: int = 3,
) -> AgentState:
    """Runs one full agent turn (model -> tools -> model -> ... -> answer)."""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session) if state["mode"] == "data_explorer" else []

            model = ChatAnthropic(
                model=model_name, max_tokens=max_tokens,
                **_sampling_kwargs(model_name, temperature),
            )
            bound_model = model.bind_tools(tools) if tools else model

            graph = StateGraph(AgentState)

            async def _agent_node(s: AgentState) -> dict:
                return await _call_model(s, bound_model, tracer, memory_window)

            graph.add_node("agent", _agent_node)
            graph.add_edge(START, "agent")
            if tools:
                graph.add_node("tools", ToolNode(tools))
                graph.add_conditional_edges(
                    "agent", _has_pending_tool_calls, {"tools": "tools", END: END}
                )
                graph.add_edge("tools", "agent")
            else:
                graph.add_edge("agent", END)

            async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
                compiled = graph.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                result = await compiled.ainvoke(state, config=config)
            return result


def get_history(thread_id: str) -> list:
    """Reads persisted conversation history for a thread without invoking the agent.

    Backs conversation resumability: reopening the app with the same thread_id
    (carried in the URL query string, see ui side of app.py) replays this.
    """
    graph = StateGraph(AgentState)

    async def _noop(_state: AgentState) -> dict:
        return {}

    graph.add_node("agent", _noop)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)

    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = compiled.get_state(config)
        if snapshot and snapshot.values:
            return snapshot.values.get("messages", [])
    return []
