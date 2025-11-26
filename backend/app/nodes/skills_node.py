# backend/app/langgraph_agent/nodes/skills_node.py
from app.config import client
from app.state_manager import save_state, get_state

class SkillsNode:
    def process(self, user_input, state, session_id=None):
        """Process selected job to suggest skills.

        Args:
            self: SkillsNode instance.
            user_input (str): The user's selected job title.
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.
        """
        # Load saved state when possible
        if session_id:
            saved = get_state(session_id)
            if isinstance(saved, dict):
                    merged = dict(saved)
                    merged.update(state or {})
                    state = merged
        state = state or {}

        state["selected_job"] = user_input

        response = client.chat(
            messages=[
                {"role": "system", "content": "You provide hard and soft skills for a job."},
                {"role": "user", "content": f"Job title: {user_input}. List 3-5 hard skills and 3-5 soft skills. Return JSON with keys 'hard_skills' and 'soft_skills'."}
            ]
        )

        state["skills"] = response

        if session_id:
            save_state(session_id, state)

        return "Here are the skills related to this job.", state