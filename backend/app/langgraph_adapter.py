"""Adapter to run existing nodes via LangGraph if available.

This mirrors the pattern used for LangChain: attempt to import LangGraph
types if present and build a Graph runner. If LangGraph isn't installed
or construction fails, fall back to a lightweight shim that sequentially
executes node.process(...).
"""
from typing import Any, Dict, Iterable, Optional
from app.langgraph_wrappers import LangGraphNodeWrapper

try:
    import langgraph
    # Try to find a Graph-like constructor
    Graph = getattr(langgraph, "Graph", None) or getattr(langgraph, "LangGraph", None)
    _HAS_LANGGRAPH = Graph is not None
except Exception:
    Graph = None  # type: ignore
    _HAS_LANGGRAPH = False


class LangGraphShim:
    """Minimal shim that runs nodes sequentially and exposes `run(state, session_id)`.

    This ensures the rest of the codebase can interact with a Graph-like
    runner without requiring LangGraph to be installed.
    """

    def __init__(self, nodes: Iterable[Any]):
        self.nodes = list(nodes)

    def run(self, state: Dict[str, Any], session_id: Optional[str] = None):
        output = None
        for node in self.nodes:
            user_input = state.get("user_input", "")
            try:
                out, state = node.process(user_input, state, session_id=session_id)
                output = out
            except TypeError:
                res = node.process(user_input, state)
                if isinstance(res, tuple) and len(res) == 2:
                    output, state = res
                else:
                    output = res
        return output, state


def create_graph_runner(nodes: Iterable[Any]):
    """Return a runner that exposes `run(state, session_id)`.

    If LangGraph is installed and a Graph can be constructed, return it.
    Otherwise return the shim.
    """
    if _HAS_LANGGRAPH and Graph is not None:
        wrapped = [LangGraphNodeWrapper(n, name=getattr(n, "__class__", type(n)).__name__) for n in nodes]
        try:
            g = Graph(wrapped)
            try:
                setattr(g, "_uses_langgraph", True)
            except Exception:
                pass
            return g
        except Exception:
            shim = LangGraphShim(nodes)
            shim._uses_langgraph = False
            return shim
    shim = LangGraphShim(nodes)
    shim._uses_langgraph = False
    return shim
