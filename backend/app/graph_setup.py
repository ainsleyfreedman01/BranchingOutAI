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


class AgentGraph:
    def __init__(self):
        self.router = RouterNode()
        self.nodes = {
            "interests_node": InterestsNode(),
            "industry_node": IndustryNode(),
            "job_node": JobNode(),
            "skills_node": SkillsNode(),
        }

    def step(self, state: Dict[str, Any], session_id: str = None):
        """Run a single step of the agent: decide next node and invoke it.
        
        Args:
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.

        Returns (output_text, updated_state).
        """
        next_name = self.router.process(state)
        if next_name == "END":
            return "Session complete.", state

        node = self.nodes.get(next_name)
        if node is None:
            return "No node found.", state

        user_input = state.get("user_input", "")
        # Node.process returns (output, state)
        output, updated_state = node.process(user_input, state, session_id=session_id)
        return output, updated_state


agent_graph = AgentGraph()