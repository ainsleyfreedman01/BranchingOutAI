# backend/app/nodes/agent_node.py
class RouterNode:
    def process(self, state):
        """Determine the next node based on the current state.
        Args:
            self: RouterNode instance.
            state (dict): The current session state.
        Returns:
            str: The name of the next node.
        """
        if "interests" not in state:
            return "interests_node"
        elif "selected_industry" not in state:
            return "industry_node"
        elif "selected_job_family" not in state:
            return "job_node"
        elif "selected_job" not in state:
            return "skills_node"
        else:
            return "END"