import json

from pydantic import BaseModel
from rolesmith_ai.pipeline.llm import extract_json
from rolesmith_ai.pipeline.models import Experience, JobRating, MasterProfile, ResumeDraft
from rolesmith_ai.pipeline.rating import rate_job
from rolesmith_ai.pipeline.tailor import tailor_resume


class DummyModel(BaseModel):
    name: str
    age: int


def test_extract_json():
    # Test valid JSON block
    text = '```json\n{"name": "Alice", "age": 30}\n```'
    data = json.loads(extract_json(text))
    assert data["name"] == "Alice"
    assert data["age"] == 30

    # Test raw JSON string
    text = '{"name": "Bob", "age": 25}'
    data = json.loads(extract_json(text))
    assert data["name"] == "Bob"
    assert data["age"] == 25


def test_rating_empty_desc(mocker):
    # Mock LLM completion to return a static rating
    mock_resp = JobRating(
        score=0,
        verdict="skip",
        seniority_fit="mismatch",
        reasoning="No description provided.",
        jd_quality="missing",
        matched_skills=[],
        missing_skills=[],
        red_flags=[],
    )
    mocker.patch("rolesmith_ai.pipeline.rating.complete_json", return_value=mock_resp)

    rating = rate_job("Software Engineer", "Acme Corp", "")
    assert rating.score == 0
    assert rating.jd_quality == "missing"
    assert rating.verdict == "skip"


def test_tailoring_drops_experience(mocker):
    # Setup mock master profile

    mock_master = MasterProfile(
        name="Test User",
        email="test@test.com",
        phone="1234567890",
        headline="Software Engineer",
        summary="A summary",
        target_roles=["DevOps"],
        total_experience_years="5",
        location="India",
        experience=[
            Experience(
                company="Company A",
                title="DevOps",
                location="Remote",
                dates="2020 - Present",
                bullets=["Did something cool", "Did something else"],
            )
        ],
    )
    mocker.patch("rolesmith_ai.pipeline.tailor.load_master_profile", return_value=mock_master)

    # Setup mock LLM completion

    mock_tailor = ResumeDraft(
        headline="DevOps Engineer",
        summary="Tailored summary",
        cover_note="Hello",
        experience=[
            Experience(
                company="Company A",
                title="DevOps",
                location="Remote",
                dates="2020 - Present",
                bullets=[
                    "Did something cool (tailored)",
                    "New bullet not in master! Improved by 50%",
                ],
            )
        ],
    )
    mocker.patch("rolesmith_ai.pipeline.tailor.complete_json", return_value=mock_tailor)

    rating = JobRating(
        score=80,
        verdict="apply",
        seniority_fit="fit",
        reasoning="Good match",
        jd_quality="full",
        matched_skills=[],
        missing_skills=[],
        red_flags=[],
    )
    draft, warnings = tailor_resume("DevOps", "Target Corp", "We need DevOps", rating)

    assert len(draft.experience) == 1
    # Only the bullet that exists in master should remain
    # But wait, our matching is simple. "Did something cool (tailored)" might not match "Did something cool" exactly if we use strict substring.
    # In tailor.py we check `if any(llm_bullet.strip() in p_b.strip() for p_b in exp.bullets) or any(p_b.strip() in llm_bullet.strip() for p_b in exp.bullets)`.
    # Let's see:

    # Actually wait, "Did something cool" is in "Did something cool (tailored)".
    # So it should be kept. "New bullet not in master!" is dropped.
    assert len(draft.experience[0].bullets) == 1
    assert draft.experience[0].bullets[0] == "Did something cool (tailored)"
    assert len(warnings) == 1
    assert "invented numbers" in warnings[0].lower()
