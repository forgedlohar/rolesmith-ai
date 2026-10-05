import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rolesmith.branding import ENV_PREFIX

class LLMSettings(BaseSettings):
    base_url: str = Field(default="http://localhost:8000/v1")
    model: str = Field(default="local")
    api_key: str = Field(default="sk-local")
    json_mode: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix=f"{ENV_PREFIX}LLM_",
        env_file=".env",
        extra="ignore"
    )

class AutopilotSettings(BaseSettings):
    platforms: list[str] = Field(default_factory=lambda: ["naukri", "linkedin"])
    days: int = Field(default=3)
    fetch_jd_linkedin: bool = Field(default=False)
    jd_enrich: bool = Field(default=True)
    max_jd_chars: int = Field(default=6000)
    max_rate_per_run: int = Field(default=30)
    max_tailor_per_run: int = Field(default=10)
    rate_min_score: int = Field(default=65)
    tailor_min_score: int = Field(default=70)
    auto_apply_min_score: int = Field(default=80)
    max_per_day: int = Field(default=15)
    max_per_company: int = Field(default=2)
    max_bullets_per_role: int = Field(default=4)
    max_projects: int = Field(default=3)
    llm_form_answers: bool = Field(default=True)
    cover_note: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix=f"{ENV_PREFIX}AUTOPILOT_",
        env_file=".env",
        extra="ignore"
    )

class CredentialsSettings(BaseSettings):
    linkedin_email: str = ""
    linkedin_password: str = ""
    naukri_email: str = ""
    naukri_password: str = ""
    wellfound_email: str = ""
    wellfound_password: str = ""
    indeed_email: str = ""
    indeed_password: str = ""
    hirist_email: str = ""
    hirist_password: str = ""
    
    model_config = SettingsConfigDict(
        env_prefix=f"{ENV_PREFIX}",
        env_file=".env",
        extra="ignore"
    )

class Settings(BaseSettings):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    autopilot: AutopilotSettings = Field(default_factory=AutopilotSettings)
    credentials: CredentialsSettings = Field(default_factory=CredentialsSettings)

def load_settings() -> Settings:
    return Settings(
        llm=LLMSettings(),
        autopilot=AutopilotSettings(),
        credentials=CredentialsSettings()
    )

settings = load_settings()
