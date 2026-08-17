"""Message rendering + the agent-transparency panel.

The tool-call timeline (plan -> tool call -> result -> answer) is reconstructed
straight from the LangGraph message list (AIMessage.tool_calls / ToolMessage
pairs) rather than from a separate trace store — that data is already there.
The trace panel adds what messages alone don't carry: latency and token counts
per model call, read from `agent/tracing.py`'s local JSONL log.
"""
import plotly.io as pio
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent.tracing import read_spans


def render_messages(messages: list) -> None:
    for msg in messages:
        if isinstance(msg, SystemMessage):
            continue
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        elif isinstance(msg, AIMessage):
            if msg.content:
                st.chat_message("assistant").write(msg.content)
            if msg.tool_calls:
                with st.expander("🔎 Agent plan", expanded=False):
                    for call in msg.tool_calls:
                        st.markdown(f"**Tool:** `{call['name']}`")
                        st.code(call["args"].get("code", ""), language="python")
        elif isinstance(msg, ToolMessage):
            _render_tool_result(msg)


def _render_tool_result(msg: ToolMessage) -> None:
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    is_error = content.startswith("ERROR")
    if msg.name == "render_plot" and not is_error:
        try:
            fig = pio.from_json(content)
            st.plotly_chart(fig, use_container_width=True)
            return
        except Exception:
            pass
    with st.status(
        "Execution error" if is_error else "Code executed successfully.",
        state="error" if is_error else "complete",
    ):
        st.write(content)


def render_trace_panel(run_id: str) -> None:
    spans = read_spans(run_id)
    if not spans:
        return
    with st.expander("📊 Trace", expanded=False):
        for span in spans:
            if span.get("kind") == "model_call":
                st.caption(
                    f"model=`{span.get('model')}` · "
                    f"tokens_in={span.get('tokens_in')} · tokens_out={span.get('tokens_out')} · "
                    f"latency={span.get('latency_ms')}ms · "
                    f"tools_requested={span.get('tool_calls') or '—'}"
                )
