import json
import os
import urllib.error
import urllib.request


DEFAULT_BAILIAN_BASE_URL = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)
DEFAULT_BAILIAN_MODEL = "qwen-plus"


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid float value for {name}: {value}") from exc


def call_llm(system_prompt: str, user_message: str) -> str:
    if os.getenv("JKMEM_LLM_MODE", "").lower() == "stub":
        return f"(stub) {user_message}"

    api_key = os.getenv("JKMEM_BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Bailian API key. Set JKMEM_BAILIAN_API_KEY or DASHSCOPE_API_KEY."
        )

    base_url = os.getenv("JKMEM_BAILIAN_BASE_URL", DEFAULT_BAILIAN_BASE_URL)
    model = os.getenv("JKMEM_BAILIAN_MODEL", DEFAULT_BAILIAN_MODEL)
    temperature = _get_env_float("JKMEM_BAILIAN_TEMPERATURE", 0.2)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        base_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Bailian API error ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach Bailian API: {exc.reason}") from exc

    data = json.loads(raw)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"Unexpected Bailian response: {data}")

    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise RuntimeError(f"Missing content in Bailian response: {data}")
    return content
