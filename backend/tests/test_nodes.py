import pytest

from app.nodes.interests_node import InterestsNode
from app.nodes.industry_node import IndustryNode
from app.nodes.job_node import JobNode
from app.nodes.skills_node import SkillsNode


class DummyClient:
    def __init__(self, response):
        self._response = response

    def chat(self, messages=None, **kwargs):
        return self._response


@pytest.fixture
def capture_save(monkeypatch):
    saved = {}

    def fake_save(session_id, state):
        saved['session_id'] = session_id
        saved['state'] = state.copy() if isinstance(state, dict) else state

    monkeypatch.setattr('app.nodes.interests_node.save_state', fake_save, raising=False)
    monkeypatch.setattr('app.nodes.industry_node.save_state', fake_save, raising=False)
    monkeypatch.setattr('app.nodes.job_node.save_state', fake_save, raising=False)
    monkeypatch.setattr('app.nodes.skills_node.save_state', fake_save, raising=False)
    return saved


@pytest.fixture
def provide_saved(monkeypatch):
    # Default saved state returned by get_state
    def _setup(saved_state):
        monkeypatch.setattr('app.nodes.interests_node.get_state', lambda sid: saved_state, raising=False)
        monkeypatch.setattr('app.nodes.industry_node.get_state', lambda sid: saved_state, raising=False)
        monkeypatch.setattr('app.nodes.job_node.get_state', lambda sid: saved_state, raising=False)
        monkeypatch.setattr('app.nodes.skills_node.get_state', lambda sid: saved_state, raising=False)
    return _setup


def test_interests_node_reads_and_writes(capture_save, provide_saved, monkeypatch):
    node = InterestsNode()
    # simulate saved state that should be used instead of passed-in state
    provide_saved({'foo': 'bar'})
    # mock client
    monkeypatch.setattr('app.nodes.interests_node.client', DummyClient(['Industry A', 'Industry B']), raising=False)

    resp, state = node.process('I like design', state={}, session_id='sess1')

    assert 'industries' in state
    assert capture_save['session_id'] == 'sess1'
    assert capture_save['state']['industries'] == ['Industry A', 'Industry B']


def test_industry_node_reads_and_writes(capture_save, provide_saved, monkeypatch):
    node = IndustryNode()
    provide_saved({'interests': 'I like design'})
    monkeypatch.setattr('app.nodes.industry_node.client', DummyClient(['JobFamily1', 'JobFamily2']), raising=False)

    resp, state = node.process('Design', state={}, session_id='sess2')

    assert 'job_families' in state
    assert capture_save['session_id'] == 'sess2'
    assert capture_save['state']['job_families'] == ['JobFamily1', 'JobFamily2']


def test_job_node_reads_and_writes(capture_save, provide_saved, monkeypatch):
    node = JobNode()
    provide_saved({'selected_industry': 'Design'})
    monkeypatch.setattr('app.nodes.job_node.client', DummyClient(['Job1', 'Job2']), raising=False)

    resp, state = node.process('Product Design', state={}, session_id='sess3')

    assert 'jobs' in state
    assert capture_save['session_id'] == 'sess3'
    assert capture_save['state']['jobs'] == ['Job1', 'Job2']


def test_skills_node_reads_and_writes(capture_save, provide_saved, monkeypatch):
    node = SkillsNode()
    provide_saved({'selected_job_family': 'Product Design'})
    monkeypatch.setattr('app.nodes.skills_node.client', DummyClient({'hard_skills': ['A'], 'soft_skills': ['B']}), raising=False)

    resp, state = node.process('Senior Product Designer', state={}, session_id='sess4')

    assert 'skills' in state
    assert capture_save['session_id'] == 'sess4'
    assert capture_save['state']['skills'] == {'hard_skills': ['A'], 'soft_skills': ['B']}
