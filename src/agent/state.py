"""Typed state threaded through every node of the data-analyst agent graph."""
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    csv_path: Optional[str]
    dataframe_columns: list[str]
    dataframe_shape: Optional[tuple]
    mode: str  # "data_explorer" | "general_chat"
