# llm_client.py
import os
import json
import re
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

# ---- Defaults you can tweak ----
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "1"))
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
DEFAULT_SEED = int(os.getenv("OPENAI_SEED", "1337"))
DEFAULT_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))  # seconds
DEFAULT_JSON_MODE = True  # our lens prompts require JSON

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---- Helpers ----

def _extract_json_loose(text: str) -> Optional[str]:
    """
    Try to pull a JSON object from text even if the model added extra prose.
    Looks for the first {...} block and returns it.
    """
    if not text:
        return None
    # Try fenced blocks first
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fence:
        return fence.group(1).strip()
    # Fallback: first balanced-ish { ... }
    brace = re.search(r"\{.*\}", text, flags=re.S)
    return brace.group(0).strip() if brace else None


def _parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Strict JSON parse with a loose fallback that tries to extract a JSON object.
    Raises ValueError if both attempts fail.
    """
    try:
        return json.loads(text)
    except Exception:
        extracted = _extract_json_loose(text)
        if extracted is None:
            raise ValueError("Model did not return JSON.")
        try:
            return json.loads(extracted)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON after extraction: {e}")


def _retry_backoff(attempt: int, base: float = 0.75, cap: float = 8.0) -> None:
    """Simple exponential backoff with jitter."""
    delay = min(cap, base * (2 ** attempt)) + (0.05 * attempt)
    time.sleep(delay)


# ---- Main entrypoints ----

def query_gpt_client(
    prompt: str,
    *,
    temperature: int = DEFAULT_TEMPERATURE,
    model: str = DEFAULT_MODEL,
    max_completion_tokens: int = DEFAULT_MAX_TOKENS,
    seed: int = DEFAULT_SEED,
    json_mode: bool = DEFAULT_JSON_MODE,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> Dict[str, Any]:
    """
    Send a single-prompt chat completion. Returns a dict.
    - json_mode=True -> enforce JSON-only responses using response_format.
    - Parses and returns a Python dict; raises on hard failure.
    """
    system_msg = (
        "You are a careful, deterministic evaluator. "
        "Return ONLY the JSON object required by the prompt. "
        "No extra text, no explanations."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]

    # response_format only for JSON mode
    response_format = {"type": "json_object"} if json_mode else None

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                seed=seed,
                timeout=timeout,
                response_format=response_format,  # requires json-capable models (e.g., gpt-4o, gpt-4o-mini)
            )
            content = (resp.choices[0].message.content or "").strip()
            if json_mode:
                return _parse_json_strict(content)
            # non-JSON mode: return a text envelope
            return {"text": content}
        except (OpenAIError, ValueError) as e:
            last_err = e
            if attempt < retries:
                _retry_backoff(attempt)
            else:
                raise

    # Should never get here due to raise on last retry
    if last_err:
        raise last_err
    raise RuntimeError("Unknown error in query_gpt_client")


def query_gpt_messages(
    messages: list,
    *,
    temperature: int = DEFAULT_TEMPERATURE,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    seed: int = DEFAULT_SEED,
    json_mode: bool = DEFAULT_JSON_MODE,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> Dict[str, Any]:
    """
    For advanced use: pass your own messages array.
    If json_mode=True, enforces JSON and returns a dict; else returns {"text": "..."}.
    """
    # Prepend the same JSON-only system guard in json mode
    if json_mode:
        messages = [
            {
                "role": "system",
                "content": "Return ONLY a single valid JSON object. No extra text."
            }
        ] + messages

    response_format = {"type": "json_object"} if json_mode else None

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                seed=seed,
                timeout=timeout,
                response_format=response_format,
            )
            content = (resp.choices[0].message.content or "").strip()
            if json_mode:
                return _parse_json_strict(content)
            return {"text": content}
        except (OpenAIError, ValueError) as e:
            last_err = e
            if attempt < retries:
                _retry_backoff(attempt)
            else:
                raise

    if last_err:
        raise last_err
    raise RuntimeError("Unknown error in query_gpt_messages")