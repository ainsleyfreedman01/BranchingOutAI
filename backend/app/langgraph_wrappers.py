"""Wrappers that adapt existing nodes to a LangGraph-friendly interface.

These wrappers are minimal and only expose a `run(state, session_id)`
method that delegates to the original node's `process` function. They are
safe to import even when `langgraph` is not installed.
"""
from typing import Any, Dict, Optional


class LangGraphNodeWrapper:
    """Wrap a node to expose `run(state, session_id)`.

    The underlying node is expected to implement `process(user_input, state, session_id)`.
    """

    def __init__(self, node: Any, name: Optional[str] = None):
        self.node = node
        self.name = name or getattr(node, "__class__", type(node)).__name__

    def run(self, state: Dict[str, Any], session_id: Optional[str] = None):
        user_input = state.get("user_input", "")
        try:
            res = self.node.process(user_input=user_input, state=state, session_id=session_id)
        except TypeError:
            res = self.node.process(user_input, state)
        if isinstance(res, tuple) and len(res) == 2:
            return res
        return (res, state)

    def __repr__(self):
        return f"<LangGraphNodeWrapper name={self.name}>"
