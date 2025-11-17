# backend/app/langgraph_agent/nodes/job_node.py
from langgraph import Node

def create_job_node():
    def process(input_text, state):
        # Placeholder for job selection logic
        state['selected_job'] = input_text
        return f"You selected the job: {input_text}"
    return Node(name="job_node", process=process)