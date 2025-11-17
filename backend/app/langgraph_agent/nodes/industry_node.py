# backend/app/langgraph_agent/nodes/industry_node.py
from langgraph import Node

def create_industry_node():
    def process(input_text, state):
        # Placeholder for industry selection logic
        state['selected_industry'] = input_text
        return f"You selected the industry: {input_text}"
    return Node(name="industry_node", process=process)