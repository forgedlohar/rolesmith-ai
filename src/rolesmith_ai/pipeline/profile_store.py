import json
from pathlib import Path

from rolesmith_ai.config import CONFIG_PATH

from .models import MasterProfile


def get_profile_path() -> Path:
    return Path.home() / ".rolesmith_ai" / "master_profile.json"


def init_template():
    path = get_profile_path()
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    template = MasterProfile(
        name="Jane Doe",
        email="jane@example.com",
        phone="+1234567890",
        location="Remote",
        headline="Senior Software Engineer",
        total_experience_years=5.0,
        summary="Experienced engineer focusing on backend systems.",
        skills={"Languages": ["Python", "Go"], "Tools": ["Docker"]},
        experience=[
            {
                "company": "Tech Corp",
                "title": "Software Engineer",
                "dates": "Jan 2020 - Present",
                "bullets": ["Built microservices", "Improved performance by 20%"],
            }
        ],
        target_roles=["Backend Engineer", "Software Engineer"],
    )
    with open(path, "w") as f:
        f.write(template.model_dump_json(indent=2))


def load_master_profile() -> MasterProfile:
    path = get_profile_path()
    if not path.exists():
        init_template()
    with open(path, "r") as f:
        data = json.load(f)
    return MasterProfile(**data)


def compact_profile_text(profile: MasterProfile) -> str:
    lines = [
        f"Name: {profile.name}",
        f"Headline: {profile.headline}",
        f"Experience: {profile.total_experience_years} years",
        f"Summary: {profile.summary}",
        "Skills:",
    ]
    for category, skills in profile.skills.items():
        lines.append(f"  {category}: {', '.join(skills)}")

    lines.append("Experience:")
    for exp in profile.experience:
        lines.append(f"  {exp.title} at {exp.company} ({exp.dates})")
        for bullet in exp.bullets:
            lines.append(f"    - {bullet}")

    if profile.projects:
        lines.append("Projects:")
        for p in profile.projects:
            lines.append(f"  {p.name}: {p.description}")
            if p.technologies:
                lines.append(f"    Tech: {', '.join(p.technologies)}")

    return "\n".join(lines)


def sync_into_config():
    profile = load_master_profile()
    config_path = CONFIG_PATH
    raw_config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            try:
                raw_config = json.load(f)
            except json.JSONDecodeError:
                pass

    all_skills = [s for skills in profile.skills.values() for s in skills]

    # Derive title_must_contain from target_roles
    generic_words = {
        "senior",
        "junior",
        "mid",
        "lead",
        "staff",
        "principal",
        "engineer",
        "developer",
        "manager",
    }
    title_must_contain = []
    for role in profile.target_roles:
        words = [w.lower() for w in role.split()]
        filtered = [w for w in words if w not in generic_words]
        if filtered:
            title_must_contain.append(" ".join(filtered))
        else:
            title_must_contain.append(role.lower())

    title_must_contain = list(set(title_must_contain))

    candidate_profile = {
        "skills": all_skills,
        "target_roles": profile.target_roles,
        "default_search_keywords": profile.target_roles,
        "title_must_contain": title_must_contain,
        "avoid_keywords": profile.preferences.deal_breakers,
    }

    raw_config["candidate_profile"] = candidate_profile
    raw_config["name"] = profile.name
    raw_config["email"] = profile.email
    raw_config["phone"] = profile.phone
    raw_config["location"] = profile.location
    raw_config["experience_years"] = int(profile.total_experience_years)

    with open(config_path, "w") as f:
        json.dump(raw_config, f, indent=2)
