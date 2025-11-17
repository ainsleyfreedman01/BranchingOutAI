# backend/app/langgraph_agent/nodes/skills_node.py
from langgraph import Node

def create_skills_node():
    def process(input_text, state):
        # Placeholder for skills selection logic
        state['selected_skills'] = input_text
        return f"You selected the skills: {input_text}"
    return Node(name="skills_node", process=process)