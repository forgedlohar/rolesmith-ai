from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator

class Experience(BaseModel):
    company: str
    title: str
    dates: str
    location: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)

class Project(BaseModel):
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None

class Education(BaseModel):
    institution: str
    degree: str
    dates: str

class Certification(BaseModel):
    name: str
    issuer: str
    dates: Optional[str] = None

class Preferences(BaseModel):
    preferred_locations: List[str] = Field(default_factory=list)
    remote_ok: bool = False
    deal_breakers: List[str] = Field(default_factory=list)
    avoid_companies: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

class MasterProfile(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    links: List[str] = Field(default_factory=list)
    headline: str
    total_experience_years: float
    summary: str
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

class JobRating(BaseModel):
    score: int
    verdict: Literal["apply", "maybe", "skip"]
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    seniority_fit: str
    red_flags: List[str] = Field(default_factory=list)
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
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    cover_note: Optional[str] = None

class FormAnswer(BaseModel):
    answer: Any
    confidence: float
    reasoning: Optional[str] = None
