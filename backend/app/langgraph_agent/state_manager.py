# backend/app/langgraph_agent/state_manager.py
class StateManager:
    """
    Simple class to track user conversation state and selections.
    """
    def __init__(self):
        self.user_state = {}

    def get_state(self, user_id):
        return self.user_state.get(user_id, {})

    def update_state(self, user_id, updates: dict):
        if user_id not in self.user_state:
            self.user_state[user_id] = {}
        self.user_state[user_id].update(updates)
        return self.user_state[user_id]