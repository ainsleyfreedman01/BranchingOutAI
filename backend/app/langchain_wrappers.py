"""Wrappers that adapt existing node objects to a lightweight LangChain-style runner.

These wrappers are intentionally minimal: they provide a `run(state, session_id)`
method that delegates to the original node's `process(user_input, state, session_id)`
signature. The adapter will use these wrappers when attempting to build a real
LangChain `Graph` so the Graph receives objects with a reasonably consistent
interface.

The wrappers do not depend on the `langchain` package to be installed — they
simply provide a stable adapter layer and are safe to import in any environment.
"""
from typing import Any, Dict, Optional


class LangChainNodeWrapper:
    """Wrap a node so it exposes a `run(state, session_id)` method.

    The underlying node is expected to implement `process(user_input, state, session_id)`.
    """

    def __init__(self, node: Any, name: Optional[str] = None):
        self.node = node
        self.name = name or getattr(node, "__class__", type(node)).__name__

    def run(self, state: Dict[str, Any], session_id: Optional[str] = None):
        """Run the wrapped node and return (output, updated_state).

        This method matches the simple contract the adapter expects from a
        Graph node runner: accept a state dict and optional session id and
        return a tuple of (output_text, state).
        """
        user_input = state.get("user_input", "")
        try:
            res = self.node.process(user_input=user_input, state=state, session_id=session_id)
        except TypeError:
            # Some nodes may not accept session_id param
            res = self.node.process(user_input, state)
        # Normalize return shape
        if isinstance(res, tuple) and len(res) == 2:
            return res
        return (res, state)

    # Provide a readable repr for logging/inspection
    def __repr__(self):
        return f"<LangChainNodeWrapper name={self.name}>"
