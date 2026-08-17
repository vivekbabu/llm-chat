"""Minimal CSS polish for the chat surface — spacing, message bubbles, and the
agent-transparency panel. Kept intentionally light: Streamlit's built-in
light/dark toggle (see .streamlit/config.toml for the base palette) already
handles theming; this only layers spacing/typography on top of it.
"""
import streamlit as st

_CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 880px; }
[data-testid="stChatMessage"] { padding: 0.9rem 1.1rem; border-radius: 14px; margin-bottom: 0.4rem; }
.stChatInput textarea { border-radius: 12px !important; }
h1 { font-weight: 650; letter-spacing: -0.02em; }
[data-testid="stExpander"] { border-radius: 10px; }
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
