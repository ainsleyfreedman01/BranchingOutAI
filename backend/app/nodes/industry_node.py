# backend/app/langgraph_agent/nodes/industry_node.py
from app.config import client
from app.state_manager import save_state

class IndustryNode:
    def process(self, user_input, state, session_id=None):
        """Process selected industry to suggest job families.

        Args:
            self: IndustryNode instance.
            user_input (str): The user's selected industry.
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.
        """
        state["selected_industry"] = user_input

        # Ask OpenAI for 2–3 job families
        response = client.chat(
            messages=[
                {"role": "system", "content": "You suggest job families in an industry."},
                {"role": "user", "content": f"Industry: {user_input}. Suggest 2-3 job families. Return JSON list only."}
            ]
        )

        state["job_families"] = response

        # Save to Supabase
        if session_id:
            save_state(session_id, state)

        return "Here are some job families in this industry.", state