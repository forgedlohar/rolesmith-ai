import json
import re
from typing import Any

from rolesmith_ai import config
from rolesmith_ai.store import get_cached_answer, save_answer

from .llm import LLMError, complete_json
from .models import FormAnswer
from .profile_store import load_master_profile

ANSWERS_SYSTEM_PROMPT = """You are answering job application form questions on behalf of the candidate.
Rely strictly on the provided profile facts.
Do NOT guess or invent facts.
If the question is sensitive or demographic (gender, DOB, age, religion, caste, race, disability,
nationality, visa/work authorization, criminal, salary history, ID numbers), you MUST set confidence to 0 and answer None.
If options are provided, your answer MUST exactly match one of the options.
If you cannot answer from the facts, set confidence to 0.
"""


def is_sensitive(question: str) -> bool:
    q = question.lower()
    sensitive_words = [
        "gender",
        "dob",
        "date of birth",
        "age",
        "religion",
        "caste",
        "race",
        "disability",
        "nationality",
        "visa",
        "work authorization",
        "criminal",
        "salary history",
        "id number",
        "ssn",
        "passport",
    ]
    for w in sensitive_words:
        # Avoid matching 'manage' when looking for 'age'
        if re.search(r"\b" + re.escape(w) + r"\b", q):
            return True
    return False


def get_answer(question: str, options: list[str] | None = None) -> Any | None:
    try:
        if is_sensitive(question):
            return None

        cached = get_cached_answer(question, options)
        if cached:
            ans, src, conf = cached
            if conf >= 0.5:
                return ans
            return None

        master = load_master_profile()
        cfg = config.load_config()

        # Build facts text
        facts = master.model_dump()
        facts.pop("preferences", None)

        autofill = cfg.autofill.copy()
        for k in ["gender", "dob", "avoid_companies"]:
            autofill.pop(k, None)

        user_prompt = f"""Candidate Facts:
{json.dumps(facts, indent=2)}

Autofill Defaults:
{json.dumps(autofill, indent=2)}

---
Question: {question}
"""
        if options:
            user_prompt += "\nOptions:\n" + "\n".join(f"- {o}" for o in options)
            user_prompt += "\nYour answer MUST exactly match one of the options."

        try:
            ans_obj = complete_json(ANSWERS_SYSTEM_PROMPT, user_prompt, FormAnswer)
        except LLMError:
            return None

        # Post-flight checks
        if ans_obj.confidence < 0.5:
            save_answer(question, options, ans_obj.answer, "llm", ans_obj.confidence)
            return None

        if options and ans_obj.answer not in options:
            # Maybe case mismatch?
            for o in options:
                if str(ans_obj.answer).lower() == str(o).lower():
                    ans_obj.answer = o
                    break
            else:
                save_answer(question, options, ans_obj.answer, "llm", ans_obj.confidence)
                return None

        save_answer(question, options, ans_obj.answer, "llm", ans_obj.confidence)
        return ans_obj.answer
    except Exception:
        # Must never raise into the caller
        return None
