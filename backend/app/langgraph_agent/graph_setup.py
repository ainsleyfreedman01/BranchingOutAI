# backend/app/langgraph_agent/graph_setup.py
from langgraph import Graph
from .nodes.interests_node import create_interests_node
from .nodes.industry_node import create_industry_node
from .nodes.job_node import create_job_node
from .nodes.skills_node import create_skills_node

def setup_graph():
    graph = Graph(name="BranchingOutAI")

    # Create nodes
    interests_node = create_interests_node()
    industry_node = create_industry_node()
    job_node = create_job_node()
    skills_node = create_skills_node()

    # Connect nodes (edges)
    graph.add_node(interests_node)
    graph.add_node(industry_node)
    graph.add_node(job_node)
    graph.add_node(skills_node)

    graph.add_edge(interests_node, industry_node)
    graph.add_edge(industry_node, job_node)
    graph.add_edge(job_node, skills_node)

    return graph