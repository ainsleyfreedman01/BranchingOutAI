# backend/app/langgraph_agent/nodes/interests_node.py
from app.config import client

class InterestsNode:
    def process(self, user_input, state):
        """Process user interests and suggest industries.
        
        Args:
            self: InterestsNode instance.
            user_input (str): The user's stated interests.
            state (dict): The current session state.
        """
        # Store interests
        state["interests"] = user_input

        # Chatbot response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful career exploration assistant."},
                {"role": "user", "content": f"The user's interests: {user_input}. Suggest 3 industries they might explore next."}
            ]
        )

        return response.choices[0].message.content, state