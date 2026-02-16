import pytest

from app.nodes.interests_node import InterestsNode


def run_node(user_input: str):
    node = InterestsNode()
    # Call without session_id to avoid external I/O in tests
    msg, state = node.process(user_input=user_input, state={}, session_id=None)
    return msg, state


@pytest.mark.parametrize(
    "user_input, expected_subset",
    [
        (
            "product design, user research, data science, machine learning",
            {"Product Design", "User Research", "Data Science", "Machine Learning"},
        ),
        (
            "data engineering, cloud infrastructure, devops, ml ops",
            {"Data Engineering", "Cloud Infrastructure", "DevOps", "MLOps"},
        ),
        (
            "UX/UI, front end dev, backend microservices",
            {"UX/UI", "Front End Development", "Backend Microservices"},
        ),
        (
            "social work community development public policy",
            {"Social Work", "Community Development", "Public Policy"},
        ),
        (
            "art history graphic design museum curation",
            {"Art History", "Graphic Design", "Museum Curation"},
        ),
        (
            "photography product management ux ui sustainability marketing data analysis",
            {"Photography", "Product Management", "UX/UI", "Sustainability", "Marketing", "Data Analysis"},
        ),
        (
            "arts and crafts jigsaw puzzles reading gardening",
            {"Arts And Crafts", "Jigsaw Puzzles", "Reading", "Gardening"},
        ),
    ],
)
def test_interests_extraction(user_input, expected_subset):
    _, state = run_node(user_input)
    interests = set(state.get("interests") or [])
    # Ensure all expected items are present in the interests output
    assert expected_subset.issubset(interests)
