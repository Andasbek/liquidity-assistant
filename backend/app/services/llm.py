import httpx
from typing import List, Dict, Any
from ..core import config

def _build_messages(system: str, user: str) -> List[Dict[str, str]]:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    return msgs

def chat(system_prompt: str, user_prompt: str) -> str:
    provider = config.LLM_PROVIDER
    if not provider:
        # LLM не сконфигурирован — вернём пусто, пусть вызывающий сделает фоллбек
        return ""

    if provider == "ollama":
        return _ollama_chat(system_prompt, user_prompt)
    elif provider == "openai":
        return _openai_compat_chat(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

def _ollama_chat(system_prompt: str, user_prompt: str) -> str:
    url = f"{config.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": config.LLM_MODEL,
        "messages": _build_messages(system_prompt, user_prompt),
        "stream": False,
        "options": {"temperature": 0.2}
    }
    with httpx.Client(timeout=config.LLM_TIMEOUT) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        # формат: {"message": {"content": "..."}}
        return data.get("message", {}).get("content", "")

def _openai_compat_chat(system_prompt: str, user_prompt: str) -> str:
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
    payload = {
        "model": config.LLM_MODEL,
        "messages": _build_messages(system_prompt, user_prompt),
        "temperature": 0.2,
        "stream": False,
    }
    with httpx.Client(timeout=config.LLM_TIMEOUT, headers=headers) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        # формат OpenAI: choices[0].message.content
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
