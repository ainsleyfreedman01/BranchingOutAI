# backend/app/langgraph_agent/nodes/job_node.py
from app.config import client
from app.state_manager import save_state, get_state

class JobNode:
    def process(self, user_input, state, session_id=None, use_live_jobs=False):
        """Process selected job family to suggest specific jobs.

        Args:
            self: JobNode instance.
            user_input (str): The user's selected job family.
            state (dict): The current session state.
            session_id (str, optional): The user's session ID for state saving.
            use_live_jobs (bool, optional): Whether to use live job data from TheirStack API.
        """
        # Load saved state if session id provided
        if session_id:
            saved = get_state(session_id)
            if isinstance(saved, dict):
                merged = dict(saved)
                merged.update(state or {})
                state = merged
        state = state or {}

        state["selected_job_family"] = user_input

        if use_live_jobs:
            # Placeholder for TheirStack API
            jobs = ["Job1", "Job2", "Job3"]
        else:
            response = client.chat(
                messages=[
                    {"role": "system", "content": "You suggest specific job titles."},
                    {"role": "user", "content": f"Job family: {user_input}. Suggest 3-4 job titles. Return JSON list only."}
                ]
            )
            jobs = response

        state["jobs"] = jobs

        if session_id:
            save_state(session_id, state)

        return "Here are some jobs you might explore.", state