import re

from .llm import complete_json
from .models import JobRating
from .profile_store import compact_profile_text, load_master_profile

RATING_SYSTEM_PROMPT = """You are an expert technical recruiter evaluating a job description against a candidate's profile.
Your job is to rate the candidate's fit for this role objectively.
Be critical. Do not inflate the score. A 100 means an absolutely perfect fit. 
Identify matched and missing skills accurately based ONLY on the provided JD.
Determine if the seniority fits (e.g., if JD wants 10 years and candidate has 3, that's a poor fit).
Identify any red flags (e.g., tech stack completely different, requires clearance candidate doesn't have).

Rate the jd_quality:
- "full": The JD has substantial details about responsibilities and requirements.
- "partial": The JD is very short or vague.
- "missing": The JD has barely any text or seems like a placeholder.
"""


def _check_deal_breakers(jd_text: str, deal_breakers: list[str]) -> str | None:
    jd_lower = jd_text.lower()
    for db in deal_breakers:
        db_lower = db.lower()
        if re.search(r"\b" + re.escape(db_lower) + r"\b", jd_lower):
            return db
    return None


def rate_job(title: str, company: str, description: str) -> JobRating:
    profile = load_master_profile()

    # Pre-flight check: deal breakers
    db = _check_deal_breakers(description, profile.preferences.deal_breakers)
    if db:
        return JobRating(
            score=0,
            verdict="skip",
            matched_skills=[],
            missing_skills=[],
            seniority_fit="N/A",
            red_flags=[f"Deal breaker found: {db}"],
            reasoning=f"Automatic skip: JD contains deal-breaker '{db}'",
            jd_quality="full" if len(description) > 500 else "partial",
        )

    user_prompt = f"""Candidate Profile:
{compact_profile_text(profile)}

---
Job Details:
Title: {title}
Company: {company}
Description:
{description}

Evaluate the fit and provide a detailed rating."""

    # Call LLM
    rating = complete_json(RATING_SYSTEM_PROMPT, user_prompt, JobRating)

    # Apply post-flight guards
    if rating.jd_quality == "missing":
        rating.score = min(rating.score, 60)
    elif rating.jd_quality == "partial":
        rating.score = min(rating.score, 80)

    if rating.score >= 75:
        rating.verdict = "apply"
    elif 60 <= rating.score <= 74:
        rating.verdict = "maybe"
    else:
        rating.verdict = "skip"

    return rating
