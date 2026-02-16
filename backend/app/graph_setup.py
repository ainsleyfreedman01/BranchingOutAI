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
from app.langchain_adapter import create_graph_runner


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
        # Create a default sequential runner over all nodes (used by shim)
        self._runner = create_graph_runner(list(self._nodes_map.values()) )

    def step(self, state: Dict[str, Any], session_id: str = None):
        """Decide next node via RouterNode and execute it.

        For compatibility we still use RouterNode to make the decision which
        single node to run next. When running an individual node, call its
        `process` method directly so behavior is unchanged.
        """
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