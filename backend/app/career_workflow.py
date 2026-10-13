"""LangGraph orchestration for the current career-tree operations."""

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.career_chat import apply_changes, explain_node, guide_message
from app.career_tree import expand_tree, extract_interest_labels, initialize_tree
from app.live_jobs import search_jobs


class CareerWorkflowState(TypedDict, total=False):
    operation: Literal["initialize", "expand", "message", "explain", "changes", "jobs"]
    payload: dict[str, Any]
    result: Any


def _initialize(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    session_state = payload["session_state"]
    user_input = payload["user_input"]
    profile_context = payload["profile_context"]

    if user_input:
        interests = extract_interest_labels(user_input, profile_context, payload["chat"])
        session_state["user_input"] = user_input
        response = "I found these interests to start your career map. Select one to explore connected industries."
        history = session_state.get("chat_history") if isinstance(session_state.get("chat_history"), list) else []
        history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response},
        ])
        session_state["chat_history"] = history[-40:]
        session_state["assistant_response"] = response
    else:
        interests = session_state.get("interests", [])
        if not isinstance(interests, list) or not interests:
            interests = profile_context.get("interests", [])
        response = session_state.get("assistant_response", "Your career map is ready to explore.")

    if not isinstance(interests, list) or not interests:
        return {"result": {"session_state": session_state, "interests": [], "response": response}}

    session_state["interests"] = interests[:12]
    tree_profile_context = {
        "interests": interests[:12],
        "industries": session_state.get("industries", [])[:12]
        if isinstance(session_state.get("industries"), list) else [],
        "skills": session_state.get("skills", [])[:12]
        if isinstance(session_state.get("skills"), list) else [],
        "starting_input": user_input,
        **profile_context,
    }
    tree = initialize_tree(payload["root_label"], interests, tree_profile_context)
    session_state["career_tree"] = tree
    return {
        "result": {
            "session_state": session_state,
            "interests": interests[:12],
            "tree": tree,
            "response": response,
        }
    }


def _expand(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    return {"result": expand_tree(payload["tree"], payload["node_id"], payload["chat"])}


def _message(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    return {
        "result": guide_message(
            payload["session_state"],
            payload["message"],
            payload["selected_node_id"],
            payload["chat"],
        )
    }


def _explain(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    return {
        "result": explain_node(
            payload["session_state"],
            payload["node_id"],
            payload["chat"],
        )
    }


def _changes(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    return {
        "result": apply_changes(
            payload["session_state"],
            payload["proposal_id"],
            payload["accept"],
        )
    }


def _jobs(state: CareerWorkflowState) -> dict[str, Any]:
    payload = state["payload"]
    return {
        "result": search_jobs(
            payload["tree"],
            payload["node_id"],
            payload["country"],
            payload["location"],
            payload["workplace"],
        )
    }


def _build_workflow():
    operations = {
        "initialize": _initialize,
        "expand": _expand,
        "message": _message,
        "explain": _explain,
        "changes": _changes,
        "jobs": _jobs,
    }
    graph = StateGraph(CareerWorkflowState)
    for operation, node in operations.items():
        graph.add_node(operation, node)
        graph.add_edge(operation, END)
    graph.add_conditional_edges(
        START,
        lambda state: state["operation"],
        {operation: operation for operation in operations},
    )
    return graph.compile()


_career_workflow = _build_workflow()


def run_career_workflow(operation: CareerWorkflowState["operation"], **payload: Any) -> Any:
    """Run one current career-tree operation through the compiled LangGraph."""
    result = _career_workflow.invoke({"operation": operation, "payload": payload})
    return result["result"]
