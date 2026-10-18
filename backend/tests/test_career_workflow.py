import copy
import hashlib
import json

import pytest
import app.career_workflow as career_workflow
from fastapi.testclient import TestClient

from app.career_tree import delete_tree_node, initialize_tree, update_view_state
from app.main import app


def test_expansion_preserves_pre_refactor_prompts_and_tree():
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()

    # Captured from the original implementation before splitting expansion into graph nodes.
    baselines = [
        ("Ai Technology",
         "96002408a22984cbf784b0101bb5a1b111c1ca8a0e514adac5918b5179270b8b",
         "6c00857b9120ec2cad10324d7483617b98b5db41049f1fb6b4823261d675c464"),
        ("Ai Engineer",
         "67ec1ff4f1d32650f9dfc5f67ab06a57bdcc804ca512d94d1b313328f9282b83",
         "ffbadecc1ddbb6d80f8f3d9a3e7a7e038037880c4d5acc7d536a31705b5cd7b7"),
    ]
    tree = initialize_tree("Avery", ["AI/ML", "Music"], {"skills": ["Python"], "education": "Design"})
    node_id = "interest:ai-ml"
    for label, tree_digest, messages_digest in baselines:
        original = copy.deepcopy(tree)
        calls = []

        def chat(messages):
            calls.append(copy.deepcopy(messages))
            if len(calls) == 1:
                return {"children": [
                    {"label": label, "why_fit": "Specific to this path.",
                     "skills": ["Python", 42], "description": "x" * 1300},
                    {"label": label.lower(), "why_fit": "Duplicate label"},
                    {"label": "Generic", "why_fit": "Uses computers"},
                    {"label": "Missing reason"},
                ]}
            return {"accepted_indices": [1, 0]}

        result = career_workflow.run_career_workflow("expand", tree=tree, node_id=node_id, chat=chat)
        assert tree == original
        assert len(calls) == 2
        assert digest(calls) == messages_digest
        assert digest(result) == tree_digest
        tree = result
        node_id = tree["nodes"][-1]["id"]


@pytest.mark.parametrize(
    ("responses", "error"),
    [
        (["not JSON"], "The career guide did not return usable branch suggestions"),
        ([{"children": [{"label": "Sector", "why_fit": "Relevant"}]}, {"accepted_indices": []}],
         "No suggestions passed the branch relevance check. Please try again."),
        ([{"children": [{"label": "Sector", "why_fit": "Relevant"}]}, {"accepted_indices": [True]}],
         "The career guide could not verify branch relevance"),
        ([{"children": [{"label": "Sector", "why_fit": "Relevant"}]}, {"accepted_indices": [99]}],
         "The career guide could not verify branch relevance"),
    ],
)
def test_expansion_validation_preserves_input_and_does_not_retry(responses, error):
    tree = initialize_tree("Avery", ["Data"])
    original = copy.deepcopy(tree)
    calls = []
    remaining = iter(responses)

    def chat(messages):
        calls.append(messages)
        return next(remaining)

    with pytest.raises(ValueError) as exc:
        career_workflow.run_career_workflow("expand", tree=tree, node_id="interest:data", chat=chat)
    assert str(exc.value) == error
    assert len(calls) == len(responses)
    assert tree == original


def stream_expansion(tree, chat):
    return career_workflow._career_workflow.stream(
        {"operation": "expand", "payload": {"tree": tree, "node_id": "interest:data", "chat": chat}},
        stream_mode="updates",
    )


def test_expansion_runs_each_step_as_a_separate_graph_node():
    tree = initialize_tree("Avery", ["Data"])
    calls = []

    def chat(messages):
        calls.append(messages)
        if len(calls) == 1:
            return {"children": [{"label": "Healthcare Analytics", "why_fit": "Uses data in healthcare."}]}
        return {"accepted_indices": [0]}

    updates = list(stream_expansion(tree, chat))
    assert [next(iter(update)) for update in updates] == [
        "expand", "expand_context", "expand_generate", "expand_verify", "expand_apply",
    ]
    assert len(calls) == 2
    assert "Generate 3-5 distinct" in calls[0][-1]["content"]
    assert "Review career branch relevance" in calls[1][0]["content"]
    result = updates[-1]["expand_apply"]["result"]
    assert result["nodes"][-1]["label"] == "Healthcare Analytics"
    assert tree["generatedNodeIds"] == ["you"]


@pytest.mark.parametrize("collapsed", [False, True])
def test_cached_expansion_skips_all_generation_nodes(collapsed):
    tree = initialize_tree("Avery", ["Data"])
    tree = career_workflow.run_career_workflow(
        "expand", tree=tree, node_id="interest:data",
        chat=lambda messages: (
            {"accepted_indices": [0]} if "Review career branch relevance" in messages[0]["content"]
            else {"children": [{"label": "Healthcare Analytics", "why_fit": "Relevant"}]}
        ),
    )
    if collapsed:
        tree = update_view_state(tree, "interest:data", ["you"])

    def no_chat(**kwargs):
        pytest.fail("Cached expansion must not call AI")

    updates = list(stream_expansion(tree, no_chat))
    assert [next(iter(update)) for update in updates] == ["expand"]
    result = updates[0]["expand"]["result"]
    assert result["nodes"] == tree["nodes"]
    assert result["expandedNodeIds"] == ["you", "interest:data"]


def test_empty_cached_branch_runs_generation_nodes_again():
    tree = initialize_tree("Avery", ["Data"])

    def chat(messages):
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [0]}
        return {"children": [{"label": "Healthcare Analytics", "why_fit": "Relevant"}]}

    tree = career_workflow.run_career_workflow("expand", tree=tree, node_id="interest:data", chat=chat)
    tree = delete_tree_node(tree, tree["nodes"][-1]["id"])
    updates = list(stream_expansion(tree, chat))
    assert [next(iter(update)) for update in updates] == [
        "expand", "expand_context", "expand_generate", "expand_verify", "expand_apply",
    ]
    assert updates[-1]["expand_apply"]["result"]["nodes"][-1]["label"] == "Healthcare Analytics"


@pytest.mark.parametrize(("fails_at", "completed_nodes"), [
    ("generate", ["expand", "expand_context"]),
    ("verify", ["expand", "expand_context", "expand_generate"]),
])
def test_ai_failure_stops_workflow_without_retry_or_mutating_input(fails_at, completed_nodes):
    tree = initialize_tree("Avery", ["Data"])
    original = copy.deepcopy(tree)
    calls = []

    def chat(messages):
        calls.append(messages)
        if fails_at == "generate" or len(calls) == 2:
            raise RuntimeError("Provider unavailable")
        return {"children": [{"label": "Sector", "why_fit": "Relevant"}]}

    completed = []
    with pytest.raises(RuntimeError, match="Provider unavailable"):
        for update in stream_expansion(tree, chat):
            completed.append(next(iter(update)))
    assert completed == completed_nodes
    assert len(calls) == (1 if fails_at == "generate" else 2)
    assert tree == original


@pytest.mark.parametrize("node_id", ["missing", "you"])
def test_invalid_expansion_stops_before_ai(node_id):
    def no_chat(**kwargs):
        pytest.fail("Invalid selections must not call AI")

    error_type = KeyError if node_id == "missing" else ValueError
    with pytest.raises(error_type):
        career_workflow.run_career_workflow(
            "expand", tree=initialize_tree("Avery", ["Data"]), node_id=node_id, chat=no_chat
        )


@pytest.mark.parametrize("path_problem", ["missing_parent", "multiple_parents", "cycle"])
def test_invalid_path_stops_at_context_without_ai(path_problem):
    tree = initialize_tree("Avery", ["Data", "Design"])
    tree["edges"] = [edge for edge in tree["edges"] if edge["target"] != "interest:data"]
    if path_problem == "multiple_parents":
        parents = ["you", "interest:design"]
    elif path_problem == "cycle":
        parents = ["interest:data"]
    else:
        parents = []
    for parent in parents:
        tree["edges"].append({"id": f"{parent}->interest:data", "source": parent, "target": "interest:data"})
    original = copy.deepcopy(tree)

    def no_chat(**kwargs):
        pytest.fail("Invalid paths must not call AI")

    completed = []
    with pytest.raises(ValueError):
        for update in stream_expansion(tree, no_chat):
            completed.append(next(iter(update)))
    assert completed == ["expand"]
    assert tree == original


@pytest.mark.parametrize(("operation", "function_name", "payload", "expected_args"), [
    ("message", "guide_message",
     {"session_state": {}, "message": "Hello", "selected_node_id": None, "chat": None},
     ({}, "Hello", None, None)),
    ("explain", "explain_node",
     {"session_state": {}, "node_id": "interest:data", "chat": None},
     ({}, "interest:data", None)),
    ("changes", "apply_changes",
     {"session_state": {}, "proposal_id": "proposal", "accept": True},
     ({}, "proposal", True)),
    ("jobs", "search_jobs",
     {"tree": {}, "node_id": "role:data", "country": "US", "location": "", "workplace": "remote"},
     ({}, "role:data", "US", "", "remote")),
])
def test_other_operations_keep_their_existing_dispatch(monkeypatch, operation, function_name, payload, expected_args):
    calls = []
    expected = {"unchanged": operation}

    def domain_function(*args):
        calls.append(args)
        return expected

    monkeypatch.setattr(career_workflow, function_name, domain_function)
    assert career_workflow.run_career_workflow(operation, **payload) == expected
    assert calls == [expected_args]


def test_legacy_chatbot_route_is_removed():
    response = TestClient(app).post(
        "/chatbot/",
        json={"session_id": "old-session", "user_input": "design"},
    )

    assert response.status_code == 404
