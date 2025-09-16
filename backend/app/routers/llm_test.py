# backend/app/routers/llm_test.py
from fastapi import APIRouter
from ..services import llm
from ..core import config

router = APIRouter(tags=["llm"])

@router.get("/llm/test")
def llm_test():
    try:
        sample = llm.chat("Ты ассистент.", "Ответь одним словом: Готово.")
    except Exception as e:
        sample = f"error: {e}"
    return {
        "provider": config.LLM_PROVIDER,
        "model": config.LLM_MODEL,
        "base_url": (config.OLLAMA_BASE_URL if config.LLM_PROVIDER == "ollama" else config.OPENAI_BASE_URL),
        "sample": sample
    }
