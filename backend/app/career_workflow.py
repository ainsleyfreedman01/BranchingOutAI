"""LangGraph orchestration for the current career-tree operations."""

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.career_chat import apply_changes, explain_node, guide_message
from app.career_tree import (
    TreeExpansion,
    _career_path,
    _relevant_children,
    apply_branch_children,
    extract_interest_labels,
    generate_branch_candidates,
    initialize_tree,
    prepare_tree_expansion,
)
from app.live_jobs import search_jobs


class CareerWorkflowState(TypedDict, total=False):
    operation: Literal["initialize", "expand", "message", "explain", "changes", "jobs"]
    payload: dict[str, Any]
    result: Any
    expansion: TreeExpansion
    expansion_path: list[dict[str, Any]]
    expansion_candidates: list[dict[str, Any]]
    expansion_children: list[dict[str, Any]]


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
    expansion = prepare_tree_expansion(payload["tree"], payload["node_id"])
    if expansion["cached"]:
        return {"expansion": expansion, "result": expansion["tree"]}
    return {"expansion": expansion}


def _route_expansion(state: CareerWorkflowState) -> Literal["cached", "generate"]:
    return "cached" if state["expansion"]["cached"] else "generate"


def _expand_context(state: CareerWorkflowState) -> dict[str, Any]:
    expansion = state["expansion"]
    return {"expansion_path": _career_path(expansion["tree"], expansion["node_id"])}


def _expand_generate(state: CareerWorkflowState) -> dict[str, Any]:
    return {
        "expansion_candidates": generate_branch_candidates(
            state["expansion"], state["expansion_path"], state["payload"]["chat"]
        )
    }


def _expand_verify(state: CareerWorkflowState) -> dict[str, Any]:
    return {
        "expansion_children": _relevant_children(
            state["expansion_candidates"],
            state["expansion_path"],
            state["expansion"]["child_type"],
            state["payload"]["chat"],
        )
    }


def _expand_apply(state: CareerWorkflowState) -> dict[str, Any]:
    return {"result": apply_branch_children(state["expansion"], state["expansion_children"])}


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
        if operation != "expand":
            graph.add_edge(operation, END)
    graph.add_node("expand_context", _expand_context)
    graph.add_node("expand_generate", _expand_generate)
    graph.add_node("expand_verify", _expand_verify)
    graph.add_node("expand_apply", _expand_apply)
    graph.add_conditional_edges(
        "expand", _route_expansion, {"cached": END, "generate": "expand_context"}
    )
    graph.add_edge("expand_context", "expand_generate")
    graph.add_edge("expand_generate", "expand_verify")
    graph.add_edge("expand_verify", "expand_apply")
    graph.add_edge("expand_apply", END)
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
