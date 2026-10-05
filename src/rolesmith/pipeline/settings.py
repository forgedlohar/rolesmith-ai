import os
import json
from pathlib import Path
from pydantic import BaseModel, Field

def get_config_path() -> Path:
    return Path.home() / ".rolesmith" / "config.json"

class LLMSettings(BaseModel):
    base_url: str = Field(default="http://localhost:8000/v1")
    model: str = Field(default="local")
    api_key: str = Field(default="sk-local")
    json_mode: bool = Field(default=True)
    extra_body: dict = Field(default_factory=dict)

class AutopilotSettings(BaseModel):
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

class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    autopilot: AutopilotSettings = Field(default_factory=AutopilotSettings)

def load_settings() -> Settings:
    config_path = get_config_path()
    raw_config = {}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                raw_config = json.load(f)
        except Exception:
            pass

    llm_config = raw_config.get("llm", {})
    autopilot_config = raw_config.get("autopilot", {})

    settings = Settings(
        llm=LLMSettings(**llm_config),
        autopilot=AutopilotSettings(**autopilot_config)
    )

    # Env overrides
    if "AUTOPILOT_LLM_BASE_URL" in os.environ:
        settings.llm.base_url = os.environ["AUTOPILOT_LLM_BASE_URL"]
    if "AUTOPILOT_LLM_MODEL" in os.environ:
        settings.llm.model = os.environ["AUTOPILOT_LLM_MODEL"]
    if "AUTOPILOT_LLM_API_KEY" in os.environ:
        settings.llm.api_key = os.environ["AUTOPILOT_LLM_API_KEY"]

    return settings

settings = load_settings()
