# backend/app/langgraph_agent/state_manager.py
class StateManager:
    """Manages user session states."""
    def __init__(self):
        """Initializes the state manager with an empty session store."""
        self.sessions = {}

    def get_state(self, session_id):
        """Retrieves the state for a given session ID."""
        return self.sessions.get(session_id, {})

    def save_state(self, session_id, state):
        """Saves the state for a given session ID."""
        self.sessions[session_id] = state

state_manager = StateManager()