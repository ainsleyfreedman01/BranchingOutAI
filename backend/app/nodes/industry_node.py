# backend/app/langgraph_agent/nodes/industry_node.py
from app.config import client

class IndustryNode:
    def process(self, user_input, state):
        """Process selected industry and suggest job roles.
        
        Args:
            self: IndustryNode instance.
            user_input (str): The user's selected industry.
            state (dict): The current session state.
        """
        state["industry"] = user_input

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful career exploration assistant."},
                {"role": "user", "content": f"User selected industry: {user_input}. Suggest 5 job roles in this industry."}
            ]
        )

        return response.choices[0].message.content, state