"""Adapter to run the existing node graph via LangChain/LangGraph if available.

This module attempts to import LangChain/LangGraph primitives. If the
library is not installed in the environment, it falls back to a small
shim that preserves the existing node semantics (calling node.process).

The goal is to make the codebase compatible with LangChain-style graphs
without changing node implementations or public behavior.
"""
from typing import Any, Dict, Iterable, Optional
from app.langchain_wrappers import LangChainNodeWrapper

try:
    # Prefer an actual LangChain / LangGraph implementation when available.
    # Keep imports optional to avoid a hard dependency in development.
    from langchain.graphs import Graph
    _HAS_LANGCHAIN = True
except Exception:
    Graph = None  # type: ignore
    _HAS_LANGCHAIN = False


class LangChainShim:
    """A minimal shim that runs a sequence of nodes in order.

    It exposes a `run` method with a similar shape to what a LangGraph
    runner might provide: takes an initial state and returns (output, state).
    """

    def __init__(self, nodes: Iterable[Any]):
        # nodes: iterable of objects with `process(user_input, state, session_id)`
        self.nodes = list(nodes)

    def run(self, state: Dict[str, Any], session_id: Optional[str] = None):
        output = None
        for node in self.nodes:
            user_input = state.get("user_input", "")
            try:
                out, state = node.process(user_input, state, session_id=session_id)
                output = out
            except TypeError:
                # Some nodes may have alternate signatures; try a safe call
                res = node.process(user_input, state)
                if isinstance(res, tuple) and len(res) == 2:
                    output, state = res
                else:
                    output = res
        return output, state


def create_graph_runner(nodes: Iterable[Any]):
    """Return a runner that exposes `run(state, session_id)`.

    If LangChain is available, a Graph-based runner would be returned.
    Otherwise the lightweight shim is used.
    """
    if _HAS_LANGCHAIN and Graph is not None:
        # Wrap nodes so the Graph receives objects with a consistent interface
        wrapped = [LangChainNodeWrapper(n, name=getattr(n, "__class__", type(n)).__name__) for n in nodes]
        try:
            g = Graph(wrapped)
            # Annotate so callers can detect a real LangChain runner
            try:
                setattr(g, "_uses_langchain", True)
            except Exception:
                pass
            return g
        except Exception:
            # Fall back to shim if constructing Graph fails
            shim = LangChainShim(nodes)
            shim._uses_langchain = False
            return shim
    shim = LangChainShim(nodes)
    shim._uses_langchain = False
    return shim
