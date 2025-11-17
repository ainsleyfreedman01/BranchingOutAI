# backend/app/langgraph_agent/graph_setup.py
from .nodes.interests_node import InterestsNode
from .nodes.industry_node import IndustryNode
from .nodes.job_node import JobNode
from .nodes.skills_node import SkillsNode

class GraphManager:
    def __init__(self):
        """Sets up the graph nodes."""
        self.nodes = {
            "interests_node": InterestsNode(),
            "industry_node": IndustryNode(),
            "job_node": JobNode(),
            "skills_node": SkillsNode(),
        }

    def get_node(self, name):
        return self.nodes.get(name)

graph_manager = GraphManager()