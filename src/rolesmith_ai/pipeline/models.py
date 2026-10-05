from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Experience(BaseModel):
    company: str
    title: str
    dates: str
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    link: str | None = None


class Education(BaseModel):
    institution: str
    degree: str
    dates: str


class Certification(BaseModel):
    name: str
    issuer: str
    dates: str | None = None


class Preferences(BaseModel):
    preferred_locations: list[str] = Field(default_factory=list)
    remote_ok: bool = False
    deal_breakers: list[str] = Field(default_factory=list)
    avoid_companies: list[str] = Field(default_factory=list)
    notes: str | None = None


class MasterProfile(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    links: list[str] = Field(default_factory=list)
    headline: str
    total_experience_years: float
    summary: str
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)


class JobRating(BaseModel):
    score: int
    verdict: Literal["apply", "maybe", "skip"]
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    seniority_fit: str
    red_flags: list[str] = Field(default_factory=list)
    reasoning: str
    jd_quality: Literal["full", "partial", "missing"]

    @field_validator("score", mode="before")
    def coerce_score(cls, v):
        if isinstance(v, str):
            v = v.replace("%", "").strip()
            try:
                v = float(v)
            except ValueError:
                v = 0
        if isinstance(v, float):
            v = int(v)
        return max(0, min(100, v))


class ResumeDraft(BaseModel):
    headline: str
    summary: str
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    cover_note: str | None = None


class FormAnswer(BaseModel):
    answer: Any
    confidence: float
    reasoning: str | None = None
