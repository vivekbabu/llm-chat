"""Local MCP server exposing sandboxed pandas/plotly tools for the data-analyst agent.

Launched as a stdio subprocess by the agent graph (see `graph.py`'s SERVER_PARAMS) for
each turn — no network exposure, no new persistent service. See
docs/ADR-001-agent-runtime.md for why this stays a local subprocess rather than a
hosted MCP service.

Both tools exec LLM-authored code, but only against a restricted builtins/globals
dict (no `import`, `open`, `os`, `__import__`, ...) — a real, if not bulletproof,
security improvement over the old app's unrestricted `exec()` of LLM output.
"""
import builtins

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("data-analyst-tools")

_ALLOWED_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "int", "len", "list", "map", "max", "min", "range", "round", "set",
    "sorted", "str", "sum", "tuple", "zip",
)
_SAFE_BUILTINS = {name: getattr(builtins, name) for name in _ALLOWED_BUILTIN_NAMES}


def _restricted_globals(df: pd.DataFrame, *, plotting: bool) -> dict:
    scope = {"__builtins__": _SAFE_BUILTINS, "df": df, "pd": pd}
    if plotting:
        scope["px"] = px
        scope["go"] = go
    return scope


def run_pandas_query(csv_path: str, code: str) -> str:
    """Execute pandas code against the uploaded dataframe and return the result.

    `code` must be a Python snippet that ends by assigning its answer to a
    variable named `result` (e.g. `result = df.groupby("Continent")["2022 Population"].sum()`).
    Only `df` and `pd` are available in scope — no filesystem, network, or import access.
    """
    df = pd.read_csv(csv_path)
    scope = _restricted_globals(df, plotting=False)
    try:
        exec(code, scope)  # noqa: S102 - restricted globals, no builtins/imports
    except Exception as exc:  # surfaced back to the agent, never raised to the process
        return f"ERROR executing pandas code: {exc}"
    result = scope.get("result")
    if result is None:
        return "ERROR: code did not assign a `result` variable."
    return str(result)[:4000]


def render_plot(csv_path: str, code: str) -> str:
    """Execute Plotly code against the uploaded dataframe and return a chart spec.

    `code` must build a `plotly.graph_objects.Figure` and assign it to `fig`,
    using `df`, `pd`, `px`, and `go` — no other imports or filesystem access.
    Returns the figure serialized as Plotly JSON for the UI to render.
    """
    df = pd.read_csv(csv_path)
    scope = _restricted_globals(df, plotting=True)
    try:
        exec(code, scope)  # noqa: S102 - restricted globals, no builtins/imports
    except Exception as exc:
        return f"ERROR executing plot code: {exc}"
    fig = scope.get("fig")
    if fig is None or not isinstance(fig, go.Figure):
        return "ERROR: code did not assign a plotly.graph_objects.Figure to `fig`."
    return fig.to_json()


mcp.tool()(run_pandas_query)
mcp.tool()(render_plot)


if __name__ == "__main__":
    mcp.run(transport="stdio")
