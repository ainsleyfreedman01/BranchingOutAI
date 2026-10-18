import copy
import json
import pytest

from app.career_tree import GENERATION_VERSION, delete_tree_node, expand_tree as domain_expand_tree, extract_interest_labels, initialize_tree, update_view_state, upgrade_tree_generation
from app.career_workflow import run_career_workflow
from app.utils.acronyms import canonicalize_acronyms


@pytest.fixture(params=["domain", "langgraph"])
def expand_tree(request):
    if request.param == "domain":
        return domain_expand_tree
    return lambda tree, node_id, chat: run_career_workflow(
        "expand", tree=tree, node_id=node_id, chat=chat
    )


def test_acronym_capitalization_preserves_words_and_proper_names():
    assert canonicalize_acronyms("Ai/Ml, Ux/Ui, Nlp and Api-driven design") == "AI/ML, UX/UI, NLP and API-driven design"
    assert canonicalize_acronyms("Retail, email, HTML, OpenAI and Python") == "Retail, email, HTML, OpenAI and Python"


def test_tree_labels_normalize_acronyms_at_every_generation_step(expand_tree):
    interests = extract_interest_labels("ai", {}, lambda **kwargs: '["Responsible Ai", "Ml"]')
    assert interests == ["Responsible AI", "ML"]
    tree = initialize_tree("Ai Jones", ["Ai/Ml"])
    assert tree["nodes"][0]["label"] == "Ai Jones"
    assert tree["nodes"][1]["label"] == "AI/ML"
    tree = expand_tree(tree, "interest:ai-ml", lambda messages: (
        {"accepted_indices": [0]} if "Review career branch relevance" in messages[0]["content"]
        else {"children": [{"label": "Ai Technology", "why_fit": "Builds AI and ML systems."}]}
    ))
    assert tree["nodes"][-1]["label"] == "AI Technology"


def test_interest_extraction_does_not_generate_deeper_career_nodes():
    calls = []

    def fake_chat(messages):
        calls.append(messages)
        return '["Software & AI", "Product Design"]'

    interests = extract_interest_labels("I like software and product design", {"skills": ["Python"]}, fake_chat)

    assert interests == ["Software & AI", "Product Design"]
    assert "Do not suggest industries, roles, jobs, or skills yet." in calls[0][-1]["content"]


def test_general_career_goal_preserves_intent_and_does_not_fake_failed_extraction():
    calls = []
    def chat(messages):
        calls.append(messages)
        return '["Supporting children with disabilities"]'
    labels = extract_interest_labels("I want to work with kids with special needs", {}, chat)
    assert labels == ["Supporting children with disabilities"]
    assert "A message expressing one goal should yield one interest" in calls[0][-1]["content"]
    with pytest.raises(ValueError):
        extract_interest_labels("I want to work with kids", {}, lambda **kw: "invalid")


def test_initial_tree_contains_interests_only():
    tree = initialize_tree("Avery", ["Software & AI", "Data & Analytics", "Software & AI"])

    assert [node["type"] for node in tree["nodes"]] == ["user", "interest", "interest"]
    assert tree["expandedNodeIds"] == ["you"]
    assert len(tree["edges"]) == 2


def test_expansion_generates_once_and_keeps_same_named_sectors_branch_specific(expand_tree):
    tree = initialize_tree("Avery", ["Software", "Analytics"])
    calls = []

    def fake_chat(messages):
        calls.append(messages)
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [0]}
        return {"children": [{"label": "Technology", "description": "Builds digital products.", "why_fit": "Supports this interest."}]}

    tree = expand_tree(tree, "interest:software", fake_chat)
    assert tree["expandedNodeIds"] == ["you", "interest:software"]
    assert any(node["label"] == "Technology" for node in tree["nodes"])
    assert "Never return job titles" in calls[0][-1]["content"]

    cached = expand_tree(tree, "interest:software", fake_chat)
    assert len(calls) == 2
    assert cached == tree

    collapsed = update_view_state(tree, "interest:software", ["you"])
    reopened = expand_tree(collapsed, "interest:software", fake_chat)
    assert reopened["expandedNodeIds"] == ["you", "interest:software"]
    assert len(calls) == 2

    tree = expand_tree(reopened, "interest:analytics", fake_chat)
    technology = [node for node in tree["nodes"] if node["label"] == "Technology"]
    assert len(technology) == 2
    assert technology[0]["id"] != technology[1]["id"]
    assert all(sum(edge["target"] == node["id"] for edge in tree["edges"]) == 1 for node in technology)


def test_expansion_regenerates_a_branch_after_all_children_are_deleted(expand_tree):
    tree = initialize_tree("Avery", ["Data Analytics"])
    generated_labels = iter(["Healthcare Analytics", "Business Analytics"])
    generation_calls = []

    def fake_chat(messages):
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [0]}
        generation_calls.append(messages)
        return {"children": [{
            "label": next(generated_labels),
            "why_fit": "Applies data analysis to this domain.",
        }]}

    tree = expand_tree(tree, "interest:data-analytics", fake_chat)
    child_id = next(edge["target"] for edge in tree["edges"] if edge["source"] == "interest:data-analytics")
    tree = delete_tree_node(tree, child_id)

    regenerated = expand_tree(tree, "interest:data-analytics", fake_chat)

    assert len(generation_calls) == 2
    assert any(node["label"] == "Business Analytics" for node in regenerated["nodes"])


@pytest.mark.parametrize("interest", ["Jewish Studies", "Marine Biology", "Music", "AI/ML"])
def test_every_generation_depth_keeps_its_ordered_originating_interest(interest, expand_tree):
    tree = initialize_tree("Avery", [interest, "Unrelated Interest"], {"interests": [interest, "Unrelated Interest"]})
    parent = tree["nodes"][1]["id"]
    labels = ["Domain-specific sector", "Domain-specific role"]
    for label in labels:
        calls = []

        def fake_chat(messages):
            calls.append(messages)
            if "Review career branch relevance" in messages[0]["content"]:
                return {"accepted_indices": [0]}
            return {"children": [{"label": label, "why_fit": f"Uses {interest} in this path."}]}

        tree = expand_tree(tree, parent, fake_chat)
        expected_labels = ["Avery", interest] + labels[:labels.index(label)]
        for messages in calls:
            prompt = messages[-1]["content"]
            assert f"Originating interest: {interest}." in prompt
            path_text = prompt.split("career path: " if "Ordered career path: " in prompt else "Career path: ")[1]
            path = json.JSONDecoder().raw_decode(path_text)[0]
            assert [node["label"] for node in path] == expected_labels
        parent = next(edge["target"] for edge in tree["edges"] if edge["source"] == parent)
    with pytest.raises(ValueError, match="no expandable"):
        expand_tree(tree, parent, lambda **kw: pytest.fail("Role expansion must not call AI"))


def test_same_named_nodes_do_not_mix_details_or_descendants_across_interests(expand_tree):
    tree = initialize_tree("Avery", ["Jewish Studies", "Software"])

    def chat_for(label):
        def chat(messages):
            if "Review career branch relevance" in messages[0]["content"]:
                return {"accepted_indices": [0]}
            return {"children": [{"label": label, "why_fit": messages[-1]["content"].split("Originating interest: ")[1].split(".")[0]}]}
        return chat

    for interest in ["interest:jewish-studies", "interest:software"]:
        tree = expand_tree(tree, interest, chat_for("Education"))
    sectors = [node for node in tree["nodes"] if node["type"] == "industry"]
    assert len(sectors) == 2
    assert sectors[0]["details"]["why_fit"] == "Jewish Studies"
    assert sectors[1]["details"]["why_fit"] == "Software"
    tree = expand_tree(tree, sectors[0]["id"], chat_for("Jewish Studies Educator"))
    tree = expand_tree(tree, sectors[1]["id"], chat_for("Programming Educator"))
    assert next(node["label"] for node in tree["nodes"] if node["id"] == next(
        edge["target"] for edge in tree["edges"] if edge["source"] == sectors[0]["id"]
    )) == "Jewish Studies Educator"
    result = delete_tree_node(tree, sectors[0]["id"])
    assert any(node["label"] == "Programming Educator" for node in result["nodes"])
    assert not any(node["label"] == "Jewish Studies Educator" for node in result["nodes"])


def test_relevance_review_filters_generic_suggestions_and_requires_explanations(expand_tree):
    tree = initialize_tree("Avery", ["Jewish Studies"])

    def fake_chat(messages):
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [1]}
        return {"children": [
            {"label": "Technology", "why_fit": "All careers can use computers."},
            {"label": "Jewish Cultural Heritage", "why_fit": "Preserves Jewish history and culture."},
            {"label": "Finance"},
        ]}

    result = expand_tree(tree, "interest:jewish-studies", fake_chat)
    assert result["nodes"][-1]["label"] == "Jewish Cultural Heritage"
    assert not any(node["label"] == "Technology" for node in result["nodes"])
    original = copy.deepcopy(tree)
    for review in [{"accepted_indices": []}, {"accepted_indices": [99]}, {"accepted_indices": [True]}, "not JSON"]:
        def rejected_chat(messages):
            if "Review career branch relevance" in messages[0]["content"]:
                return review
            return {"children": [{"label": "Technology", "why_fit": "Generic"}]}
        with pytest.raises(ValueError):
            expand_tree(tree, "interest:jewish-studies", rejected_chat)
        assert tree == original


def test_legacy_upgrade_rebuilds_descendants_once_and_preserves_starting_data():
    tree = initialize_tree("Avery", ["Jewish Studies", "Software"], {"education": "History"})
    tree.pop("generationVersion")
    tree["nodes"].append({"id": "industry:technology", "type": "industry", "label": "Technology", "details": {}})
    tree["edges"].append({"id": "old", "source": "interest:jewish-studies", "target": "industry:technology"})
    tree["generatedNodeIds"].append("interest:jewish-studies")
    tree["selectedNodeId"] = "industry:technology"
    original = copy.deepcopy(tree)
    upgraded = upgrade_tree_generation(tree)
    assert tree == original
    assert [node["type"] for node in upgraded["nodes"]] == ["user", "interest", "interest"]
    assert upgraded["profileContext"] == tree["profileContext"]
    assert upgraded["generatedNodeIds"] == upgraded["expandedNodeIds"] == ["you"]
    assert upgraded["selectedNodeId"] == "you"
    assert upgraded["generationVersion"] == GENERATION_VERSION
    assert "cleared" in upgraded["rebuildNotice"]
    assert upgrade_tree_generation(upgraded) is upgraded


def test_colliding_interest_slugs_still_have_independent_paths(expand_tree):
    tree = initialize_tree("Avery", ["AI/ML", "AI ML", "\u6587\u5316", "\u6559\u80b2"])
    interests = tree["nodes"][1:]
    assert len({node["id"] for node in interests}) == 4
    for interest in interests:
        def fake_chat(messages):
            if "Review career branch relevance" in messages[0]["content"]:
                return {"accepted_indices": [0]}
            assert f"Originating interest: {interest['label']}." in messages[-1]["content"]
            return {"children": [{"label": "Domain sector", "why_fit": "Specific to this interest."}]}
        tree = expand_tree(tree, interest["id"], fake_chat)
    assert len({node["id"] for node in tree["nodes"] if node["type"] == "industry"}) == 4


def test_depth_upgrade_preserves_roles_and_removes_only_deeper_nodes(expand_tree):
    tree = initialize_tree("Avery", ["Design"])
    tree.pop("treeDepthVersion")
    for node_id, node_type in [("sector", "industry"), ("role", "role"), ("job", "job"), ("skill", "skill")]:
        tree["nodes"].append({"id": node_id, "type": node_type, "label": node_id, "details": {}})
    path = ["interest:design", "sector", "role", "job", "skill"]
    tree["edges"] += [{"id": f"{a}->{b}", "source": a, "target": b} for a, b in zip(path, path[1:])]
    tree["expandedNodeIds"] += path[:-1]
    tree["generatedNodeIds"] += path[:-1]
    tree["selectedNodeId"] = "job"
    original = copy.deepcopy(tree)
    result = upgrade_tree_generation(tree)
    assert tree == original
    assert [node["type"] for node in result["nodes"]] == ["user", "interest", "industry", "role"]
    assert result["selectedNodeId"] == "you"
    assert result["expandedNodeIds"] == result["generatedNodeIds"] == ["you", "interest:design", "sector"]
    assert result["profileContext"] == tree["profileContext"]
    assert upgrade_tree_generation(result) is result
    with pytest.raises(ValueError, match="no expandable"):
        expand_tree(result, "role", lambda **kw: pytest.fail("No AI call for a leaf role"))


def test_view_state_tracks_selection_and_expansion_separately():
    tree = initialize_tree("Avery", ["Software"])
    tree = update_view_state(tree, "interest:software", ["you", "interest:software"])

    assert tree["selectedNodeId"] == "interest:software"
    assert tree["expandedNodeIds"] == ["you", "interest:software"]


def test_deletion_removes_exclusive_descendants_but_preserves_shared_branch():
    tree = initialize_tree("Avery", ["Design", "Data"])
    for node_id in ("exclusive", "shared", "shared-child"):
        tree["nodes"].append({"id": node_id, "type": "role", "label": node_id, "details": {}})
    for source, target in (
        ("interest:design", "exclusive"),
        ("interest:design", "shared"),
        ("interest:data", "shared"),
        ("shared", "shared-child"),
    ):
        tree["edges"].append({"id": f"{source}->{target}", "source": source, "target": target})
    tree["selectedNodeId"] = "exclusive"
    tree["expandedNodeIds"] += ["interest:design", "exclusive", "shared"]
    tree["generatedNodeIds"] += ["interest:design", "exclusive", "shared"]
    original = copy.deepcopy(tree)

    result = delete_tree_node(tree, "interest:design")
    assert {node["id"] for node in result["nodes"]} == {"you", "interest:data", "shared", "shared-child"}
    assert result["selectedNodeId"] == "you"
    assert result["expandedNodeIds"] == ["you", "shared"]
    assert result["generatedNodeIds"] == ["you", "shared"]
    assert all("interest:design" not in (edge["source"], edge["target"]) for edge in result["edges"])
    assert tree == original


def test_deletion_protects_root_and_rejects_unknown_nodes():
    tree = initialize_tree("Avery", ["Design"])
    with pytest.raises(ValueError, match="central name"):
        delete_tree_node(tree, "you")
    with pytest.raises(KeyError, match="not found"):
        delete_tree_node(tree, "missing")
    result = delete_tree_node(tree, "interest:design")
    assert len(result["nodes"]) == 1
    assert result["edges"] == []
    assert result["generatedNodeIds"] == ["you"]