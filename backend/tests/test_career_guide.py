from copy import deepcopy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.career_workflow as career_workflow
import app.live_jobs as live_jobs
from app.career_chat import guide_message, apply_changes
from app.career_tree import initialize_tree, expand_tree


def seeded_state():
    tree = initialize_tree("Avery", ["Jewish Studies", "Software"])

    def chat(messages):
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [0]}
        return {"children": [{"label": "Jewish Education", "why_fit": "Teaches Jewish history."}]}

    tree = expand_tree(tree, "interest:jewish-studies", chat)
    return {"career_tree": tree, "chat_history": [], "setting": "keep"}


def test_ongoing_chat_proposes_additions_and_context_without_changing_tree():
    state = seeded_state()
    original = deepcopy(state)
    calls = []

    def chat(messages):
        calls.append(messages)
        return {"response": "We can add this interest and keep your other branches.",
            "interests_to_add": ["Supporting children with disabilities"],
            "context_note": "Volunteers with children on weekends."}

    proposed = guide_message(state, "I volunteer with children and want to support kids with disabilities",
        "interest:jewish-studies", chat)
    assert state == original
    assert proposed["career_tree"] == original["career_tree"]
    assert len(proposed["chat_history"]) == 2
    assert json.loads(calls[0][-1]["content"])["selected_node"]["id"] == "interest:jewish-studies"
    changes = proposed["pending_career_changes"]
    applied = apply_changes(proposed, changes["id"], True)
    assert any(node["label"] == "Supporting children with disabilities" for node in applied["career_tree"]["nodes"])
    assert all(node in applied["career_tree"]["nodes"] for node in original["career_tree"]["nodes"])
    assert applied["career_tree"]["profileContext"]["career_notes"] == ["Volunteers with children on weekends."]
    assert applied["setting"] == "keep"
    assert "pending_career_changes" not in applied


def test_refresh_requires_confirmation_and_preserves_other_interests():
    state = seeded_state()
    proposed = guide_message(state, "This branch is not relevant", "interest:jewish-studies", lambda **kw: {
        "response": "I suggest rebuilding Jewish Studies.",
        "refresh_interest_ids": ["interest:jewish-studies"],
    })
    changes = proposed["pending_career_changes"]
    rejected = apply_changes(proposed, changes["id"], False)
    assert rejected["career_tree"] == state["career_tree"]
    applied = apply_changes(proposed, changes["id"], True)
    assert [node["type"] for node in applied["career_tree"]["nodes"]] == ["user", "interest", "interest"]
    assert "interest:jewish-studies" not in applied["career_tree"]["generatedNodeIds"]
    assert applied["interests"] == ["Jewish Studies", "Software"]
    with pytest.raises(ValueError, match="no longer"):
        apply_changes(applied, changes["id"], True)


def test_questions_and_ambiguous_goals_do_not_mutate_graph():
    state = seeded_state()
    result = guide_message(state, "What qualifications do I need?", None, lambda **kw: {
        "response": "Which role would you like to discuss?",
    })
    assert result["career_tree"] == state["career_tree"]
    assert "pending_career_changes" not in result
    with pytest.raises(ValueError, match="unknown interest"):
        guide_message(state, "Refine", None, lambda **kw: {"response": "OK", "refresh_interest_ids": ["you"]})


def test_followup_keeps_pending_proposal_and_conversation_history():
    state = seeded_state()
    state["chat_history"] = [{"role": "user", "content": f"Message {i}"} for i in range(20)]
    proposed = guide_message(state, "Add music", None, lambda **kw: {"response": "We can add music.", "interests_to_add": ["Music"]})
    followed = guide_message(proposed, "Why?", None, lambda **kw: {"response": "Because you said you enjoy it."})
    assert followed["pending_career_changes"] == proposed["pending_career_changes"]
    assert len(followed["chat_history"]) == 24
    assert followed["chat_history"][0] == state["chat_history"][0]


def jobs_tree():
    tree = initialize_tree("Avery", ["Supporting children with disabilities"])
    interest = tree["nodes"][1]["id"]
    tree["nodes"] += [
        {"id": "sector", "type": "industry", "label": "Special Education", "details": {}},
        {"id": "role", "type": "role", "label": "Special Education Teacher", "details": {}},
    ]
    tree["edges"] += [
        {"id": "s", "source": interest, "target": "sector"},
        {"id": "r", "source": "sector", "target": "role"},
    ]
    return tree


@pytest.fixture
def stub_job_title_service(monkeypatch):
    monkeypatch.setattr(live_jobs.client, "chat_json", lambda **kw: {"titles": ["Special Education Teacher"]})


def test_provider_search_uses_server_key_and_real_safe_listing_urls(monkeypatch, stub_job_title_service):
    monkeypatch.setenv("THEIRSTACK_API_KEY", "private-test-key")
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"data": [
            {"id": 1, "job_title": "Special Education Teacher", "company_object": {"name": "School"},
             "final_url": "https://school.example/jobs/1", "location": "Boston", "date_posted": "2026-10-05"},
            {"id": 2, "job_title": "Bad link", "url": "javascript:alert(1)"},
            {"id": 3, "job_title": "Blurred", "url": "https://example.com", "has_blurred_data": True},
        ]})

    monkeypatch.setattr(live_jobs.httpx, "post", post)
    jobs = live_jobs.search_jobs(jobs_tree(), "role", "us", "Boston, ma", "local")
    assert len(jobs) == 1
    assert jobs[0]["company"] == "School"
    assert jobs[0]["url"] == "https://school.example/jobs/1"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer private-test-key"
    payload = calls[0][1]["json"]
    assert payload["limit"] == 5
    assert payload["job_title_or"] == ["Special Education Teacher"]
    assert payload["job_country_code_or"] == ["US"]
    assert payload["workplace_types_or"] == ["hybrid", "on_site"]
    assert payload["job_location_pattern_or"] == [r"Boston,\ MA"]
    assert "private-test-key" not in str(jobs)


@pytest.mark.parametrize("status", [401, 403, 402, 429, 500])
def test_provider_errors_are_explicit_not_empty_success(monkeypatch, status, stub_job_title_service):
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-key")
    monkeypatch.setattr(live_jobs.httpx, "post", lambda *a, **kw: httpx.Response(status))
    with pytest.raises(live_jobs.JobSearchUnavailable):
        live_jobs.search_jobs(jobs_tree(), "role", "US", "", "remote")


@pytest.mark.parametrize("location", ["Boston", "Boston, Massachusetts", "Boston, ZZ", ", MA", "123, MA"])
def test_local_search_validates_supplied_city_and_state(location):
    with pytest.raises(ValueError, match="state abbreviation"):
        live_jobs.search_jobs(jobs_tree(), "role", "US", location, "local")


def test_remote_search_drops_location_and_requires_work_setting(monkeypatch, stub_job_title_service):
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-key")
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr(live_jobs.httpx, "post", post)
    assert live_jobs.search_jobs(jobs_tree(), "role", "US", "Boston, MA", "remote") == []
    assert calls[0]["workplace_types_or"] == ["remote"]
    assert "job_location_pattern_or" not in calls[0]
    for location in ("", "  "):
        assert live_jobs.search_jobs(jobs_tree(), "role", "US", location, "local") == []
        assert calls[-1]["workplace_types_or"] == ["hybrid", "on_site"]
        assert calls[-1]["job_country_code_or"] == ["US"]
        assert "job_location_pattern_or" not in calls[-1]
    with pytest.raises(ValueError, match="Choose"):
        live_jobs.search_jobs(jobs_tree(), "role", "US", "", "any")


def test_missing_key_invalid_nodes_empty_results_and_timeout(monkeypatch, stub_job_title_service):
    monkeypatch.delenv("THEIRSTACK_API_KEY", raising=False)
    with pytest.raises(live_jobs.JobSearchUnavailable, match="configured"):
        live_jobs.search_jobs(jobs_tree(), "role", "US", "", "remote")
    with pytest.raises(ValueError, match="Select a role"):
        live_jobs.search_jobs(jobs_tree(), "you", "US", "", "remote")
    with pytest.raises(ValueError, match="United States"):
        live_jobs.search_jobs(jobs_tree(), "role", "CA", "", "remote")
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-key")
    monkeypatch.setattr(live_jobs.httpx, "post", lambda *a, **kw: httpx.Response(200, json={"data": []}))
    assert live_jobs.search_jobs(jobs_tree(), "role", "US", "", "remote") == []

    def timeout(*a, **kw):
        raise httpx.ReadTimeout("timeout")
    monkeypatch.setattr(live_jobs.httpx, "post", timeout)
    with pytest.raises(live_jobs.JobSearchUnavailable, match="unavailable"):
        live_jobs.search_jobs(jobs_tree(), "role", "US", "", "remote")


def test_guide_and_jobs_routes_are_authenticated_and_persist_proposals(monkeypatch):
    state = seeded_state()
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *a: (True, 0))
    monkeypatch.setattr(main, "get_state", lambda *a, **kw: deepcopy(state))
    monkeypatch.setattr(career_workflow, "search_jobs", lambda *a: [])

    def save(session_id, updated, **kw):
        assert kw == {"user_id": "user", "access_token": "token"}
        state.clear()
        state.update(deepcopy(updated))

    monkeypatch.setattr(main, "save_state", save)
    import app.config as config
    monkeypatch.setattr(config.client, "chat", lambda **kw: {
        "response": "Add music?", "interests_to_add": ["Music"],
    })
    client = TestClient(main.app)
    assert client.post("/career-tree/message", json={"session_id": "session", "message": "Music"}).status_code == 401
    assert client.post("/career-tree/jobs", json={"session_id": "session", "node_id": "role", "country": "US"}).status_code == 401
    main.app.dependency_overrides[main.authenticated_user] = lambda: main.AuthenticatedUser("user", "token")
    try:
        response = client.post("/career-tree/message", json={"session_id": "session", "message": "Add music"})
        assert response.status_code == 200
        proposal = response.json()["state"]["pending_career_changes"]
        applied = client.post("/career-tree/changes", json={"session_id": "session", "proposal_id": proposal["id"], "accept": True})
        assert applied.status_code == 200
        assert any(node["label"] == "Music" for node in applied.json()["state"]["career_tree"]["nodes"])
        assert client.post("/career-tree/changes", json={"session_id": "session", "proposal_id": proposal["id"], "accept": True}).status_code == 409
        assert client.post("/career-tree/jobs", json={"session_id": "session", "node_id": "role", "country": "USA"}).status_code == 422
        assert client.post("/career-tree/jobs", json={"session_id": "session", "node_id": "role", "country": "CA"}).status_code == 422
        assert client.post("/career-tree/jobs", json={"session_id": "session", "node_id": "role"}).status_code == 422
        assert client.post("/career-tree/jobs", json={"session_id": "session", "node_id": "role", "country": "US", "workplace": "remote"}).json() == {"jobs": [], "source": "TheirStack"}
    finally:
        main.app.dependency_overrides.clear()
