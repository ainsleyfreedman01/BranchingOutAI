# backend/app/langgraph_agent/nodes/skills_node.py
from app.config import client

class SkillsNode:
    def process(self, user_input, state):
        """Process selected skill and suggest development steps.
    
        Args:
            self: SkillsNode instance.
            user_input (str): The user's selected skill.
            state (dict): The current session state.
        """
        state["skill"] = user_input

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You help users develop and become confident in their skills."},
                {"role": "user", "content": f"How can someone build the skill '{user_input}'? Give 5 actionable steps."}
            ]
        )

        return response.choices[0].message.content, state