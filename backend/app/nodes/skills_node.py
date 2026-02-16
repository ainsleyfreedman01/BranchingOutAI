# backend/app/langgraph_agent/nodes/skills_node.py
from app.config import client
from app.state_manager import save_state, get_state
from app.utils.keywords import extract_keywords

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

        # Use extracted keywords (concise) for the selected job
        kws = extract_keywords(user_input, max_keywords=1)
        state["selected_job"] = kws[0] if kws else user_input

        response = client.chat(
            messages=[
                {"role": "system", "content": "You provide hard and soft skills for a job."},
                {"role": "user", "content": f"Job title: {state['selected_job']}. List 3-5 hard skills and 3-5 soft skills. Return JSON with keys 'hard_skills' and 'soft_skills'."}
            ]
        )

        state["skills"] = response

        if session_id:
            save_state(session_id, state)

        return "Here are the skills related to this job.", state