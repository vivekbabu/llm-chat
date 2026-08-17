"""Data Explorer — an agentic chat app for querying and plotting a CSV, backed
by a LangGraph agent (Claude + MCP tools) with durable, resumable conversations.

Run: streamlit run src/app.py
"""
import asyncio
import os
import uuid

import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage

from agent.graph import get_history, run_turn
from agent.state import AgentState
from agent.tracing import Tracer
from config import require_api_key
from ui.components import render_messages, render_trace_panel
from ui.sidebar import sidebar
from ui.theme import inject as inject_theme

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
SAMPLE_CSV = os.path.join(_REPO_ROOT, "data", "world_population.csv")
UPLOAD_DIR = os.path.join(_REPO_ROOT, "data", "uploads")


def _ensure_thread_id() -> str:
    thread_id = st.query_params.get("thread")
    if not thread_id:
        thread_id = uuid.uuid4().hex
        st.query_params["thread"] = thread_id
    return thread_id


def _load_dataframe(uploaded_file, use_sample: bool) -> tuple:
    if uploaded_file is not None:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        path = os.path.join(UPLOAD_DIR, f"{st.session_state['thread_id']}.csv")
        with open(path, "wb") as f:
            f.write(uploaded_file.getvalue())
        return pd.read_csv(path), path
    if use_sample:
        return pd.read_csv(SAMPLE_CSV), SAMPLE_CSV
    return pd.DataFrame(), None


def main() -> None:
    st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="centered")
    inject_theme()

    try:
        require_api_key()
    except RuntimeError as exc:
        st.title("🔍 Data Explorer")
        st.error(str(exc), icon="🔑")
        st.stop()

    st.title("🔍 Data Explorer")
    st.caption("An agentic chat for your data — Claude + LangGraph + MCP tools.")

    if "thread_id" not in st.session_state:
        st.session_state["thread_id"] = _ensure_thread_id()
    thread_id = st.session_state["thread_id"]

    model_params = sidebar()
    mode = model_params["mode"]

    df, csv_path = pd.DataFrame(), None
    if mode == "data_explorer":
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("Upload a CSV", type=["csv"])
        with col2:
            st.write("")
            st.write("")
            sample_clicked = st.button("Load sample data", use_container_width=True)
        if sample_clicked:
            st.session_state["use_sample"] = True
        if uploaded_file is not None:
            st.session_state["use_sample"] = False
        df, csv_path = _load_dataframe(uploaded_file, st.session_state.get("use_sample", False))
        if not df.empty:
            st.dataframe(df.head(5), use_container_width=True, height=180)

    if "history_loaded" not in st.session_state:
        st.session_state["messages"] = get_history(thread_id)
        st.session_state["history_loaded"] = True
        st.session_state["run_ids"] = {}

    render_messages(st.session_state["messages"])
    for i in range(len(st.session_state["messages"])):
        run_id = st.session_state["run_ids"].get(i)
        if run_id:
            render_trace_panel(run_id)

    user_input = st.chat_input(placeholder="Ask a question about your data…")

    if user_input and st.session_state.get("last_input") == user_input:
        user_input = None
    if user_input:
        st.session_state["last_input"] = user_input

        if mode == "data_explorer" and df.empty:
            st.warning(
                "The dataframe is empty. Please upload a valid CSV file, or "
                "load the sample dataset.",
                icon="🚫",
            )
        else:
            st.chat_message("user").write(user_input)
            input_state: AgentState = {
                "messages": [HumanMessage(content=user_input)],
                "csv_path": csv_path,
                "dataframe_columns": list(df.columns) if not df.empty else [],
                "dataframe_shape": tuple(df.shape) if not df.empty else None,
                "mode": mode,
            }
            run_id = uuid.uuid4().hex
            tracer = Tracer(run_id=run_id, thread_id=thread_id)
            try:
                with st.spinner("Thinking…"):
                    result = asyncio.run(run_turn(
                        input_state,
                        model_name=model_params["model"],
                        temperature=model_params["temperature"],
                        max_tokens=model_params["max_tokens"],
                        thread_id=thread_id,
                        tracer=tracer,
                        memory_window=model_params["memory_window"],
                    ))
                new_messages = result["messages"][len(st.session_state["messages"]):]
                render_messages(new_messages)
                render_trace_panel(run_id)
                st.session_state["run_ids"][len(result["messages"]) - 1] = run_id
                st.session_state["messages"] = result["messages"]
            except Exception as exc:
                debug = os.environ.get("DEBUG")
                error_message = (
                    f"Error: {exc}" if debug else
                    "Something went wrong running the agent. Please refine your query and try again."
                )
                st.chat_message("assistant").warning(error_message, icon="⚠️")


if __name__ == "__main__":
    main()
