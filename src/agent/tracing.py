"""Lightweight local tracing: JSONL spans with GenAI-ish field names.

No external tracing service is stood up here — see docs/ADR-001-agent-runtime.md
for why self-hosting Langfuse/an OTel collector was deferred for this scope. The
UI's agent-transparency panel (`ui/components.py::render_trace_panel`) reads this
file to show per-message model latency/token/cost detail; the tool-call timeline
itself is reconstructed straight from the LangGraph message list, not from here.
"""
import json
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
TRACE_LOG = os.path.join(_REPO_ROOT, "data", "traces.jsonl")


class Tracer:
    def __init__(self, run_id: str, thread_id: str):
        self.run_id = run_id
        self.thread_id = thread_id

    def _emit(self, span: dict) -> None:
        span.update(run_id=self.run_id, thread_id=self.thread_id, ts=time.time())
        os.makedirs(os.path.dirname(TRACE_LOG), exist_ok=True)
        with open(TRACE_LOG, "a") as f:
            f.write(json.dumps(span, default=str) + "\n")

    def record_model_call(self, response, *, latency_ms: float) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        tool_calls = getattr(response, "tool_calls", None) or []
        self._emit({
            "kind": "model_call",
            "model": (getattr(response, "response_metadata", {}) or {}).get("model"),
            "tokens_in": usage.get("input_tokens"),
            "tokens_out": usage.get("output_tokens"),
            "latency_ms": round(latency_ms, 1),
            "tool_calls": [tc.get("name") for tc in tool_calls],
        })


def read_spans(run_id: str) -> list:
    if not os.path.exists(TRACE_LOG):
        return []
    spans = []
    with open(TRACE_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                span = json.loads(line)
            except json.JSONDecodeError:
                continue
            if span.get("run_id") == run_id:
                spans.append(span)
    return spans
