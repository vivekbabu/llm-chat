"""Sidebar controls: mode, model, sampling parameters, and memory window.

Model list is Claude-only per the explicit instruction to move off OpenAI (see
docs/ADR-001-agent-runtime.md). Sampling controls are more restricted than the
old OpenAI-shaped 0-2 temperature/top_p sliders — confirmed live against the
Anthropic API: the claude-*-5 flagship models run with extended thinking
always on and reject temperature/top_p entirely (HTTP 400), and
claude-haiku-4-5 accepts one or the other but never both at once. See
docs/PARITY.md item #4/#6 and `agent/graph.py::_sampling_kwargs`.
"""
import streamlit as st

CLAUDE_MODELS = {
    "claude-sonnet-5": 200_000,
    "claude-opus-5": 200_000,
    "claude-fable-5": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
}

NO_SAMPLING_PARAMS_MODELS = {"claude-sonnet-5", "claude-opus-5", "claude-fable-5"}


def sidebar() -> dict:
    with st.sidebar:
        st.markdown("### Settings")
        mode_label = st.radio(
            "Mode",
            ["Data Explorer", "General Chat"],
            help=(
                "Data Explorer requires a CSV and can query/plot it with tools. "
                "General Chat is a plain assistant with no data tools — this "
                "folds in the old app's separate, unreachable generic-chat mode."
            ),
        )
        mode = "data_explorer" if mode_label == "Data Explorer" else "general_chat"

        model = st.selectbox("Model", options=list(CLAUDE_MODELS), index=0)
        supports_temperature = model not in NO_SAMPLING_PARAMS_MODELS
        temperature = st.slider(
            "Temperature", 0.0, 1.0, 0.2, 0.01,
            disabled=not supports_temperature,
            help=(
                "Controls randomness (Anthropic's range is 0-1)."
                if supports_temperature else
                "Not adjustable for this model — it always runs with extended "
                "thinking enabled, which locks out sampling parameters."
            ),
        )
        max_tokens = st.slider(
            "Max tokens", 256, min(CLAUDE_MODELS[model], 8192), 4096, 64
        )
        st.slider(
            "Top P", 0.0, 1.0, 0.5, 0.01, disabled=True,
            help=(
                "Disabled: Anthropic's API rejects setting temperature and "
                "top_p at once, so this app always drives sampling with "
                "temperature instead."
            ),
        )
        memory_window = st.slider(
            "Memory window",
            value=3, min_value=1, max_value=10, step=1,
            help=(
                "Number of past user/assistant turn pairs kept in the prompt "
                "sent to the model. Older turns stay visible in the transcript "
                "but stop influencing new answers — same windowing strategy as "
                "the old app, applied at prompt-build time instead of by "
                "deleting from history (see docs/PARITY.md item #7)."
            ),
        )

        st.divider()
        thread_id = st.session_state.get("thread_id", "")
        with st.expander("Conversation", expanded=False):
            st.caption(f"Thread ID: `{thread_id[:8]}…`" if thread_id else "Thread ID: —")
            st.caption(
                "This conversation is durably checkpointed to a local SQLite "
                "file — refreshing this exact URL resumes it."
            )

        return {
            "mode": mode,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "memory_window": memory_window,
        }
