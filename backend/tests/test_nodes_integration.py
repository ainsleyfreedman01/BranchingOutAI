import types
import pytest
from app.graph_setup import agent_graph


@pytest.mark.integration
def test_agent_graph_nodes_integration(monkeypatch):
    """Integration test that exercises interests -> industry -> job -> skills nodes.

    This replaces the OpenAI client with a deterministic fake that returns
    Python structures for each node so the flow can be tested end-to-end.
    """

    responses = {
        "interests": ["Technology", "Finance"],
        "industries": ["Software", "Banking"],
        "job_families": ["Data Science", "DevOps"],
        "jobs": ["Data Scientist", "Machine Learning Engineer"],
        "skills": {"hard_skills": ["Python", "SQL"], "soft_skills": ["Communication"]},
    }

    # Fake chat that inspects the last user message to decide which response to return
    def fake_chat(messages, model=None, temperature=None):
        last = messages[-1]["content"].lower()
        if "suggest 2-3 broad industries" in last or "the user is interested in" in last:
            return responses["industries"]
        if "suggest 2-3 job families" in last or "industry:" in last:
            return responses["job_families"]
        if "suggest 3-4 job titles" in last or "job family" in last:
            return responses["jobs"]
        if "list 3-5 hard skills" in last or "job title" in last:
            return responses["skills"]
        # default
        return responses["industries"]

    import app.config as cfg
    monkeypatch.setattr(cfg.client, "chat", fake_chat)

    # Start with raw input; agent_graph will route through nodes
    state = {"user_input": "I like data and systems"}
    session_id = "integration-test-1"

    # Step 1: interests_node
    out, state = agent_graph.step(state, session_id=session_id)
    assert "industries" in state

    # Step 2: industry_node (use the first industry as selected)
    state["user_input"] = state["industries"][0]
    out, state = agent_graph.step(state, session_id=session_id)
    assert "job_families" in state

    # Step 3: job_node
    state["user_input"] = state["job_families"][0]
    out, state = agent_graph.step(state, session_id=session_id)
    assert "jobs" in state

    # Step 4: skills_node
    state["user_input"] = state["jobs"][0]
    out, state = agent_graph.step(state, session_id=session_id)
    assert "skills" in state

    # Final router should now return END
    out, state = agent_graph.step(state, session_id=session_id)
    assert out == "Session complete." or "END" in out
