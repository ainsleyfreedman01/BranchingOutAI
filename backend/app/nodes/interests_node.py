# backend/app/langgraph_agent/nodes/interests_node.py
from app.config import client
from app.state_manager import save_state, get_state

class InterestsNode:
    def process(self, user_input, state, session_id=None):
        """Process user interests to suggest industries.

        Args:
            self: InterestsNode instance.
            user_input (str): The user's stated interests.
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.
        """
        # If session_id provided, prefer latest saved state from Supabase
        if session_id:
            saved = get_state(session_id)
            if isinstance(saved, dict):
                state = saved
        state = state or {}

        # Save user interests
        state["interests"] = user_input

        # Ask OpenAI for 2-3 industries
        response = client.chat(
            messages=[
                {"role": "system", "content": "You are a career exploration AI."},
                {"role": "user", "content": f"The user is interested in: {user_input}. Suggest 2-3 broad industries. Return JSON list only."}
            ]
        )

        state["industries"] = response

        # Save to Supabase
        if session_id:
            save_state(session_id, state)

        return "Here are some industries you might explore.", state