# backend/app/langgraph_agent/nodes/interests_node.py
from langgraph import Node

def create_interests_node():
    """
    This node prompts the user for their interests.
    """
    def process(input_text, state):
        # Placeholder logic for now
        # 'state' will eventually store user selections
        state['interests'] = input_text
        return f"Got it! You’re interested in: {input_text}"

    return Node(name="interests_node", process=process)