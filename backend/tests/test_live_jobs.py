import json
from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient

from app import live_jobs
from app import main
from app.career_tree import initialize_tree


def role_tree(interest, sector, role):
    tree = initialize_tree("Private Name", [interest], {"private": "Do not send"})
    tree["nodes"].extend([
        {"id": "sector", "type": "industry", "label": sector, "details": {}},
        {"id": "role", "type": "role", "label": role, "details": {}},
    ])
    tree["edges"].extend([
        {"source": tree["nodes"][1]["id"], "target": "sector"},
        {"source": "sector", "target": "role"},
    ])
    return tree


@pytest.mark.parametrize(("interest", "sector", "role", "variants"), [
    ("Jewish Studies", "Jewish Education", "Jewish Studies Educator",
     ["Judaic Studies Teacher", "Jewish Educator"]),
    ("Responsible AI", "AI Governance", "Responsible AI Specialist",
     ["AI Governance Specialist", "AI Ethics Specialist"]),
    ("Social Impact", "Nonprofit Services", "Community Programs Professional",
     ["Community Program Coordinator", "Community Outreach Specialist"]),
    ("Software", "Software Development", "Software Engineer",
     ["Software Developer", "Application Developer"]),
])
def test_every_role_search_uses_branch_specific_hiring_titles(monkeypatch, interest, sector, role, variants):
    tree = role_tree(interest, sector, role)
    original = deepcopy(tree)
    prompts = []
    requests = []

    def translate(messages):
        prompts.append(messages)
        return json.dumps({"titles": variants})

    def provider(url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(200, json={"data": [{
            "id": "opening", "job_title": variants[0], "company": "Employer",
            "final_url": "https://employer.example/opening",
        }]})

    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-only-key")
    monkeypatch.setattr(live_jobs.client, "chat_json", translate)
    monkeypatch.setattr(live_jobs.httpx, "post", provider)
    jobs = live_jobs.search_jobs(tree, "role", "US", "", "local")

    assert len(prompts) == len(requests) == 1
    assert requests[0]["job_title_or"] == [role, *variants]
    assert requests[0]["job_country_code_or"] == ["US"]
    assert requests[0]["workplace_types_or"] == ["hybrid", "on_site"]
    assert requests[0]["posted_at_max_age_days"] == 30
    assert jobs[0]["title"] == variants[0]
    assert jobs[0]["interest"] == interest
    assert json.loads(prompts[0][1]["content"]) == {"career_path": [
        {"type": "interest", "label": interest},
        {"type": "industry", "label": sector},
        {"type": "role", "label": role},
    ]}
    assert "Private Name" not in prompts[0][1]["content"]
    assert "Do not send" not in prompts[0][1]["content"]
    assert tree == original


def test_title_normalization_and_deduplication(monkeypatch):
    monkeypatch.setattr(live_jobs.client, "chat_json", lambda **kw: {
        "titles": [" software   engineer ", "Software Developer", "software developer"],
    })
    tree = role_tree("Software", "Development", "Software Engineer")
    path = live_jobs._career_path(tree, "role")
    assert live_jobs._search_titles(path) == ["Software Engineer", "Software Developer"]


@pytest.mark.parametrize("response", [
    "not json", {}, {"titles": []}, {"titles": "Teacher"},
    {"titles": [None]}, {"titles": [" "]}, {"titles": ["x" * 121]},
    {"titles": ["Teacher"] * 6},
])
def test_invalid_title_translation_is_not_an_empty_success(monkeypatch, response):
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-only-key")
    monkeypatch.setattr(live_jobs.client, "chat_json", lambda **kw: response)

    def unexpected_provider_call(*args, **kwargs):
        pytest.fail("Invalid title translations must not query the job provider")

    monkeypatch.setattr(live_jobs.httpx, "post", unexpected_provider_call)
    with pytest.raises(live_jobs.JobSearchUnavailable, match="invalid"):
        live_jobs.search_jobs(role_tree("Jewish Studies", "Education", "Jewish Educator"),
                              "role", "US", "", "remote")


def test_title_service_failure_is_explicit(monkeypatch):
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-only-key")

    def unavailable(**kwargs):
        raise RuntimeError("Unconfigured service")

    monkeypatch.setattr(live_jobs.client, "chat_json", unavailable)
    with pytest.raises(live_jobs.JobSearchUnavailable, match="prepare related job titles"):
        live_jobs.search_jobs(role_tree("Software", "Development", "Software Engineer"),
                              "role", "US", "", "remote")


@pytest.mark.parametrize("invalid_titles", [False, True])
def test_job_route_returns_related_openings_or_explicit_service_error(monkeypatch, invalid_titles):
    tree = role_tree("Jewish Studies", "Jewish Education", "Jewish Studies Educator")
    monkeypatch.setenv("THEIRSTACK_API_KEY", "test-only-key")
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *a: (True, 0))
    monkeypatch.setattr(main, "get_state", lambda *a, **kw: {"career_tree": tree})
    monkeypatch.setattr(live_jobs.client, "chat_json", lambda **kw: {
        "titles": [] if invalid_titles else ["Judaic Studies Teacher"],
    })
    monkeypatch.setattr(live_jobs.httpx, "post", lambda *a, **kw: httpx.Response(200, json={
        "data": [{"id": 1, "job_title": "Judaic Studies Teacher",
                  "url": "https://school.example/opening"}],
    }))
    main.app.dependency_overrides[main.authenticated_user] = lambda: main.AuthenticatedUser("user", "token")
    try:
        response = TestClient(main.app).post("/career-tree/jobs", json={
            "session_id": "session", "node_id": "role", "country": "US", "workplace": "remote",
        })
        assert response.status_code == (503 if invalid_titles else 200)
        if invalid_titles:
            assert "invalid search titles" in response.json()["detail"]
        else:
            assert response.json()["jobs"][0]["title"] == "Judaic Studies Teacher"
            assert response.json()["source"] == "TheirStack"
    finally:
        main.app.dependency_overrides.clear()
