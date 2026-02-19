# backend/app/graph_setup.py
"""Lightweight AgentGraph compatible with the node `process` signatures.

This avoids depending on the external `langgraph` package and provides a
simple `agent_graph.step(state, session_id)` method used by `app.main`.
"""

from typing import Dict, Any
from app.nodes.interests_node import InterestsNode
from app.nodes.industry_node import IndustryNode
from app.nodes.job_node import JobNode
from app.nodes.skills_node import SkillsNode
from app.nodes.agent_node import RouterNode
try:
    # Prefer LangGraph adapter when available
    from app.langgraph_adapter import create_graph_runner as create_langgraph_runner
    _HAS_LANGGRAPH_ADAPTER = True
except Exception:
    create_langgraph_runner = None
    _HAS_LANGGRAPH_ADAPTER = False

from app.langchain_adapter import create_graph_runner as create_langchain_runner


class AgentGraph:
    """AgentGraph compatible with both the legacy node runner and LangChain.

    This class builds a sequence of nodes and exposes a `step` method that
    runs the graph. When LangChain/LangGraph is available, the adapter will
    produce a Graph-like runner; otherwise we use a local shim that keeps
    calling `node.process(...)` in order.
    """

    def __init__(self):
        self.router = RouterNode()
        # Keep node instances the same as before
        self._nodes_map = {
            "interests_node": InterestsNode(),
            "industry_node": IndustryNode(),
            "job_node": JobNode(),
            "skills_node": SkillsNode(),
        }
        # Create a default sequential runner over all nodes (used by shim).
        # Prefer LangGraph adapter if present, else fall back to LangChain adapter.
        if _HAS_LANGGRAPH_ADAPTER and create_langgraph_runner is not None:
            self._runner = create_langgraph_runner(list(self._nodes_map.values()))
        else:
            self._runner = create_langchain_runner(list(self._nodes_map.values()))

    def step(self, state: Dict[str, Any], session_id: str = None):
        """Decide next node via RouterNode and execute it.

        For compatibility we still use RouterNode to make the decision which
        single node to run next. When running an individual node, call its
        `process` method directly so behavior is unchanged.
        """
        # If we constructed a real LangChain runner, prefer to run the
        # graph runner which can manage orchestration end-to-end.
        runner = getattr(self, "_runner", None)
        if runner is not None and getattr(runner, "_uses_langchain", False):
            # The Graph/runner is expected to accept the state and return
            # (output, state) or similar. We call run with the session id
            # when supported.
            try:
                # Some Graph implementations accept a dict and return (out, state)
                return runner.run(state, session_id=session_id)
            except TypeError:
                # Fallback to calling run(state) if session_id not supported
                return runner.run(state)
            except Exception:
                # If the langchain runner fails for any reason, fall back to
                # the legacy RouterNode + node.process flow.
                pass

        # Legacy, fine-grained behavior: use RouterNode to pick the next node
        next_name = self.router.process(state)
        if next_name == "END":
            return "Session complete.", state

        node = self._nodes_map.get(next_name)
        if node is None:
            return "No node found.", state

        user_input = state.get("user_input", "")
        output, updated_state = node.process(user_input, state, session_id=session_id)
        return output, updated_state


agent_graph = AgentGraph()