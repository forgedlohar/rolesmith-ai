import json
import re
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .settings import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


def extract_json(text: str) -> str:
    # Remove <think> blocks
    text = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL)

    # Remove markdown code blocks
    text = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)

    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _call_api(system: str, user: str, use_json_mode: bool = True) -> str:
    req_data = {
        "model": settings.llm.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **settings.llm.extra_body,
    }

    if use_json_mode and settings.llm.json_mode:
        req_data["response_format"] = {"type": "json_object"}

    req_bytes = json.dumps(req_data).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.llm.base_url}/chat/completions",
        data=req_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm.api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body)
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP Error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"Cannot reach LLM at {settings.llm.base_url}") from e
    except Exception as e:
        raise LLMError(f"LLM call failed: {e!s}") from e


def complete_json(system: str, user: str, model_cls: type[T], retries: int = 2) -> T:
    last_error = None
    use_json_mode = True

    # Add schema to system prompt
    schema_str = json.dumps(model_cls.model_json_schema())
    sys_prompt = f"{system}\n\nYou must respond with JSON conforming to this schema:\n{schema_str}"

    current_user = user
    for attempt in range(retries + 1):
        try:
            try:
                response_text = _call_api(sys_prompt, current_user, use_json_mode=use_json_mode)
            except LLMError as e:
                # Retry once without response_format on HTTP 400
                if "400" in str(e) and use_json_mode:
                    use_json_mode = False
                    response_text = _call_api(sys_prompt, current_user, use_json_mode=use_json_mode)
                else:
                    raise

            json_str = extract_json(response_text)
            if not json_str:
                raise ValueError("No JSON object found in response")

            parsed = json.loads(json_str)
            return model_cls(**parsed)

        except (ValueError, json.JSONDecodeError, ValidationError) as e:
            last_error = e
            current_user = f"{user}\n\nYour previous response failed validation with error:\n{e!s}\n\nPlease try again."

    raise LLMError(f"Failed to generate valid JSON after {retries} retries. Last error: {last_error}")
