# backend/app/langgraph_agent/nodes/job_node.py
from app.config import client

class JobNode:
    def process(self, user_input, state):
        """Process selected job role and explain it.
        
        Args:
            self: JobNode instance.
            user_input (str): The user's selected job role.
            state (dict): The current session state.
        """
        state["selected_job"] = user_input

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You explain job roles clearly."},
                {"role": "user", "content": f"Explain the job '{user_input}' in 3 sentences, and list 5 required skills."}
            ]
        )

        return response.choices[0].message.content, state